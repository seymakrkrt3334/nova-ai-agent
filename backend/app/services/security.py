import secrets

from fastapi import HTTPException, Security
from fastapi.security import APIKeyHeader
from pydantic import SecretStr

from app.config import settings

api_key_header = APIKeyHeader(
    name="X-API-Key",
    auto_error=False,
)


def secret_text(value: SecretStr | None) -> str | None:
    if value is None:
        return None
    text = value.get_secret_value().strip()
    return text or None


API_KEY = secret_text(settings.nova_api_key)


async def verify_api_key(
    api_key: str | None = Security(api_key_header),
):
    if not API_KEY:
        raise HTTPException(
            status_code=503,
            detail="API key is not configured.",
        )

    if not api_key:
        raise HTTPException(
            status_code=401,
            detail="Invalid API key.",
        )

    try:
        matches = secrets.compare_digest(api_key, API_KEY)
    except Exception:
        matches = False

    if not matches:
        raise HTTPException(
            status_code=401,
            detail="Invalid API key.",
        )

    return True
