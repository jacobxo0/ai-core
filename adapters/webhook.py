"""Webhook adapter — FastAPI router that accepts incoming webhook-triggered commands.

Mount on the main app with app.include_router(webhook_router).
Optional auth: set WEBHOOK_TOKEN env var; callers must send
  Authorization: Bearer <token>
"""
import logging
import os
from typing import Any, Callable, Optional

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhook", tags=["webhook"])

_run_fn: Callable | None = None
_token: str | None = os.getenv("WEBHOOK_TOKEN")


def set_run_fn(fn: Callable) -> None:
    """Inject the orchestrator's _run_command function. Called at app startup."""
    global _run_fn
    _run_fn = fn


class WebhookPayload(BaseModel):
    command: str
    arguments: dict[str, Any] = {}
    request_id: Optional[str] = None
    source: Optional[str] = None  # informational: webhook source identifier


@router.post("/trigger", summary="Trigger a tool via webhook")
def trigger(
    payload: WebhookPayload,
    authorization: Optional[str] = Header(None),
) -> Any:
    # Auth check
    if _token:
        if not authorization or authorization != f"Bearer {_token}":
            logger.warning("webhook_auth_failure source=%s", payload.source)
            raise HTTPException(status_code=401, detail="Unauthorized")

    if _run_fn is None:
        raise HTTPException(status_code=503, detail="Runner not initialised")

    request_id = payload.request_id or f"webhook:{payload.source or 'unknown'}"
    logger.info(
        "webhook_trigger command=%s source=%s request_id=%s",
        payload.command, payload.source, request_id,
    )
    return _run_fn(payload.command, payload.arguments, request_id)


@router.get("/status", summary="Webhook adapter health")
def status() -> dict[str, Any]:
    return {
        "adapter": "webhook",
        "auth_required": bool(_token),
        "runner_configured": _run_fn is not None,
    }
