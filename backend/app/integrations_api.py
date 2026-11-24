import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.errors import AuthorizationRequired
from app.services.calendar_flow import apply_change, propose_change
from app.services.calendar_read import list_events
from app.services.contacts import list_contacts
from app.config import settings
from app.services.web import search_web
from app.social_api import social_status
from app.voice_api import voice_ready

logger = logging.getLogger(__name__)
BACKEND_DIR = Path(__file__).resolve().parents[1]

router = APIRouter(tags=["Integrations"])


def _token_ready(name: str) -> bool:
    return (BACKEND_DIR / name).is_file()


@router.get("/integrations/status")
def integration_status():
    return {
        "gmail": {
            "connected": _token_ready("token.json"),
            "scope": "gmail.readonly",
            "setup": "python scripts/authorize_google.py gmail",
        },
        "contacts": {
            "connected": _token_ready("token_contacts.json"),
            "scope": "contacts.readonly",
            "setup": "python scripts/authorize_google.py contacts",
        },
        "calendar": {
            "connected": _token_ready("token_calendar.json"),
            "scope": "calendar.readonly",
            "setup": "python scripts/authorize_google.py calendar",
        },
        "web": {"provider": settings.web_search_provider, "connected": settings.web_search_provider != "disabled"},
        "voice": {
            "ready": voice_ready(),
            "continuous_listening": False,
            "setup": "VOICE_STT_PROVIDER=whisper and a local VOICE_STT_COMMAND. The model file is not downloaded automatically.",
        },
        "social": social_status(),
    }


class CalendarProposal(BaseModel):
    action: str = Field(min_length=1, max_length=20)
    summary: str = Field(default="Etkinlik", max_length=180)
    when: str = Field(default="", max_length=120)
    event_id: str = Field(default="", max_length=64)


class CalendarConfirmation(BaseModel):
    code: str = Field(min_length=4, max_length=16)
    message: str = Field(min_length=1, max_length=200)


@router.get("/contacts")
def contacts(
    q: str = Query("", max_length=200),
    limit: int = Query(10, ge=1, le=30),
):
    try:
        return {"contacts": list_contacts(q, limit)}
    except AuthorizationRequired:
        raise HTTPException(status_code=403, detail="Google Contacts izni gerekli.") from None
    except Exception as exc:
        logger.error("The contacts request failed: %s", exc.__class__.__name__)
        raise HTTPException(status_code=503, detail="The contacts service could not be reached.") from None


@router.get("/calendar/upcoming")
def upcoming(days: int = Query(7, ge=1, le=7)):
    try:
        return {"events": list_events(days, 20)}
    except AuthorizationRequired:
        raise HTTPException(status_code=403, detail="Google Calendar izni gerekli.") from None
    except Exception as exc:
        logger.error("The calendar request failed: %s", exc.__class__.__name__)
        raise HTTPException(status_code=503, detail="The calendar service could not be reached.") from None


@router.post("/calendar/propose")
def propose(proposal: CalendarProposal):
    try:
        return propose_change(proposal.action, proposal.model_dump())
    except ValueError:
        raise HTTPException(status_code=422, detail="The calendar action could not be validated.") from None


@router.post("/calendar/confirm")
def confirm(confirmation: CalendarConfirmation):
    return apply_change(confirmation.code, confirmation.message)


@router.get("/web/search")
async def web_search(q: str = Query(min_length=1, max_length=300)):
    try:
        return {"results": await search_web(q)}
    except ValueError:
        raise HTTPException(status_code=422, detail="The search could not be validated.") from None
    except Exception as exc:
        logger.error("The web search failed: %s", exc.__class__.__name__)
        raise HTTPException(status_code=503, detail="The web search could not be completed.") from None
