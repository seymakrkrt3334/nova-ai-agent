import logging

from fastapi import APIRouter, HTTPException, Query

from app.services.gmail import get_email, search_email_page, search_emails

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/gmail",
    tags=["Gmail"],
)


def _emails(query: str, limit: int):
    try:
        return search_emails(query, limit)
    except AssertionError:
        raise
    except ValueError:
        raise HTTPException(
            status_code=422,
            detail="The search could not be validated.",
        ) from None
    except Exception as exc:
        logger.error("The Gmail search failed: %s", exc.__class__.__name__)
        raise HTTPException(
            status_code=503,
            detail="The Gmail service could not be reached.",
        ) from None


@router.get("/inbox")
def inbox(limit: int = Query(10, ge=1, le=50)):
    return {"emails": _emails("in:inbox", limit)}


@router.get("/unread")
def unread(limit: int = Query(10, ge=1, le=50)):
    return {"emails": _emails("is:unread", limit)}


@router.get("/search")
def search(
    q: str = Query(min_length=1, max_length=500),
    limit: int = Query(10, ge=1, le=50),
    page_token: str | None = Query(default=None, max_length=256),
):
    try:
        page = search_email_page(q, limit, page_token=page_token)
    except AssertionError:
        raise
    except ValueError:
        raise HTTPException(status_code=422, detail="The search could not be validated.") from None
    except Exception as exc:
        logger.error("The Gmail search failed: %s", exc.__class__.__name__)
        raise HTTPException(status_code=503, detail="The Gmail service could not be reached.") from None
    return page


@router.get("/message/{message_id}")
def message(message_id: str):
    try:
        return {"email": get_email(message_id)}
    except AssertionError:
        raise
    except ValueError:
        raise HTTPException(status_code=422, detail="The message could not be validated.") from None
    except Exception as exc:
        logger.error("The Gmail message could not be read: %s", exc.__class__.__name__)
        raise HTTPException(status_code=503, detail="The Gmail service could not be reached.") from None
