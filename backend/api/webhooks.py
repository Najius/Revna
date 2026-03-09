"""Webhook endpoints — Telegram & Terra."""

from fastapi import APIRouter, Request

import structlog

logger = structlog.get_logger()

router = APIRouter(tags=["webhooks"])


@router.post("/telegram")
async def telegram_webhook(request: Request):
    """Receive inbound Telegram messages."""
    body = await request.json()
    logger.info("webhook.telegram", update_id=body.get("update_id"))
    # TODO: dispatch to services.telegram
    return {"ok": True}


@router.post("/terra")
async def terra_webhook(request: Request):
    """Receive Terra API data pushes (wearable sync)."""
    body = await request.json()
    logger.info("webhook.terra", event_type=body.get("type"))
    # TODO: dispatch to services.wearable
    return {"ok": True}
