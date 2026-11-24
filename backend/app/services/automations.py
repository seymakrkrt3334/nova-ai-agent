from datetime import datetime, timedelta, timezone

from app.services.automation_policy import execution_plan, run_readonly_job, validate_schedule, window_key
from app.services.memory import _connection


def advance_due_jobs(jobs: list[dict], now: datetime) -> list[dict]:
    """Mark due local jobs as waiting for a person. Do not run tools."""
    waiting = []
    for job in jobs:
        due = job.get("next_run_at")
        if job.get("status") == "active" and isinstance(due, datetime) and due <= now:
            job["status"] = "awaiting_confirmation"
            job["last_status"] = "awaiting_confirmation"
            waiting.append({"id": job["id"], "name": job["name"]})
    return waiting


def next_run(now: datetime, interval_minutes: int) -> datetime:
    return now + timedelta(minutes=interval_minutes)


async def list_automations():
    async with _connection() as connection:
        async with connection.cursor() as cursor:
            await cursor.execute(
                """
                SELECT id, name, prompt, interval_minutes, status, next_run_at, last_status,
                       scope, access_grant, auto_execute, authorized, last_run_at
                FROM automations
                ORDER BY id DESC
                """
            )
            rows = await cursor.fetchall()
    return [_job_row(row) for row in rows]


async def create_automation(
    name: str,
    prompt: str,
    interval_minutes: int,
    scope: str = "manual",
    access_grant: str = "none",
    auto_execute: bool = False,
    authorize: bool = False,
):
    validate_schedule(scope, access_grant, auto_execute, authorize)
    now = datetime.now(timezone.utc)
    async with _connection() as connection:
        async with connection.cursor() as cursor:
            await cursor.execute(
                """
                INSERT INTO automations (
                    name, prompt, interval_minutes, status, next_run_at, last_status,
                    scope, access_grant, auto_execute, authorized
                )
                VALUES (%s, %s, %s, 'active', %s, 'scheduled', %s, %s, %s, %s)
                RETURNING id, name, prompt, interval_minutes, status, next_run_at, last_status,
                          scope, access_grant, auto_execute, authorized, last_run_at
                """,
                (name, prompt, interval_minutes, next_run(now, interval_minutes), scope, access_grant, auto_execute, authorize),
            )
            row = await cursor.fetchone()
    return _job_row(row)


async def set_automation_status(automation_id: int, status: str):
    if status not in {"active", "paused"}:
        raise ValueError("Geçersiz durum.")
    async with _connection() as connection:
        async with connection.cursor() as cursor:
            await cursor.execute(
                """
                UPDATE automations
                SET status = %s, last_status = %s
                WHERE id = %s
                RETURNING id
                """,
                (status, status, automation_id),
            )
            row = await cursor.fetchone()
    return row is not None


async def delete_automation(automation_id: int):
    async with _connection() as connection:
        async with connection.cursor() as cursor:
            await cursor.execute(
                "DELETE FROM automations WHERE id = %s RETURNING id",
                (automation_id,),
            )
            row = await cursor.fetchone()
    return row is not None


async def tick_automations(readers: dict | None = None):
    now = datetime.now(timezone.utc)
    readers = readers if readers is not None else _safe_readers()
    notices = []
    async with _connection() as connection:
        async with connection.cursor() as cursor:
            await cursor.execute(
                """
                SELECT id, name, prompt, interval_minutes, status, next_run_at, last_status,
                       scope, access_grant, auto_execute, authorized
                FROM automations
                WHERE status = 'active' AND next_run_at <= %s
                ORDER BY id
                """,
                (now,),
            )
            due = await cursor.fetchall()
            for row in due:
                job = _job_from_due(row)
                key = window_key(job)
                await cursor.execute(
                    "SELECT 1 FROM automation_runs WHERE window_key = %s",
                    (key,),
                )
                if await cursor.fetchone():
                    await cursor.execute(
                        """
                        UPDATE automations
                        SET next_run_at = %s, last_status = 'skipped_duplicate'
                        WHERE id = %s
                        """,
                        (next_run(now, job["interval_minutes"]), job["id"]),
                    )
                    notices.append({"id": job["id"], "name": job["name"], "status": "skipped_duplicate"})
                    continue
                if execution_plan(job) == "run":
                    try:
                        summary = run_readonly_job(job, readers)
                    except Exception:
                        summary = "Salt okunur iş tamamlanamadı."
                    await cursor.execute(
                        """
                        INSERT INTO automation_runs (automation_id, window_key, status, summary)
                        VALUES (%s, %s, 'completed', %s)
                        """,
                        (job["id"], key, summary[:500]),
                    )
                    await cursor.execute(
                        """
                        UPDATE automations
                        SET next_run_at = %s, last_status = 'completed', last_run_at = %s
                        WHERE id = %s
                        """,
                        (next_run(now, job["interval_minutes"]), now, job["id"]),
                    )
                    notices.append({"id": job["id"], "name": job["name"], "status": "completed"})
                    continue
                await cursor.execute(
                    """
                    UPDATE automations
                    SET status = 'awaiting_confirmation', last_status = 'awaiting_confirmation'
                    WHERE id = %s
                    """,
                    (job["id"],),
                )
                notices.append({"id": job["id"], "name": job["name"]})
    return notices


async def list_automation_runs(limit: int = 30):
    async with _connection() as connection:
        async with connection.cursor() as cursor:
            await cursor.execute(
                """
                SELECT id, automation_id, status, summary, created_at
                FROM automation_runs
                ORDER BY id DESC
                LIMIT %s
                """,
                (limit,),
            )
            rows = await cursor.fetchall()
    return [
        {
            "id": row[0],
            "automation_id": row[1],
            "status": row[2],
            "summary": row[3],
            "created_at": row[4].isoformat() if row[4] else None,
        }
        for row in rows
    ]


async def revoke_automation(automation_id: int) -> bool:
    async with _connection() as connection:
        async with connection.cursor() as cursor:
            await cursor.execute(
                """
                UPDATE automations
                SET auto_execute = false, authorized = false, status = 'paused', last_status = 'revoked'
                WHERE id = %s
                RETURNING id
                """,
                (automation_id,),
            )
            row = await cursor.fetchone()
    return row is not None


def _safe_readers() -> dict:
    def gmail():
        from app.errors import AuthorizationRequired
        from app.services.gmail import inbox_subjects

        try:
            return inbox_subjects()
        except AuthorizationRequired:
            return None

    def calendar():
        from app.errors import AuthorizationRequired
        from app.services.calendar_read import list_events

        try:
            return list_events(1, 10)
        except AuthorizationRequired:
            return None

    def web(query: str):
        return []

    return {"gmail": gmail, "calendar": calendar, "web": web}


async def approve_automation(automation_id: int):
    now = datetime.now(timezone.utc)
    async with _connection() as connection:
        async with connection.cursor() as cursor:
            await cursor.execute(
                """
                SELECT id, name, prompt, interval_minutes, status
                FROM automations
                WHERE id = %s
                """,
                (automation_id,),
            )
            row = await cursor.fetchone()
            if row is None or row[4] != "awaiting_confirmation":
                return None
            await cursor.execute(
                """
                UPDATE automations
                SET status = 'active', last_status = 'approved', next_run_at = %s
                WHERE id = %s
                """,
                (next_run(now, row[3]), automation_id),
            )
    return {"id": row[0], "name": row[1], "prompt": row[2]}


def _job_row(row) -> dict:
    return {
        "id": row[0],
        "name": row[1],
        "prompt": row[2],
        "interval_minutes": row[3],
        "status": row[4],
        "next_run_at": row[5].isoformat() if row[5] else None,
        "last_status": row[6],
        "scope": row[7] if len(row) > 7 and row[7] else "manual",
        "access_grant": row[8] if len(row) > 8 and row[8] else "none",
        "auto_execute": bool(row[9]) if len(row) > 9 else False,
        "authorized": bool(row[10]) if len(row) > 10 else False,
        "last_run_at": row[11].isoformat() if len(row) > 11 and row[11] else None,
    }


def _job_from_due(row) -> dict:
    return {
        "id": row[0],
        "name": row[1],
        "prompt": row[2],
        "interval_minutes": row[3],
        "status": row[4],
        "next_run_at": row[5],
        "scope": row[7] or "manual",
        "access_grant": row[8] or "none",
        "auto_execute": bool(row[9]),
        "authorized": bool(row[10]),
    }
