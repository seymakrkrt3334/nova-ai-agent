import re
import secrets

from app.services.language import calendar_proposal, phrase

CONFIRM_WORDS = ("onaylıyorum", "onayliyorum", "confirm")
_PENDING: dict[str, dict] = {}


def interpret_calendar_request(message: str) -> dict:
    text = message.lower()
    create_phrases = (
        "toplantı oluştur",
        "toplanti olustur",
        "etkinlik oluştur",
        "etkinlik olustur",
        "takvime ekle",
        "create event",
        "schedule a",
    )
    update_phrases = ("ertele", "güncelle", "guncelle", "update event", "değiştir", "degistir")
    delete_phrases = ("etkinliği sil", "etkinligi sil", "toplantıyı sil", "toplanti sil", "delete event", "iptal et")
    if any(phrase in text for phrase in delete_phrases):
        action = "delete"
    elif any(phrase in text for phrase in update_phrases):
        action = "update"
    elif any(phrase in text for phrase in create_phrases):
        action = "create"
    else:
        action = "list"
    if any(phrase in text for phrase in ("bugün", "bugun", "today", "yarın", "yarin", "tomorrow")):
        days = 1
    elif any(phrase in text for phrase in ("hafta", "week", "weekly")):
        days = 7
    else:
        days = 7
    return {"action": action, "days": days}


def confirmation_matches(message: str, code: str) -> bool:
    text = message.lower()
    if not code or code.lower() not in text:
        return False
    return any(word in text for word in CONFIRM_WORDS)


def propose_change(action: str, payload: dict, message: str = "") -> dict:
    if action not in {"create", "update", "delete"}:
        raise ValueError("Invalid calendar action.")
    clean = {
        "summary": " ".join(str(payload.get("summary") or "Etkinlik").split())[:180],
        "when": " ".join(str(payload.get("when") or "").split())[:120],
        "event_id": re.sub(r"[^A-Za-z0-9_-]", "", str(payload.get("event_id") or ""))[:64],
    }
    code = secrets.token_hex(3)
    _PENDING[code] = {"action": action, "payload": clean}
    return {
        "ok": False,
        "status": "confirmation_required",
        "code": code,
        "message": calendar_proposal(action, code, message),
    }


def apply_change(code: str, message: str, service=None) -> dict:
    pending = _PENDING.get(code)
    if pending is None:
        return {"ok": False, "message": phrase("calendar_missing_code", message)}
    if not confirmation_matches(message, code):
        return {"ok": False, "message": phrase("calendar_need_confirm", message)}
    if service is None:
        return {"ok": False, "message": phrase("calendar_no_scope", message)}
    service(pending["action"], pending["payload"])
    _PENDING.pop(code, None)
    return {"ok": True, "message": phrase("calendar_applied", message)}


def pending_confirmation(message: str) -> str | None:
    for code in list(_PENDING):
        if confirmation_matches(message, code):
            return code
    return None


def clear_pending() -> None:
    _PENDING.clear()
