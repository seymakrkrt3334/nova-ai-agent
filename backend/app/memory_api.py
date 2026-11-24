import logging

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field, field_validator

from app.errors import ConsentRequired, LLMUnavailableError, MemoryStoreError
from app.services.memory import (
    delete_memory,
    edit_memory,
    get_chat_history,
    list_memories,
    list_sessions,
    save_memory,
    search_memories,
)
from app.services.session_context import valid_session_id

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/memory", tags=["Memory"])


class MemoryRequest(BaseModel):
    content: str = Field(min_length=1, max_length=16000)
    category: str = Field(default="general", min_length=1, max_length=100)

    @field_validator("content", "category")
    @classmethod
    def strip_value(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("cannot be empty")
        return cleaned


class MemoryEdit(BaseModel):
    content: str = Field(min_length=1, max_length=16000)
    category: str | None = Field(default=None, min_length=1, max_length=100)

    @field_validator("content")
    @classmethod
    def strip_content(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("cannot be empty")
        return cleaned


class MemorySearch(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    limit: int = Field(default=5, ge=1, le=20)

    @field_validator("query")
    @classmethod
    def strip_query(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("cannot be empty")
        return cleaned


def _raise_memory_http(exc: Exception) -> None:
    if isinstance(exc, AssertionError):
        raise exc
    if isinstance(exc, LLMUnavailableError):
        logger.error("The local model could not be used for memory")
        raise HTTPException(
            status_code=503,
            detail="The local AI service could not be reached.",
        ) from None
    if isinstance(exc, MemoryStoreError):
        logger.error("The memory service could not be reached")
        raise HTTPException(
            status_code=503,
            detail="The memory service could not be reached.",
        ) from None
    if isinstance(exc, ConsentRequired):
        raise HTTPException(
            status_code=409,
            detail="Explicit consent is required for personal information.",
        ) from None
    if isinstance(exc, ValueError):
        raise HTTPException(
            status_code=422,
            detail="The memory record could not be validated.",
        ) from None
    logger.error("The memory request could not be completed: %s", exc.__class__.__name__)
    raise HTTPException(
        status_code=500,
        detail="The request could not be completed.",
    ) from None


@router.post("/save")
async def save(request: MemoryRequest):
    try:
        result = await save_memory(request.content, request.category, consent=True)
    except Exception as exc:
        _raise_memory_http(exc)
    if isinstance(result, dict) and result.get("status") == "duplicate":
        return result
    return {"status": "saved"}


@router.patch("/{memory_id}")
async def edit(memory_id: int, request: MemoryEdit):
    try:
        updated = await edit_memory(
            memory_id,
            request.content,
            request.category,
            consent=True,
        )
    except Exception as exc:
        _raise_memory_http(exc)
    if not updated:
        raise HTTPException(status_code=404, detail="The memory record was not found.")
    return {"status": "updated", "id": memory_id}


@router.get("/history")
async def history(
    limit: int = Query(10, ge=1, le=50),
    session_id: str | None = Query(default=None, max_length=64),
):
    try:
        if session_id is None:
            messages = await get_chat_history(limit)
        else:
            selected = valid_session_id(session_id)
            if not selected:
                raise HTTPException(status_code=422, detail="The session could not be validated.")
            messages = await get_chat_history(limit, selected)
    except HTTPException:
        raise
    except Exception as exc:
        _raise_memory_http(exc)
    return {"messages": messages}


@router.get("/sessions")
async def sessions(limit: int = Query(20, ge=1, le=50)):
    try:
        return {"sessions": await list_sessions(limit)}
    except Exception as exc:
        _raise_memory_http(exc)


@router.post("/search")
async def search(request: MemorySearch):
    try:
        results = await search_memories(request.query, request.limit)
    except Exception as exc:
        _raise_memory_http(exc)
    return {"memories": results}


@router.get("/list")
async def get_memories(limit: int = Query(100, ge=1, le=100)):
    try:
        memories = await list_memories(limit)
    except Exception as exc:
        _raise_memory_http(exc)
    return {"memories": memories}


@router.delete("/{memory_id}")
async def remove_memory(memory_id: int):
    try:
        deleted = await delete_memory(memory_id)
    except Exception as exc:
        _raise_memory_http(exc)

    if not deleted:
        raise HTTPException(
            status_code=404,
            detail="The memory record was not found.",
        )

    return {"status": "deleted", "id": memory_id}
