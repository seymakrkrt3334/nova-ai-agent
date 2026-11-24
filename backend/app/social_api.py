import logging

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.config import settings
from app.services.social import clean_chat_id, parse_official_payload, platform_catalog, template_draft
from app.services.social_store import list_social_messages, save_social_messages

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/social", tags=["Social"])


class IngestRequest(BaseModel):
    platform: str = Field(min_length=1, max_length=20)
    payload: dict


class DraftRequest(BaseModel):
    text: str = Field(min_length=1, max_length=2000)
    use_model: bool = False


class SendRequest(BaseModel):
    platform: str = Field(min_length=1, max_length=20)
    chat_id: str = Field(min_length=1, max_length=64)
    text: str = Field(min_length=1, max_length=2000)
    confirm: bool


def secret_ready(value) -> bool:
    if value is None:
        return False
    return bool(value.get_secret_value().strip())


def social_status() -> dict:
    return {
        "telegram": {
            "configured": secret_ready(settings.telegram_bot_token),
            "official": True,
            "personal_inbox": False,
        },
        "whatsapp": {
            "configured": secret_ready(settings.whatsapp_token) and bool(settings.whatsapp_phone_number_id.strip()),
            "official": True,
            "personal_accounts": False,
            "public_webhook": False,
        },
        "instagram": {
            "configured": secret_ready(settings.instagram_token) and bool(settings.instagram_page_id.strip()),
            "official": True,
            "personal_accounts": False,
            "public_webhook": False,
        },
    }


async def deliver_official(platform: str, chat_id: str, text: str) -> None:
    async with httpx.AsyncClient(timeout=20, follow_redirects=False) as client:
        if platform == "telegram":
            token = settings.telegram_bot_token.get_secret_value().strip() if settings.telegram_bot_token else ""
            if not token:
                raise HTTPException(status_code=409, detail="The Telegram bot is not configured.")
            response = await client.post(
                f"https://api.telegram.org/bot{token}/sendMessage",
                json={"chat_id": chat_id, "text": text},
            )
        elif platform == "whatsapp":
            token = settings.whatsapp_token.get_secret_value().strip() if settings.whatsapp_token else ""
            phone_id = settings.whatsapp_phone_number_id.strip()
            if not phone_id.isdigit():
                raise HTTPException(status_code=409, detail="The WhatsApp Business Cloud API is not configured.")
            if not token or not phone_id:
                raise HTTPException(status_code=409, detail="The WhatsApp Business Cloud API is not configured.")
            response = await client.post(
                f"https://graph.facebook.com/v21.0/{phone_id}/messages",
                headers={"Authorization": f"Bearer {token}"},
                json={
                    "messaging_product": "whatsapp",
                    "to": chat_id,
                    "type": "text",
                    "text": {"body": text},
                },
            )
        elif platform == "instagram":
            token = settings.instagram_token.get_secret_value().strip() if settings.instagram_token else ""
            page_id = settings.instagram_page_id.strip()
            if not page_id.isdigit():
                raise HTTPException(status_code=409, detail="The Instagram Messaging API is not configured.")
            if not token or not page_id:
                raise HTTPException(status_code=409, detail="The Instagram Messaging API is not configured.")
            response = await client.post(
                f"https://graph.facebook.com/v21.0/{page_id}/messages",
                headers={"Authorization": f"Bearer {token}"},
                json={"recipient": {"id": chat_id}, "message": {"text": text}},
            )
        else:
            raise HTTPException(status_code=422, detail="Desteklenmeyen platform.")
    if response.status_code >= 400:
        logger.error("Official social send failed: %s", response.status_code)
        raise HTTPException(status_code=502, detail="The official platform send could not be completed.")


@router.get("/platforms")
def platforms():
    return {"platforms": platform_catalog(), "status": social_status()}


@router.get("/messages")
async def messages(limit: int = 20):
    try:
        return {"messages": await list_social_messages(min(max(limit, 1), 50))}
    except Exception as exc:
        logger.error("Social messages could not be read: %s", exc.__class__.__name__)
        raise HTTPException(status_code=503, detail="The social record service could not be reached.") from None


@router.post("/ingest")
async def ingest(request: IngestRequest):
    try:
        parsed = parse_official_payload(request.platform, request.payload)
        imported = await save_social_messages(parsed)
    except ValueError:
        raise HTTPException(status_code=422, detail="The social event could not be validated.") from None
    except Exception as exc:
        logger.error("Sosyal olay kaydedilemedi: %s", exc.__class__.__name__)
        raise HTTPException(status_code=503, detail="The social record service could not be reached.") from None
    return {"imported": imported}


@router.post("/draft")
async def draft(request: DraftRequest):
    if not request.use_model:
        return {"draft": template_draft(request.text), "sent": False}
    try:
        from app.services.llm import MODEL, client

        from app.services.language import assistant_system

        response = await client.chat(
            model=MODEL,
            options={"num_ctx": 2048, "num_predict": 300, "num_thread": 8},
            messages=[
                {
                    "role": "system",
                    "content": assistant_system(
                        request.text,
                        extra="Write a short reply draft. Do not send it. Do not call tools.",
                    ),
                },
                {"role": "user", "content": request.text[:1000]},
            ],
        )
    except Exception as exc:
        logger.error("The social draft could not be produced: %s", exc.__class__.__name__)
        raise HTTPException(status_code=503, detail="The draft could not be produced.") from None
    return {"draft": (response.message.content or template_draft(request.text))[:2000], "sent": False}


@router.post("/send")
async def send(request: SendRequest):
    if not request.confirm:
        raise HTTPException(status_code=422, detail="Explicit confirmation is required before sending.")
    try:
        chat_id = clean_chat_id(request.chat_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="The chat could not be validated.") from None
    try:
        await deliver_official(request.platform, chat_id, request.text.strip())
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Social send error: %s", exc.__class__.__name__)
        raise HTTPException(status_code=502, detail="The official platform send could not be completed.") from None
    return {"status": "sent", "platform": request.platform}


@router.post("/telegram/poll")
async def telegram_poll():
    if not secret_ready(settings.telegram_bot_token):
        raise HTTPException(status_code=409, detail="The Telegram bot is not configured.")
    token = settings.telegram_bot_token.get_secret_value().strip()
    try:
        async with httpx.AsyncClient(timeout=20, follow_redirects=False) as client:
            response = await client.get(f"https://api.telegram.org/bot{token}/getUpdates", params={"timeout": 0})
        payload = response.json()
    except Exception as exc:
        logger.error("Telegram could not be read: %s", exc.__class__.__name__)
        raise HTTPException(status_code=503, detail="Telegram could not be read.") from None
    imported = 0
    for update in payload.get("result") or []:
        try:
            parsed = parse_official_payload("telegram", update)
            imported += await save_social_messages(parsed)
        except Exception:
            logger.error("The Telegram event was skipped")
    return {"imported": imported}
