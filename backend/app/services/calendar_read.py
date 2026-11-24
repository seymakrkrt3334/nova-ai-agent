from app.errors import AuthorizationRequired


def list_events(days: int = 7, limit: int = 20, service=None) -> list[dict]:
    if service is None:
        raise AuthorizationRequired
    days = 1 if int(days) <= 1 else 7
    limit = min(max(int(limit), 1), 30)
    rows = service(days=days, limit=limit)
    events = []
    for row in rows or []:
        if not isinstance(row, dict):
            continue
        events.append({
            "id": " ".join(str(row.get("id") or "").split())[:64],
            "summary": " ".join(str(row.get("summary") or "").split())[:180],
            "start": " ".join(str(row.get("start") or "").split())[:40],
            "end": " ".join(str(row.get("end") or "").split())[:40],
        })
    return events
