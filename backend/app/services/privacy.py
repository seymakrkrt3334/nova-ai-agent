import re

EMAIL_RE = re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", re.IGNORECASE)
PHONE_RE = re.compile(r"(?:\+?\d[\d\s().-]{8,}\d)")
NATIONAL_ID_RE = re.compile(r"\b\d{11}\b")
SENSITIVE_WORDS = (
    "şifre",
    "sifre",
    "parola",
    "password",
    "tc kimlik",
    "kredi kart",
    "credit card",
)


def looks_personal(text: str) -> bool:
    if not isinstance(text, str) or not text.strip():
        return False
    if EMAIL_RE.search(text) or PHONE_RE.search(text) or NATIONAL_ID_RE.search(text):
        return True
    lowered = text.lower()
    return any(word in lowered for word in SENSITIVE_WORDS)


def relevance_score(distance: float) -> float:
    if distance <= 0:
        return 1.0
    if distance >= 1:
        return 0.0
    return round(1.0 - float(distance), 4)


def is_duplicate_distance(distance: float, threshold: float) -> bool:
    return float(distance) <= float(threshold)
