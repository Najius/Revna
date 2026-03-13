"""Health check and admin endpoints."""

import datetime

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import settings
from backend.database import get_db
from backend.models.user import User
from backend.models.health_data import HealthSnapshot
from backend.services.telegram import set_webhook

router = APIRouter(tags=["health"])


@router.get("/health")
async def healthcheck():
    return {"status": "ok", "service": "revna"}


@router.get("/admin/users")
async def list_users(db: AsyncSession = Depends(get_db)):
    """List all users with connection status and latest data."""
    result = await db.execute(select(User).where(User.is_active.is_(True)))
    users = list(result.scalars().all())

    output = []
    for user in users:
        # Get latest snapshot
        snap_result = await db.execute(
            select(HealthSnapshot)
            .where(HealthSnapshot.user_id == user.id)
            .order_by(HealthSnapshot.date.desc())
            .limit(1)
        )
        snapshot = snap_result.scalar_one_or_none()

        user_data = {
            "id": str(user.id),
            "name": user.name,
            "telegram_username": user.telegram_username,
            "wearable_type": user.wearable_type,
            "has_garmin": user.garmin_email is not None,
            "has_google_fit": user.google_refresh_token is not None,
            "created_at": str(user.created_at),
        }

        if snapshot:
            user_data["latest_snapshot"] = {
                "date": str(snapshot.date),
                "sleep_score": snapshot.sleep_score,
                "body_battery": snapshot.body_battery,
                "resting_heart_rate": snapshot.resting_heart_rate,
                "hrv_status": snapshot.hrv_status,
                "avg_stress": snapshot.avg_stress,
                "total_steps": snapshot.total_steps,
                "total_sleep_minutes": snapshot.total_sleep_minutes,
            }
        else:
            user_data["latest_snapshot"] = None

        output.append(user_data)

    return {"users": output, "total": len(output)}


@router.post("/setup/telegram-webhook")
async def setup_telegram_webhook():
    """Register the Telegram webhook. Call once after deployment."""
    if not settings.telegram_webhook_url:
        return {"status": "error", "message": "TELEGRAM_WEBHOOK_URL not configured"}

    success = await set_webhook(settings.telegram_webhook_url)
    if success:
        return {"status": "ok", "webhook_url": settings.telegram_webhook_url}
    return {"status": "error", "message": "Failed to register webhook"}
