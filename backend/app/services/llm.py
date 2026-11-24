from ollama import AsyncClient

from app.config import settings
from app.errors import LLMUnavailableError, is_llm_unavailable
from app.services.language import assistant_system, phrase
from app.services.memory import (
    format_memory_context,
    get_chat_history,
    save_chat_message,
    save_memory,
    search_memories,
)

client = AsyncClient(host=settings.ollama_base_url)
MODEL = settings.ollama_model
LOCAL_CHAT_OPTIONS = {"num_ctx": 4096, "num_predict": 400, "num_thread": 8}


async def generate_reply(message: str) -> str:
    text = message.strip()

    if text.lower().startswith("bunu hatırla:"):
        content = text.split(":", 1)[1].strip()

        if not content:
            return phrase("remember_missing", text)

        await save_memory(content, "user_note", consent=True)
        await save_chat_message("user", text)

        reply = phrase("saved", text)
        await save_chat_message("assistant", reply)

        return reply

    memories = await search_memories(text)
    history = await get_chat_history(limit=10)
    memory_context = format_memory_context(memories)

    try:
        response = await client.chat(
            model=MODEL,
            options=LOCAL_CHAT_OPTIONS,
            messages=build_chat_messages(text, history, memory_context),
        )
    except Exception as exc:
        if is_llm_unavailable(exc):
            raise LLMUnavailableError from exc
        raise

    reply = response.message.content or phrase("no_reply", text, history)

    await save_chat_message("user", text)
    await save_chat_message("assistant", reply)

    return reply


def build_chat_messages(message: str, history: list, memory_context: str) -> list[dict]:
    return [
        {
            "role": "system",
            "content": assistant_system(
                message,
                history,
                extra=f"Long-term memory:\n{memory_context}",
            ),
        },
        *history,
        {"role": "user", "content": message},
    ]
