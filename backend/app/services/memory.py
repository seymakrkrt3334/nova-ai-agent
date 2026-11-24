import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import psycopg
from ollama import AsyncClient

from app.config import settings
from app.errors import ConsentRequired, LLMUnavailableError, MemoryStoreError, is_llm_unavailable
from app.services.privacy import is_duplicate_distance, looks_personal, relevance_score
from app.services.session_context import current_session_id

logger = logging.getLogger(__name__)

EMBEDDING_DIM = 768
MAX_MEMORY_CHARS = 16000
MAX_CATEGORY_CHARS = 100
MAX_SEARCH_RESULTS = 20

client = AsyncClient(host=settings.ollama_base_url)
EMBED_MODEL = settings.ollama_embed_model


def database_url() -> str:
    if settings.database_url is None:
        raise MemoryStoreError
    value = settings.database_url.get_secret_value().strip()
    if not value:
        raise MemoryStoreError
    return value


def vector_string(embedding) -> str:
    if not isinstance(embedding, (list, tuple)) or len(embedding) != EMBEDDING_DIM:
        raise ValueError("Invalid embedding vector.")

    numbers: list[str] = []
    for value in embedding:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError("Invalid embedding vector.")
        number = float(value)
        if number != number or number in (float("inf"), float("-inf")):
            raise ValueError("Invalid embedding vector.")
        numbers.append(repr(number))
    return "[" + ",".join(numbers) + "]"


def _clean_text(value: str, limit: int, empty_message: str) -> str:
    if not isinstance(value, str):
        raise ValueError(empty_message)
    text = value.strip()
    if not text:
        raise ValueError(empty_message)
    if len(text) > limit:
        raise ValueError(empty_message)
    return text


def validate_memory(content: str, category: str) -> tuple[str, str]:
    return (
        _clean_text(content, MAX_MEMORY_CHARS, "Invalid memory content."),
        _clean_text(category, MAX_CATEGORY_CHARS, "Invalid category."),
    )


def validate_search_query(query: str) -> str:
    return _clean_text(query, 2000, "Invalid search.")


def validate_limit(limit: int, maximum: int) -> int:
    if isinstance(limit, bool) or not isinstance(limit, int):
        raise ValueError("Invalid limit.")
    if limit < 1 or limit > maximum:
        raise ValueError("Invalid limit.")
    return limit


async def get_embedding(text: str):
    try:
        result = await client.embed(model=EMBED_MODEL, input=text)
    except Exception as exc:
        if is_llm_unavailable(exc):
            raise LLMUnavailableError from exc
        raise
    embeddings = getattr(result, "embeddings", None)
    if not embeddings:
        raise LLMUnavailableError
    return embeddings[0]


@asynccontextmanager
async def _connection() -> AsyncIterator[psycopg.AsyncConnection]:
    url = database_url()
    try:
        connection = await psycopg.AsyncConnection.connect(url)
    except Exception:
        logger.error("Could not connect to the memory database")
        raise MemoryStoreError from None
    try:
        async with connection:
            yield connection
    except MemoryStoreError:
        raise
    except Exception:
        logger.error("The memory database operation failed")
        raise MemoryStoreError from None


def _distance_limit(max_distance: float | None) -> float:
    value = settings.memory_max_distance if max_distance is None else max_distance
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("Invalid similarity threshold.")
    if value <= 0 or value > 1.5:
        raise ValueError("Invalid similarity threshold.")
    return float(value)


async def save_memory(
    content: str,
    category: str = "general",
    consent: bool = False,
    durability: str = "long_term",
):
    content, category = validate_memory(content, category)
    if durability not in {"long_term", "short_term"}:
        raise ValueError("Invalid memory lifetime.")
    if looks_personal(content) and not consent:
        raise ConsentRequired
    embedding = await get_embedding(content)
    literal = vector_string(embedding)
    threshold = float(settings.memory_duplicate_distance)

    async with _connection() as connection:
        async with connection.cursor() as cursor:
            await cursor.execute(
                """
                SELECT id, (embedding <=> %s::vector) AS distance
                FROM memories
                WHERE embedding IS NOT NULL
                ORDER BY embedding <=> %s::vector
                LIMIT 1
                """,
                (literal, literal),
            )
            nearest = await cursor.fetchone()
        if nearest is not None and is_duplicate_distance(nearest[1], threshold):
            return {"status": "duplicate", "id": int(nearest[0])}
        async with connection.cursor() as cursor:
            await cursor.execute(
                """
                INSERT INTO memories (content, category, embedding, durability)
                VALUES (%s, %s, %s::vector, %s)
                RETURNING id
                """,
                (content, category, literal, durability),
            )
            created = await cursor.fetchone()
    return {"status": "saved", "id": int(created[0]) if created else None}


async def search_memories(query: str, limit: int = 5, max_distance: float | None = None):
    query = validate_search_query(query)
    limit = validate_limit(limit, MAX_SEARCH_RESULTS)
    distance_limit = _distance_limit(max_distance)
    embedding = await get_embedding(query)
    literal = vector_string(embedding)

    async with _connection() as connection:
        async with connection.cursor() as cursor:
            await cursor.execute(
                """
                SELECT id, content, category, source, durability,
                       (embedding <=> %s::vector) AS distance
                FROM memories
                WHERE embedding IS NOT NULL
                  AND (embedding <=> %s::vector) <= %s
                  AND (
                        COALESCE(durability, 'long_term') = 'long_term'
                        OR created_at > now() - interval '7 days'
                  )
                ORDER BY distance
                LIMIT %s
                """,
                (literal, literal, distance_limit, limit),
            )
            rows = await cursor.fetchall()

    return [
        {
            "id": row[0],
            "content": row[1],
            "category": row[2],
            "source": row[3],
            "durability": row[4] or "long_term",
            "distance": float(row[5]),
            "score": relevance_score(float(row[5])),
        }
        for row in rows
    ]


def format_memory_context(memories) -> str:
    lines = []
    for item in memories or []:
        if isinstance(item, str) and item.strip():
            lines.append(item.strip())
        elif isinstance(item, dict) and str(item.get("content") or "").strip():
            lines.append(str(item["content"]).strip())
    return "\n".join(lines) if lines else "No records yet."


async def delete_memory(memory_id: int):
    if isinstance(memory_id, bool) or not isinstance(memory_id, int) or memory_id < 1:
        raise ValueError("Invalid memory record.")

    async with _connection() as connection:
        async with connection.cursor() as cursor:
            await cursor.execute(
                "DELETE FROM memories WHERE id = %s RETURNING id",
                (memory_id,),
            )
            deleted = await cursor.fetchone()

    return deleted is not None


async def edit_memory(
    memory_id: int,
    content: str,
    category: str | None = None,
    consent: bool = False,
):
    if isinstance(memory_id, bool) or not isinstance(memory_id, int) or memory_id < 1:
        raise ValueError("Invalid memory record.")
    content, validated_category = validate_memory(content, category or "general")
    if looks_personal(content) and not consent:
        raise ConsentRequired
    embedding = await get_embedding(content)
    literal = vector_string(embedding)

    async with _connection() as connection:
        async with connection.cursor() as cursor:
            if category is None:
                await cursor.execute(
                    """
                    UPDATE memories
                    SET content = %s, embedding = %s::vector, updated_at = now()
                    WHERE id = %s
                    RETURNING id
                    """,
                    (content, literal, memory_id),
                )
            else:
                await cursor.execute(
                    """
                    UPDATE memories
                    SET content = %s, category = %s, embedding = %s::vector, updated_at = now()
                    WHERE id = %s
                    RETURNING id
                    """,
                    (content, validated_category, literal, memory_id),
                )
            updated = await cursor.fetchone()
    return updated is not None


async def list_memories(limit: int = 100, category: str | None = None):
    limit = validate_limit(limit, 100)
    params: list = []
    where = ""
    if category:
        category = _clean_text(category, MAX_CATEGORY_CHARS, "Invalid category.")
        where = "WHERE category = %s"
        params.append(category)
    params.append(limit)
    async with _connection() as connection:
        async with connection.cursor() as cursor:
            await cursor.execute(
                f"""
                SELECT id, content, category, source, durability, created_at
                FROM memories
                {where}
                ORDER BY created_at DESC, id DESC
                LIMIT %s
                """,
                tuple(params),
            )
            rows = await cursor.fetchall()

    return [
        {
            "id": row[0],
            "content": row[1],
            "category": row[2],
            "source": row[3],
            "durability": row[4] or "long_term",
            "created_at": row[5].isoformat() if row[5] else None,
        }
        for row in rows
    ]


async def save_chat_message(role: str, content: str):
    if role not in {"user", "assistant", "system"}:
        raise ValueError("Invalid role.")
    content = _clean_text(content, 100000, "Invalid message.")

    session_id = current_session_id.get()
    async with _connection() as connection:
        await connection.execute(
            """
            INSERT INTO conversations (role, content, session_id)
            VALUES (%s, %s, %s)
            """,
            (role, content, session_id),
        )


async def get_chat_history(limit: int = 10, session_id: str | None = None):
    limit = validate_limit(limit, 50)
    selected = current_session_id.get() if session_id is None else session_id
    params: tuple
    if selected:
        where = "WHERE session_id = %s"
        params = (selected, limit)
    else:
        where = ""
        params = (limit,)
    async with _connection() as connection:
        async with connection.cursor() as cursor:
            await cursor.execute(
                f"""
                SELECT role, content
                FROM (
                    SELECT id, role, content
                    FROM conversations
                    {where}
                    ORDER BY id DESC
                    LIMIT %s
                ) AS recent
                ORDER BY id ASC
                """,
                params,
            )
            rows = await cursor.fetchall()

    return [
        {"role": row[0], "content": row[1]}
        for row in rows
    ]


async def list_sessions(limit: int = 30):
    limit = validate_limit(limit, 50)
    async with _connection() as connection:
        async with connection.cursor() as cursor:
            await cursor.execute(
                """
                SELECT session_id, COUNT(*), MAX(created_at)
                FROM conversations
                GROUP BY session_id
                ORDER BY MAX(created_at) DESC
                LIMIT %s
                """,
                (limit,),
            )
            rows = await cursor.fetchall()
            previews = []
            for session_id, count, updated_at in rows:
                if session_id:
                    await cursor.execute(
                        """
                        SELECT content FROM conversations
                        WHERE session_id = %s
                        ORDER BY id DESC
                        LIMIT 1
                        """,
                        (session_id,),
                    )
                else:
                    await cursor.execute(
                        """
                        SELECT content FROM conversations
                        WHERE session_id IS NULL
                        ORDER BY id DESC
                        LIMIT 1
                        """
                    )
                preview_row = await cursor.fetchone()
                preview = " ".join(str(preview_row[0]).split())[:80] if preview_row else ""
                previews.append({
                    "session_id": session_id,
                    "messages": count,
                    "updated_at": updated_at.isoformat() if updated_at else None,
                    "preview": preview,
                })
    return previews
