import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.agents.agent import run_agent
from app.automation_api import router as automation_router
from app.errors import LLMUnavailableError, MemoryStoreError
from app.gmail_api import router as gmail_router
from app.integrations_api import router as integrations_router
from app.memory_api import router as memory_router
from app.schemas import ChatRequest, ChatResponse, LanguageRequest, LanguageResponse
from app.services.language import response_language
from app.services.automations import tick_automations
from app.services.memory import get_chat_history, save_chat_message
from app.services.security import verify_api_key
from app.services.session_context import current_session_id, valid_session_id
from app.social_api import router as social_router
from app.voice_api import router as voice_router

logger = logging.getLogger(__name__)


async def _automation_loop(stop: asyncio.Event) -> None:
    while not stop.is_set():
        try:
            await asyncio.wait_for(stop.wait(), timeout=60)
            return
        except asyncio.TimeoutError:
            pass
        try:
            await tick_automations()
        except Exception as exc:
            logger.error("The automation loop could not be completed: %s", exc.__class__.__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    stop = asyncio.Event()
    task = asyncio.create_task(_automation_loop(stop))
    try:
        yield
    finally:
        stop.set()
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass


app = FastAPI(
    title="NOVA AI Agent",
    dependencies=[Depends(verify_api_key)],
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5173",
        "http://localhost:5173",
        "http://127.0.0.1:4173",
        "http://localhost:4173",
    ],
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["Content-Type", "X-API-Key"],
)

app.include_router(memory_router)
app.include_router(gmail_router)
app.include_router(integrations_router)
app.include_router(automation_router)
app.include_router(voice_router)
app.include_router(social_router)


async def _record_exchange(user: str, assistant: str) -> None:
    await save_chat_message("user", user)
    await save_chat_message("assistant", assistant)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
async def chat(payload: ChatRequest):
    session = current_session_id.set(valid_session_id(payload.session_id))
    try:
        history = await get_chat_history(limit=8)
        reply = await run_agent(
            payload.message,
            record_exchange=_record_exchange,
            history=history,
        )
    except LLMUnavailableError:
        logger.error("The local model service could not be reached")
        raise HTTPException(
            status_code=503,
            detail="The local AI service could not be reached.",
        ) from None
    except MemoryStoreError:
        logger.error("The memory service could not be reached")
        raise HTTPException(
            status_code=503,
            detail="The memory service could not be reached.",
        ) from None
    except Exception as exc:
        logger.error("The NOVA chat request could not be completed: %s", exc.__class__.__name__)
        raise HTTPException(
            status_code=500,
            detail="The request could not be completed.",
        ) from None
    finally:
        current_session_id.reset(session)

    return ChatResponse(reply=reply, language=response_language(payload.message, history))


@app.post("/language", response_model=LanguageResponse)
def language(payload: LanguageRequest):
    return LanguageResponse(language=response_language(payload.text))
