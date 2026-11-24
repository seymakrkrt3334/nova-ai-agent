import re

OFFICIAL_PLATFORMS = ("telegram", "whatsapp", "instagram")
CHAT_ID_RE = re.compile(r"^[A-Za-z0-9_\-]{1,64}$")

PLATFORM_FACTS = {
    "telegram": {
        "official_api": "Telegram Bot API",
        "personal_inbox": False,
        "can_read": "Only messages sent to the bot",
        "can_send": "A chat that reached the bot, after explicit confirmation",
        "account": "A bot created with BotFather",
        "cost": "The Bot API is free. NOVA does not enable a paid plan.",
        "restriction": "Personal chats and unofficial user clients are not supported.",
    },
    "whatsapp": {
        "official_api": "WhatsApp Business Cloud API",
        "personal_inbox": False,
        "can_read": "Only official webhook events sent to the business number",
        "can_send": "Inside the 24-hour customer window, after explicit confirmation",
        "account": "A Meta business account and a registered phone number",
        "cost": "Meta conversation fees belong to the user's account. NOVA does not enable them.",
        "restriction": "A personal WhatsApp account is not connected. NOVA does not open a public port; a private tunnel for the webhook is the user's choice.",
    },
    "instagram": {
        "official_api": "Instagram Messaging API",
        "personal_inbox": False,
        "can_read": "Official message events sent to the professional account",
        "can_send": "Inside the reply window the platform allows, after explicit confirmation",
        "account": "A professional Instagram account and a linked Facebook page",
        "cost": "The messaging API follows Meta account terms. NOVA does not enable ads or a paid API.",
        "restriction": "There is no personal-account automation and no unofficial client.",
    },
}


def platform_catalog() -> list[dict]:
    return [{"platform": name, **facts} for name, facts in PLATFORM_FACTS.items()]


def clean_chat_id(value: str) -> str:
    cleaned = str(value or "").strip()
    if not CHAT_ID_RE.fullmatch(cleaned):
        raise ValueError("Invalid chat.")
    return cleaned


def normalize_telegram_update(update: dict) -> dict | None:
    if not isinstance(update, dict):
        return None
    message = update.get("message") if isinstance(update.get("message"), dict) else None
    if message is None and isinstance(update.get("edited_message"), dict):
        message = update["edited_message"]
    if not isinstance(message, dict):
        return None
    text = " ".join(str(message.get("text") or "").split())
    chat = message.get("chat") if isinstance(message.get("chat"), dict) else {}
    external_id = str(update.get("update_id") or message.get("message_id") or "")
    chat_id = str(chat.get("id") or "")
    if not text or not external_id or not chat_id:
        return None
    sender = message.get("from") if isinstance(message.get("from"), dict) else {}
    return {
        "platform": "telegram",
        "external_id": external_id[:128],
        "chat_id": chat_id[:64],
        "sender": str(sender.get("username") or sender.get("first_name") or "")[:80],
        "text": text[:2000],
    }


def normalize_whatsapp_webhook(payload: dict) -> list[dict]:
    messages = []
    if not isinstance(payload, dict):
        return messages
    for entry in payload.get("entry") or []:
        if not isinstance(entry, dict):
            continue
        for change in entry.get("changes") or []:
            value = change.get("value") if isinstance(change, dict) else None
            if not isinstance(value, dict):
                continue
            for item in value.get("messages") or []:
                if not isinstance(item, dict) or item.get("type") not in {None, "text"}:
                    continue
                body = item.get("text") if isinstance(item.get("text"), dict) else {}
                text = " ".join(str(body.get("body") or "").split())
                if not text or not item.get("id"):
                    continue
                messages.append({
                    "platform": "whatsapp",
                    "external_id": str(item.get("id"))[:128],
                    "chat_id": str(item.get("from") or "")[:64],
                    "sender": str(item.get("from") or "")[:80],
                    "text": text[:2000],
                })
    return messages


def normalize_instagram_webhook(payload: dict) -> list[dict]:
    messages = []
    if not isinstance(payload, dict) or payload.get("object") not in {None, "instagram"}:
        return messages
    for entry in payload.get("entry") or []:
        if not isinstance(entry, dict):
            continue
        for event in entry.get("messaging") or []:
            if not isinstance(event, dict):
                continue
            message = event.get("message") if isinstance(event.get("message"), dict) else {}
            text = " ".join(str(message.get("text") or "").split())
            if not text or not message.get("mid"):
                continue
            sender = event.get("sender") if isinstance(event.get("sender"), dict) else {}
            messages.append({
                "platform": "instagram",
                "external_id": str(message.get("mid"))[:128],
                "chat_id": str(sender.get("id") or "")[:64],
                "sender": str(sender.get("id") or "")[:80],
                "text": text[:2000],
            })
    return messages


def parse_official_payload(platform: str, payload: dict) -> list[dict]:
    if platform == "telegram":
        item = normalize_telegram_update(payload)
        return [item] if item else []
    if platform == "whatsapp":
        return normalize_whatsapp_webhook(payload)
    if platform == "instagram":
        return normalize_instagram_webhook(payload)
    raise ValueError("Desteklenmeyen platform.")


def template_draft(inbound: str) -> str:
    from app.services.language import phrase

    clipped = " ".join(str(inbound or "").split())[:500]
    label = "Alıntı" if phrase("social_draft", inbound).startswith("Taslak") else "Quote"
    return f"{phrase('social_draft', inbound)}\n\n{label}: {clipped}"
