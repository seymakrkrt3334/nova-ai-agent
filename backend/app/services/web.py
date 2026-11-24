import re
from html import unescape
from urllib.parse import parse_qs, quote_plus, unquote, urlparse

import httpx

from app.config import settings
from app.services.net_guard import UnsafeURL, citation_url, validate_public_url

MAX_QUERY_CHARS = 300
MAX_PAGE_CHARS = 8000
MAX_RESULTS = 5
DUCKDUCKGO_URL = "https://html.duckduckgo.com/html/"
ANCHOR_RE = re.compile(
    r'<a[^>]*class="[^"]*result__a[^"]*"[^>]*href="([^"]+)"[^>]*>(.*?)</a>',
    re.IGNORECASE | re.DOTALL,
)
TAG_RE = re.compile(r"(?is)<(script|style).*?>.*?</\1>|<[^>]+>")


def user_named_url(message: str, url: str) -> bool:
    if not url or not message:
        return False
    lowered = message.lower()
    if url.lower() in lowered:
        return True
    host = urlparse(url).hostname
    return bool(host) and host.lower() in lowered


def strip_html(value: str) -> str:
    text = TAG_RE.sub(" ", value or "")
    return " ".join(unescape(text).split())


def _clip(value: str, limit: int) -> str:
    return " ".join(str(value or "").split())[:limit]


def provider_request(query: str) -> tuple[str, str] | None:
    cleaned = " ".join(query.split())
    if not cleaned or len(cleaned) > MAX_QUERY_CHARS:
        raise ValueError("Invalid search.")
    provider = (settings.web_search_provider or "disabled").strip().lower()
    if provider in {"", "disabled", "off"}:
        return None
    encoded = quote_plus(cleaned)
    if provider == "duckduckgo":
        return "duckduckgo", f"{DUCKDUCKGO_URL}?q={encoded}"
    if provider == "searxng":
        base = (settings.web_search_base_url or "").strip().rstrip("/")
        if not base:
            return None
        return "searxng", f"{base}/search?format=json&q={encoded}"
    return None


def decode_result_url(href: str) -> str | None:
    href = unescape(href or "").strip()
    if href.startswith("//"):
        href = "https:" + href
    parsed = urlparse(href)
    values = parse_qs(parsed.query).get("uddg")
    if values:
        href = unquote(values[0])
    return citation_url(href)


def parse_duckduckgo_html(page: str) -> list[dict]:
    results = []
    for href, raw_title in ANCHOR_RE.findall(page or ""):
        url = decode_result_url(href)
        title = strip_html(raw_title)
        if not url or not title:
            continue
        results.append({"title": _clip(title, 180), "url": url, "snippet": ""})
        if len(results) >= MAX_RESULTS:
            break
    return results


def parse_searxng_json(payload: dict) -> list[dict]:
    results = []
    for item in (payload or {}).get("results", []):
        if not isinstance(item, dict):
            continue
        url = citation_url(str(item.get("url") or ""))
        title = _clip(item.get("title") or "", 180)
        if not url or not title:
            continue
        results.append({
            "title": title,
            "url": url,
            "snippet": _clip(item.get("content") or "", 300),
        })
        if len(results) >= MAX_RESULTS:
            break
    return results


async def search_web(query: str, limit: int = 5, transport=None) -> list[dict]:
    request = provider_request(query)
    if request is None:
        return []
    provider, url = request
    if transport is None:
        async def transport(target: str):
            async with httpx.AsyncClient(timeout=8.0, follow_redirects=False) as client:
                response = await client.get(
                    target,
                    headers={"User-Agent": "NOVA-local/0.3"},
                )
                response.raise_for_status()
                return response.text, response.headers.get("content-type", "")

    body, content_type = await transport(url)
    if provider == "searxng" or "json" in content_type:
        import json
        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            payload = {}
        results = parse_searxng_json(payload if isinstance(payload, dict) else {})
    else:
        results = parse_duckduckgo_html(body)
    return results[: max(1, min(int(limit), MAX_RESULTS))]


async def read_public_page(url: str, *, resolve=None, transport=None) -> dict:
    current = validate_public_url(url, resolve)
    for _ in range(2):
        if transport is None:
            async with httpx.AsyncClient(timeout=8.0, follow_redirects=False) as client:
                response = await client.get(current, headers={"User-Agent": "NOVA-local/0.3"})
                status = response.status_code
                location = response.headers.get("location")
                content_type = response.headers.get("content-type", "")
                body = response.text
        else:
            status, location, content_type, body = await transport(current)
        if status in {301, 302, 303, 307, 308} and location:
            current = validate_public_url(location, resolve)
            continue
        if status >= 400:
            raise UnsafeURL
        if content_type and "html" not in content_type and "text" not in content_type and "json" not in content_type:
            raise UnsafeURL
        return {"url": current, "text": strip_html(body)[:MAX_PAGE_CHARS]}
    raise UnsafeURL
