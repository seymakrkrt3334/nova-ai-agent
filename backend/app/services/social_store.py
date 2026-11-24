from app.services.memory import _connection


async def save_social_messages(messages: list[dict]) -> int:
    saved = 0
    async with _connection() as connection:
        async with connection.cursor() as cursor:
            for item in messages:
                await cursor.execute(
                    """
                    INSERT INTO social_messages (platform, external_id, chat_id, sender, body)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (platform, external_id) DO NOTHING
                    RETURNING id
                    """,
                    (item["platform"], item["external_id"], item["chat_id"], item.get("sender") or "", item["text"]),
                )
                if await cursor.fetchone():
                    saved += 1
    return saved


async def list_social_messages(limit: int = 30):
    async with _connection() as connection:
        async with connection.cursor() as cursor:
            await cursor.execute(
                """
                SELECT platform, chat_id, sender, body, created_at
                FROM social_messages
                ORDER BY id DESC
                LIMIT %s
                """,
                (limit,),
            )
            rows = await cursor.fetchall()
    return [
        {
            "platform": row[0],
            "chat_id": row[1],
            "sender": row[2],
            "text": row[3],
            "created_at": row[4].isoformat() if row[4] else None,
        }
        for row in rows
    ]
