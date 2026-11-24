import asyncio
import inspect
import json
import logging

from app.agents.tools import (
    MAX_TOOL_STEPS,
    CalendarListArguments,
    CalendarProposeArguments,
    ContactsSearchArguments,
    GmailReadArguments,
    GmailSearchArguments,
    LEGACY_REMEMBER_PREFIX,
    MemorySearchArguments,
    WebReadArguments,
    WebSearchArguments,
    build_gmail_query,
    explicit_save_parts,
    parse_tool_call,
    prepare_emails,
    resolve_gmail_search,
    router_instructions,
    router_payload,
    wants_full_email,
    wants_reply_draft,
)
from app.errors import AuthorizationRequired, LLMUnavailableError, is_llm_unavailable
from app.services.calendar_flow import (
    apply_change,
    interpret_calendar_request,
    pending_confirmation,
    propose_change,
)
from app.services.calendar_read import list_events
from app.services.contacts import list_contacts
from app.services.gmail import get_email, search_emails
from app.services.language import assistant_system, phrase
from app.services.llm import LOCAL_CHAT_OPTIONS, MODEL, client, generate_reply
from app.services.net_guard import UnsafeURL, validate_public_url
from app.services.web import read_public_page, search_web, user_named_url

logger = logging.getLogger(__name__)


async def _call(func, *args):
    if inspect.iscoroutinefunction(func):
        return await func(*args)
    return await asyncio.to_thread(func, *args)


async def _router(message: str, observations: list[dict]) -> str:
    try:
        response = await client.chat(
            model=MODEL,
            format="json",
            options=LOCAL_CHAT_OPTIONS,
            messages=[
                {"role": "system", "content": router_instructions()},
                {
                    "role": "user",
                    "content": json.dumps(
                        router_payload(message, observations),
                        ensure_ascii=False,
                    ),
                },
            ],
        )
    except Exception as exc:
        if is_llm_unavailable(exc):
            raise LLMUnavailableError from exc
        raise
    return response.message.content or ""


def _memory_for_model(memories) -> list[str]:
    lines = []
    for memory in memories[:20]:
        if isinstance(memory, str) and memory.strip():
            lines.append(memory[:1000])
        elif isinstance(memory, dict):
            content = str(memory.get("content") or "").strip()
            if not content:
                continue
            score = memory.get("score")
            lines.append(f"{content[:1000]} (ilgililik: {score})" if score is not None else content[:1000])
    return lines


def _public_items(items) -> list[dict]:
    public = []
    for item in items[:20]:
        if isinstance(item, dict):
            public.append({
                key: str(value)[:180]
                for key, value in item.items()
                if key in {"name", "emails", "id", "summary", "start", "end", "title", "url", "snippet"}
            })
    return public


def clip_history(history) -> list[dict]:
    clipped = []
    for item in history or []:
        if not isinstance(item, dict):
            continue
        role = item.get("role")
        if role not in {"user", "assistant"}:
            continue
        content = " ".join(str(item.get("content") or "").split())[:500]
        if content:
            clipped.append({"role": role, "content": content})
    return clipped[-8:]


async def _synthesize(message: str, observations: list[dict], history=None) -> str:
    safe_observations = []
    for item in observations:
        tool = item.get("tool")
        if tool in {"gmail_search", "gmail_read", "gmail_draft"}:
            safe_observations.append({
                "tool": tool,
                "query": item.get("query", ""),
                "emails": prepare_emails(
                    item.get("emails", []),
                    include_body=tool in {"gmail_read", "gmail_draft"},
                ),
            })
        elif tool == "memory_search":
            safe_observations.append({
                "tool": "memory_search",
                "memories": _memory_for_model(item.get("memories", [])),
            })
        elif tool == "web_search":
            safe_observations.append({
                "tool": "web_search",
                "results": _public_items(item.get("results", [])),
            })
        elif tool == "web_read":
            safe_observations.append({
                "tool": "web_read",
                "pages": [
                    {
                        "url": str(page.get("url") or "")[:300],
                        "text": str(page.get("text") or "")[:1500],
                    }
                    for page in item.get("pages", [])[:2]
                    if isinstance(page, dict)
                ],
            })
        elif tool in {"contacts_search", "calendar_list"}:
            safe_observations.append({
                "tool": tool,
                "items": _public_items(item.get("items", [])),
            })

    try:
        response = await client.chat(
            model=MODEL,
            options=LOCAL_CHAT_OPTIONS,
            messages=[
                {"role": "system", "content": assistant_system(message, history)},
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "request": message,
                            "history": clip_history(history),
                            "observations": safe_observations,
                        },
                        ensure_ascii=False,
                    ),
                },
            ],
        )
    except Exception as exc:
        if is_llm_unavailable(exc):
            raise LLMUnavailableError from exc
        raise
    return response.message.content or phrase("no_reply", message, history)


async def _finish(message: str, reply: str, record_exchange) -> str:
    if record_exchange is not None:
        try:
            await _call(record_exchange, message, reply)
        except AssertionError:
            raise
        except Exception:
            logger.error("The conversation record could not be written")
    return reply


async def run_agent(
    message: str,
    *,
    router=None,
    reply_fn=None,
    gmail_search=None,
    gmail_read=None,
    memory_search=None,
    memory_save=None,
    web_search=None,
    web_read=None,
    contacts_search=None,
    calendar_list=None,
    calendar_apply=None,
    synthesize=None,
    record_exchange=None,
    history=None,
) -> str:
    text = message.strip()
    if not text:
        return phrase("empty", text, history)

    reply_fn = reply_fn or generate_reply
    gmail_search = gmail_search or search_emails
    gmail_read = gmail_read or get_email
    web_search = web_search or search_web
    web_read = web_read or read_public_page
    contacts_search = contacts_search or list_contacts
    calendar_list = calendar_list or list_events
    calendar_apply = calendar_apply or apply_change
    supplied_synthesize = synthesize

    async def synthesize_with_history(message: str, observations: list[dict]) -> str:
        return await _synthesize(message, observations, history)

    synthesize = supplied_synthesize or synthesize_with_history
    router = router or _router

    if text.lower().startswith(LEGACY_REMEMBER_PREFIX):
        return await reply_fn(message)

    confirmed = pending_confirmation(text)
    if confirmed:
        try:
            result = calendar_apply(confirmed, text)
            if inspect.isawaitable(result):
                result = await result
        except AssertionError:
            raise
        except Exception:
            logger.error("The calendar confirmation could not be applied")
            return await _finish(message, phrase("calendar_failed", text, history), record_exchange)
        reply = result.get("message") if isinstance(result, dict) else phrase("calendar_failed", text, history)
        return await _finish(message, reply, record_exchange)

    is_explicit_save, explicit_content = explicit_save_parts(text)
    if is_explicit_save and not text.lower().startswith(LEGACY_REMEMBER_PREFIX):
        if not explicit_content:
            return phrase("remember_missing", text, history)
        save = memory_save or _default_memory_save
        try:
            await _call(save, explicit_content, "user_note", True)
        except (LLMUnavailableError, AssertionError):
            raise
        except Exception:
            logger.error("The memory save failed")
            return phrase("memory_error", text, history)
        return await _finish(message, phrase("saved", text, history), record_exchange)

    observations: list[dict] = []
    for _ in range(MAX_TOOL_STEPS):
        try:
            raw = await router(message, observations)
        except (LLMUnavailableError, AssertionError):
            raise
        except Exception:
            logger.error("Tool routing failed")
            break

        call = parse_tool_call(raw)
        if call is None or call.tool == "chat":
            break

        if call.tool == "gmail_search":
            arguments = call.arguments
            if not isinstance(arguments, GmailSearchArguments):
                arguments = GmailSearchArguments()
            resolved = resolve_gmail_search(message, arguments)
            query = build_gmail_query(resolved)
            try:
                emails = await _call(gmail_search, query, resolved.limit)
            except AssertionError:
                raise
            except Exception:
                logger.error("The Gmail tool failed")
                return await _finish(message, phrase("gmail_error", text, history), record_exchange)
            if not emails:
                return await _finish(message, phrase("gmail_empty", text, history), record_exchange)
            observations.append({
                "tool": "gmail_search",
                "ok": True,
                "query": query,
                "emails": emails,
                "count": len(emails),
            })
            continue

        if call.tool == "memory_search":
            arguments = call.arguments
            if not isinstance(arguments, MemorySearchArguments):
                arguments = MemorySearchArguments()
            query = (arguments.query or message).strip()
            search = memory_search or _default_memory_search
            try:
                memories = await _call(search, query, arguments.limit)
            except (LLMUnavailableError, AssertionError):
                raise
            except Exception:
                logger.error("The memory tool failed")
                observations.append({
                    "tool": "memory_search",
                    "ok": False,
                    "message": phrase("memory_search_error", message),
                    "count": 0,
                })
                continue
            observations.append({
                "tool": "memory_search",
                "ok": True,
                "memories": memories,
                "count": len(memories) if isinstance(memories, list) else 0,
            })
            continue

        if call.tool == "memory_save":
            observations.append({
                "tool": "memory_save",
                "ok": False,
                "message": phrase("memory_consent", message),
                "count": 0,
            })
            continue

        outcome = await _run_extra_tool(
            call,
            message,
            gmail_read=gmail_read,
            web_search=web_search,
            web_read=web_read,
            contacts_search=contacts_search,
            calendar_list=calendar_list,
        )
        if outcome is None:
            break
        if outcome.get("direct"):
            return await _finish(message, outcome.get("message") or phrase("need_confirm", message), record_exchange)
        observations.append(outcome)
        continue

    productive = [item for item in observations if item.get("ok")]
    if productive:
        try:
            reply = await synthesize(message, productive)
        except (LLMUnavailableError, AssertionError):
            raise
        except Exception:
            logger.error("The tool result could not be summarized")
            reply = phrase("summary_failed", message, history)
        return await _finish(message, reply, record_exchange)
    return await reply_fn(message)


async def _run_extra_tool(call, message: str, **handlers) -> dict | None:
    if call.tool == "gmail_read":
        if not wants_full_email(message):
            return {"tool": "gmail_read", "ok": False, "count": 0}
        arguments = call.arguments if isinstance(call.arguments, GmailReadArguments) else GmailReadArguments()
        if not arguments.message_id:
            return {"tool": "gmail_read", "ok": False, "count": 0}
        try:
            email = await _call(handlers["gmail_read"], arguments.message_id)
        except AssertionError:
            raise
        except Exception:
            logger.error("The Gmail read tool failed")
            return {"tool": "gmail_read", "ok": False, "count": 0, "message": phrase("gmail_read_error", message)}
        return {"tool": "gmail_read", "ok": True, "emails": [email], "count": 1}

    if call.tool == "gmail_draft":
        if not wants_reply_draft(message):
            return {"tool": "gmail_draft", "ok": False, "count": 0}
        return {
            "tool": "gmail_draft",
            "ok": True,
            "emails": [],
            "count": 0,
            "message": phrase("draft_pending", message),
        }

    if call.tool == "web_search":
        arguments = call.arguments if isinstance(call.arguments, WebSearchArguments) else WebSearchArguments()
        query = (arguments.query or message).strip()[:300]
        try:
            results = await _call(handlers["web_search"], query, arguments.limit)
        except AssertionError:
            raise
        except Exception:
            logger.error("The web tool failed")
            return {"tool": "web_search", "ok": False, "count": 0}
        return {"tool": "web_search", "ok": True, "results": results or [], "count": len(results or [])}

    if call.tool == "web_read":
        arguments = call.arguments if isinstance(call.arguments, WebReadArguments) else WebReadArguments()
        if not arguments.url or not user_named_url(message, arguments.url):
            return {"tool": "web_read", "ok": False, "count": 0}
        try:
            validate_public_url(arguments.url)
        except UnsafeURL:
            return {"tool": "web_read", "ok": False, "count": 0}
        try:
            page = await _call(handlers["web_read"], arguments.url)
        except AssertionError:
            raise
        except Exception:
            logger.error("The page read tool failed")
            return {"tool": "web_read", "ok": False, "count": 0}
        return {"tool": "web_read", "ok": True, "pages": [page], "count": 1}

    if call.tool == "contacts_search":
        arguments = call.arguments if isinstance(call.arguments, ContactsSearchArguments) else ContactsSearchArguments()
        try:
            items = await _call(handlers["contacts_search"], arguments.query or "", arguments.limit)
        except AuthorizationRequired:
            return {
                "tool": "contacts_search",
                "ok": False,
                "direct": True,
                "count": 0,
                "message": phrase("contacts_auth", message),
            }
        except AssertionError:
            raise
        except Exception:
            logger.error("The contacts tool failed")
            return {"tool": "contacts_search", "ok": False, "count": 0}
        return {"tool": "contacts_search", "ok": True, "items": items or [], "count": len(items or [])}

    if call.tool == "calendar_list":
        intent = interpret_calendar_request(message)
        arguments = call.arguments if isinstance(call.arguments, CalendarListArguments) else CalendarListArguments()
        days = arguments.days or intent["days"]
        try:
            items = await _call(handlers["calendar_list"], days, 20)
        except AuthorizationRequired:
            return {
                "tool": "calendar_list",
                "ok": False,
                "direct": True,
                "count": 0,
                "message": phrase("calendar_auth", message),
            }
        except AssertionError:
            raise
        except Exception:
            logger.error("The calendar tool failed")
            return {"tool": "calendar_list", "ok": False, "count": 0}
        return {"tool": "calendar_list", "ok": True, "items": items or [], "count": len(items or [])}

    if call.tool == "calendar_propose":
        intent = interpret_calendar_request(message)
        if intent["action"] == "list":
            return {"tool": "calendar_propose", "ok": False, "count": 0}
        arguments = call.arguments if isinstance(call.arguments, CalendarProposeArguments) else CalendarProposeArguments()
        proposal = propose_change(intent["action"], {
            "summary": arguments.summary or "Etkinlik",
            "when": arguments.when or "",
            "event_id": arguments.event_id or "",
        }, message)
        return {"tool": "calendar_propose", "ok": False, "direct": True, "message": proposal["message"], "count": 0}

    return None


async def _default_memory_save(content: str, category: str = "user_note", consent: bool = True):
    from app.services.memory import save_memory

    await save_memory(content, category, consent=consent)


async def _default_memory_search(query: str, limit: int = 5):
    from app.services.memory import search_memories

    return await search_memories(query, limit)
