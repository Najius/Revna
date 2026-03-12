"""Health check and admin endpoints."""

from fastapi import APIRouter

from backend.config import settings
from backend.services.telegram import set_webhook

router = APIRouter(tags=["health"])


@router.get("/health")
async def healthcheck():
    return {"status": "ok", "service": "revna"}


@router.post("/setup/telegram-webhook")
async def setup_telegram_webhook():
    """Register the Telegram webhook. Call once after deployment."""
    if not settings.telegram_webhook_url:
        return {"status": "error", "message": "TELEGRAM_WEBHOOK_URL not configured"}

    success = await set_webhook(settings.telegram_webhook_url)
    if success:
        return {"status": "ok", "webhook_url": settings.telegram_webhook_url}
    return {"status": "error", "message": "Failed to register webhook"}
