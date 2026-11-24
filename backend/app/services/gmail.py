
import base64
import re
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from app.services.google_scopes import GMAIL_READONLY_SCOPES
from app.services.web import strip_html

BASE_DIR = Path(__file__).resolve().parents[2]

CREDENTIALS_PATH = BASE_DIR / "credentials.json"
TOKEN_PATH = BASE_DIR / "token.json"

SCOPES = list(GMAIL_READONLY_SCOPES)
PAGE_TOKEN_RE = re.compile(r"^[A-Za-z0-9_-]{1,256}$")
MESSAGE_ID_RE = re.compile(r"^[A-Za-z0-9]{8,64}$")

MAX_QUERY_LENGTH = 500
MAX_RESULTS = 50


def normalize_search(query: str = "in:inbox", limit: int = 10) -> tuple[str, int]:
    if not isinstance(query, str):
        raise ValueError("Invalid search.")
    normalized = " ".join(query.split())
    if not normalized or len(normalized) > MAX_QUERY_LENGTH:
        raise ValueError("Invalid search.")
    if isinstance(limit, bool) or not isinstance(limit, int):
        raise ValueError("Invalid limit.")
    if limit < 1 or limit > MAX_RESULTS:
        raise ValueError("Invalid limit.")
    return normalized, limit


def get_gmail_service():
    creds = None

    if TOKEN_PATH.exists():
        creds = Credentials.from_authorized_user_file(
            str(TOKEN_PATH), SCOPES
        )

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                str(CREDENTIALS_PATH), SCOPES
            )

            creds = flow.run_local_server(port=0)

        TOKEN_PATH.write_text(
            creds.to_json(), encoding="utf-8"
        )

    return build("gmail", "v1", credentials=creds)


def valid_page_token(value: str | None) -> str | None:
    if not value:
        return None
    text = value.strip()
    if not PAGE_TOKEN_RE.fullmatch(text):
        raise ValueError("Invalid page.")
    return text


def iter_parts(payload: dict):
    if not isinstance(payload, dict):
        return
    yield payload
    for part in payload.get("parts") or []:
        yield from iter_parts(part)


def attachment_metadata(payload: dict) -> list[dict]:
    items = []
    for part in iter_parts(payload):
        filename = " ".join(str(part.get("filename") or "").split())
        if not filename:
            continue
        body = part.get("body") or {}
        size = body.get("size") or 0
        try:
            size = int(size)
        except (TypeError, ValueError):
            size = 0
        items.append({
            "filename": filename[:200],
            "mime_type": str(part.get("mimeType") or "")[:120],
            "size": size,
        })
        if len(items) >= 20:
            break
    return items


def classify_priority(label_ids) -> str:
    labels = {str(item).upper() for item in (label_ids or [])}
    if "IMPORTANT" in labels:
        return "high"
    if "CATEGORY_PROMOTIONS" in labels or "CATEGORY_SOCIAL" in labels or "CATEGORY_FORUMS" in labels:
        return "low"
    return "normal"


def extract_text(payload: dict) -> str:
    plain = []
    html = []
    for part in iter_parts(payload):
        mime = str(part.get("mimeType") or "").lower()
        data = (part.get("body") or {}).get("data")
        if not data or mime not in {"text/plain", "text/html"}:
            continue
        try:
            raw = str(data)
            padded = raw + "=" * (-len(raw) % 4)
            decoded = base64.urlsafe_b64decode(padded.encode("utf-8")).decode("utf-8", errors="replace")
        except Exception:
            continue
        if mime == "text/plain":
            plain.append(decoded)
        else:
            html.append(strip_html(decoded))
    chosen = plain or html
    return "\n".join(chosen)[:8000]


def message_view(message: dict, *, include_body: bool = False) -> dict:
    payload = message.get("payload") or {}
    headers = {
        str(header.get("name", "")).lower(): str(header.get("value", ""))
        for header in payload.get("headers") or []
        if isinstance(header, dict)
    }
    view = {
        "id": str(message.get("id") or ""),
        "sender": headers.get("from", ""),
        "subject": headers.get("subject", ""),
        "date": headers.get("date", ""),
        "snippet": message.get("snippet", ""),
        "priority": classify_priority(message.get("labelIds")),
        "attachments": attachment_metadata(payload),
    }
    if include_body:
        view["body"] = extract_text(payload)
    return view


def search_email_page(query="in:inbox", limit=10, page_token=None, include_body=False) -> dict:
    query, limit = normalize_search(query, limit)
    token = valid_page_token(page_token)
    service = get_gmail_service()
    request = {
        "userId": "me",
        "q": query,
        "maxResults": limit,
    }
    if token:
        request["pageToken"] = token
    result = service.users().messages().list(**request).execute()
    emails = []
    message_format = "full" if include_body else "metadata"
    for item in result.get("messages", []):
        kwargs = {
            "userId": "me",
            "id": item["id"],
            "format": message_format,
        }
        if message_format == "metadata":
            kwargs["metadataHeaders"] = ["From", "Subject", "Date"]
        message = service.users().messages().get(**kwargs).execute()
        emails.append(message_view(message, include_body=include_body))
    return {
        "emails": emails,
        "next_page_token": result.get("nextPageToken"),
    }


def search_emails(query="in:inbox", limit=10, page_token=None, include_body=False):
    return search_email_page(
        query,
        limit,
        page_token=page_token,
        include_body=include_body,
    )["emails"]


def authorized_gmail_service():
    """Use an existing readonly token. Never open a browser."""
    from app.errors import AuthorizationRequired

    if not TOKEN_PATH.is_file():
        raise AuthorizationRequired
    creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            TOKEN_PATH.write_text(creds.to_json(), encoding="utf-8")
        else:
            raise AuthorizationRequired
    return build("gmail", "v1", credentials=creds)


def inbox_subjects(limit: int = 10) -> list[str]:
    service = authorized_gmail_service()
    listed = service.users().messages().list(
        userId="me",
        q="in:inbox newer_than:1d",
        maxResults=min(max(int(limit), 1), 10),
    ).execute()
    subjects = []
    for item in (listed.get("messages") or [])[:10]:
        message = service.users().messages().get(
            userId="me",
            id=item.get("id"),
            format="metadata",
            metadataHeaders=["Subject"],
        ).execute()
        headers = {
            str(header.get("name", "")).lower(): str(header.get("value", ""))
            for header in ((message.get("payload") or {}).get("headers") or [])
        }
        subject = " ".join(headers.get("subject", "").split())[:80]
        if subject:
            subjects.append(subject)
    return subjects


def get_email(message_id: str) -> dict:
    if not isinstance(message_id, str) or not MESSAGE_ID_RE.fullmatch(message_id):
        raise ValueError("Invalid message.")
    service = get_gmail_service()
    message = service.users().messages().get(
        userId="me",
        id=message_id,
        format="full",
    ).execute()
    return message_view(message, include_body=True)
