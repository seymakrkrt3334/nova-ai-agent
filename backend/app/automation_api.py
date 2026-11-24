import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.automations import (
    approve_automation,
    create_automation,
    delete_automation,
    list_automation_runs,
    list_automations,
    revoke_automation,
    set_automation_status,
    tick_automations,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/automations", tags=["Automations"])


class AutomationRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    prompt: str = Field(min_length=1, max_length=2000)
    interval_minutes: int = Field(ge=5, le=10080)
    scope: str = Field(default="manual", max_length=40)
    access_grant: str = Field(default="none", max_length=40)
    auto_execute: bool = False
    authorize: bool = False


class StatusRequest(BaseModel):
    status: str = Field(pattern="^(active|paused)$")


class ApprovalRequest(BaseModel):
    confirm: bool


@router.get("")
async def get_automations():
    try:
        return {"automations": await list_automations()}
    except Exception as exc:
        logger.error("Otomasyon listelenemedi: %s", exc.__class__.__name__)
        raise HTTPException(status_code=503, detail="The automation service could not be reached.") from None


@router.post("")
async def add_automation(request: AutomationRequest):
    try:
        return await create_automation(
            request.name.strip(),
            request.prompt.strip(),
            request.interval_minutes,
            request.scope,
            request.access_grant,
            request.auto_execute,
            request.authorize,
        )
    except ValueError:
        raise HTTPException(status_code=422, detail="The automation permission could not be validated.") from None
    except Exception as exc:
        logger.error("Otomasyon kaydedilemedi: %s", exc.__class__.__name__)
        raise HTTPException(status_code=503, detail="The automation service could not be reached.") from None


@router.get("/runs")
async def runs():
    try:
        return {"runs": await list_automation_runs()}
    except Exception as exc:
        logger.error("Automation history could not be read: %s", exc.__class__.__name__)
        raise HTTPException(status_code=503, detail="The automation service could not be reached.") from None


@router.post("/tick")
async def tick():
    try:
        return {"notifications": await tick_automations()}
    except Exception as exc:
        logger.error("The automation check failed: %s", exc.__class__.__name__)
        raise HTTPException(status_code=503, detail="The automation service could not be reached.") from None


@router.post("/{automation_id}/status")
async def update_status(automation_id: int, request: StatusRequest):
    try:
        updated = await set_automation_status(automation_id, request.status)
    except ValueError:
        raise HTTPException(status_code=422, detail="The automation could not be validated.") from None
    except Exception as exc:
        logger.error("The automation status did not change: %s", exc.__class__.__name__)
        raise HTTPException(status_code=503, detail="The automation service could not be reached.") from None
    if not updated:
        raise HTTPException(status_code=404, detail="The automation was not found.")
    return {"status": request.status, "id": automation_id}


@router.post("/{automation_id}/approve")
async def approve(automation_id: int, request: ApprovalRequest):
    if not request.confirm:
        raise HTTPException(status_code=422, detail="Explicit confirmation is required before this can run.")
    try:
        approved = await approve_automation(automation_id)
    except Exception as exc:
        logger.error("Automation approval failed: %s", exc.__class__.__name__)
        raise HTTPException(status_code=503, detail="The automation service could not be reached.") from None
    if approved is None:
        raise HTTPException(status_code=404, detail="No automation is waiting for confirmation.")
    return approved


@router.post("/{automation_id}/revoke")
async def revoke(automation_id: int):
    try:
        updated = await revoke_automation(automation_id)
    except Exception as exc:
        logger.error("The automation permission could not be revoked: %s", exc.__class__.__name__)
        raise HTTPException(status_code=503, detail="The automation service could not be reached.") from None
    if not updated:
        raise HTTPException(status_code=404, detail="The automation was not found.")
    return {"status": "revoked", "id": automation_id}


@router.delete("/{automation_id}")
async def remove(automation_id: int):
    try:
        deleted = await delete_automation(automation_id)
    except Exception as exc:
        logger.error("Otomasyon silinemedi: %s", exc.__class__.__name__)
        raise HTTPException(status_code=503, detail="The automation service could not be reached.") from None
    if not deleted:
        raise HTTPException(status_code=404, detail="The automation was not found.")
    return {"status": "deleted", "id": automation_id}
