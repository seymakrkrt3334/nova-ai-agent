from contextvars import ContextVar

current_session_id: ContextVar[str | None] = ContextVar("nova_session_id", default=None)


def valid_session_id(value: str | None) -> str | None:
    if value is None:
        return None
    text = value.strip()
    if not text or len(text) > 64:
        return None
    if any(not (character.isalnum() or character in {"-", "_"}) for character in text):
        return None
    return text
