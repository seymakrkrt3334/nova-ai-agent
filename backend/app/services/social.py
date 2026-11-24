import re

OFFICIAL_PLATFORMS = ("telegram", "whatsapp", "instagram")
CHAT_ID_RE = re.compile(r"^[A-Za-z0-9_\-]{1,64}$")

PLATFORM_FACTS = {
    "telegram": {
        "official_api": "Telegram Bot API",
        "personal_inbox": False,
        "can_read": "Yalnızca bota gönderilen iletiler",
        "can_send": "Açık onaydan sonra bota gelen sohbet",
        "account": "BotFather ile oluşturulan bot",
        "cost": "Bot API ücretsizdir. NOVA ücretli bir plan açmaz.",
        "restriction": "Kişisel sohbetler ve resmi olmayan kullanıcı istemcileri desteklenmez.",
    },
    "whatsapp": {
        "official_api": "WhatsApp Business Cloud API",
        "personal_inbox": False,
        "can_read": "Yalnızca işletme numarasına gelen resmi webhook olayları",
        "can_send": "Açık onaydan sonra, 24 saatlik müşteri penceresinde",
        "account": "Meta işletme hesabı ve kayıtlı telefon numarası",
        "cost": "Meta konuşma ücretleri kullanıcı hesabına aittir. NOVA bunları açmaz.",
        "restriction": "Kişisel WhatsApp hesabı bağlanmaz. NOVA genel internete port açmaz; webhook için özel tünel kullanıcının işidir.",
    },
    "instagram": {
        "official_api": "Instagram Messaging API",
        "personal_inbox": False,
        "can_read": "Profesyonel hesaba gelen resmi mesaj olayları",
        "can_send": "Açık onaydan sonra, platformun izin verdiği yanıt penceresinde",
        "account": "Profesyonel Instagram hesabı ve bağlı Facebook sayfası",
        "cost": "Mesajlaşma API'si Meta hesap koşullarına bağlıdır. NOVA reklam veya ücretli API açmaz.",
        "restriction": "Kişisel hesap otomasyonu ve resmi olmayan istemciler yoktur.",
    },
}


def platform_catalog() -> list[dict]:
    return [{"platform": name, **facts} for name, facts in PLATFORM_FACTS.items()]


def clean_chat_id(value: str) -> str:
    cleaned = str(value or "").strip()
    if not CHAT_ID_RE.fullmatch(cleaned):
        raise ValueError("Geçersiz sohbet.")
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
