"""Webhook endpoints — Telegram & Terra."""

import structlog
from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.models.user import User
from backend.services.telegram import handle_start_command, process_reply, send_telegram
from backend.services.wearable import process_terra_webhook, verify_terra_signature

logger = structlog.get_logger()

router = APIRouter(tags=["webhooks"])


@router.post("/telegram")
async def telegram_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    """Receive inbound Telegram messages and route to bot logic."""
    body = await request.json()
    update_id = body.get("update_id")
    message = body.get("message")

    if not message:
        logger.debug("webhook.telegram.no_message", update_id=update_id)
        return {"ok": True}

    chat_id = message.get("chat", {}).get("id")
    text = message.get("text", "").strip()
    username = message.get("from", {}).get("username")

    if not chat_id or not text:
        logger.debug("webhook.telegram.skip", chat_id=chat_id, has_text=bool(text))
        return {"ok": True}

    logger.info("webhook.telegram", update_id=update_id, chat_id=chat_id, text=text[:80])

    # /start command — onboarding
    if text.startswith("/start"):
        await handle_start_command(db, chat_id, username)
        return {"ok": True}

    # Look up user by chat_id
    result = await db.execute(
        select(User).where(User.telegram_chat_id == chat_id)
    )
    user = result.scalar_one_or_none()

    if not user:
        logger.warning("webhook.telegram.unknown_user", chat_id=chat_id)
        await send_telegram(
            chat_id,
            "Je ne te connais pas encore ! Envoie /start pour commencer.",
        )
        return {"ok": True}

    if not user.is_active:
        logger.info("webhook.telegram.inactive_user", user_id=str(user.id))
        return {"ok": True}

    # Route to main message processor
    await process_reply(db, user.id, user, text)
    return {"ok": True}


@router.post("/terra")
async def terra_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    """Receive Terra API data pushes (wearable sync)."""
    raw_body = (await request.body()).decode()
    signature = request.headers.get("terra-signature", "")

    if signature and not verify_terra_signature(raw_body, signature):
        logger.warning("webhook.terra.invalid_signature")
        return {"ok": False, "error": "invalid signature"}

    body = await request.json()
    logger.info("webhook.terra", event_type=body.get("type"))

    result = await process_terra_webhook(db, body)
    return {"ok": True, **result}
