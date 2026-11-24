from datetime import datetime

from app.services.language import automation_line

READONLY_ACCESS = {
    "gmail_summary": "gmail_readonly",
    "calendar_reminder": "calendar_readonly",
    "briefing": "memory_readonly",
    "web_research": "web_readonly",
    "reminder": "local",
}


def execution_plan(job: dict) -> str:
    scope = str(job.get("scope") or "manual")
    access = str(job.get("access_grant") or "none")
    if job.get("auto_execute") and job.get("authorized") and READONLY_ACCESS.get(scope) == access:
        return "run"
    return "confirm"


def validate_schedule(scope: str, access_grant: str, auto_execute: bool, authorize: bool) -> None:
    if scope not in {"manual", *READONLY_ACCESS}:
        raise ValueError("Invalid automation scope.")
    if access_grant not in {"none", *READONLY_ACCESS.values()}:
        raise ValueError("Invalid access permission.")
    if not auto_execute:
        return
    if not authorize or execution_plan({
        "scope": scope,
        "access_grant": access_grant,
        "auto_execute": True,
        "authorized": True,
    }) != "run":
        raise ValueError("Automatic execution is allowed only for an explicitly authorized read-only scope.")


def window_key(job: dict) -> str:
    due = job.get("next_run_at")
    stamp = due.isoformat() if isinstance(due, datetime) else "unscheduled"
    return f"{job.get('id')}:{stamp}"[:80]


def run_readonly_job(job: dict, readers: dict | None = None) -> str:
    if execution_plan(job) != "run":
        raise PermissionError("This job cannot run automatically.")
    readers = readers or {}
    scope = job["scope"]
    sample = f"{job.get('prompt') or ''} {job.get('name') or ''}"
    if scope == "reminder":
        return str(job.get("name") or automation_line(sample, "Hatırlatma", "Reminder"))[:120]
    if scope == "gmail_summary":
        reader = readers.get("gmail")
        subjects = reader() if reader else None
        if subjects is None:
            return automation_line(sample, "Gmail izni bağlı değil. Tarayıcı açılmadı.", "Gmail is not connected. No browser was opened.")
        records = "record" if len(subjects) == 1 else "records"
        return automation_line(sample, f"Günlük posta özeti: {len(subjects)} kayıt.", f"Daily mail summary: {len(subjects)} {records}.")
    if scope == "calendar_reminder":
        reader = readers.get("calendar")
        events = reader() if reader else None
        if events is None:
            return automation_line(sample, "Takvim izni bağlı değil. Tarayıcı açılmadı.", "Calendar is not connected. No browser was opened.")
        events_label = "event" if len(events) == 1 else "events"
        return automation_line(sample, f"Takvim hatırlatması: {len(events)} etkinlik.", f"Calendar reminder: {len(events)} {events_label}.")
    if scope == "briefing":
        name = str(job.get("name") or "NOVA")[:80]
        return automation_line(sample, f"Günlük brifing: {name}", f"Daily briefing: {name}")
    if scope == "web_research":
        reader = readers.get("web")
        query = str(job.get("name") or "")[:200]
        results = reader(query) if reader else None
        if results is None:
            return automation_line(sample, "Web araştırması için sağlayıcı bağlı değil.", "No web provider is connected for research.")
        sources = "source" if len(results) == 1 else "sources"
        return automation_line(sample, f"Web araştırması: {len(results)} kaynak.", f"Web research: {len(results)} {sources}.")
    raise PermissionError("A write cannot run automatically.")
