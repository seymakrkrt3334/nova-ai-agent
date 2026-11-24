from app.errors import AuthorizationRequired


def list_contacts(query: str = "", limit: int = 20, service=None) -> list[dict]:
    if service is None:
        raise AuthorizationRequired
    limit = min(max(int(limit), 1), 30)
    rows = service(query=query.strip()[:200], limit=limit)
    contacts = []
    for row in rows or []:
        if not isinstance(row, dict):
            continue
        contacts.append({
            "name": " ".join(str(row.get("name") or "").split())[:180],
            "emails": [
                " ".join(str(item).split())[:180]
                for item in (row.get("emails") or [])[:5]
                if str(item).strip()
            ],
        })
    return contacts
