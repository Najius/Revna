"""Health check and admin endpoints."""

import datetime
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func as sa_func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import settings
from backend.database import get_db
from backend.models.conversation import Conversation
from backend.models.feeling import Feeling
from backend.models.health_data import HealthSnapshot
from backend.models.notification import NotificationSent
from backend.models.user import User
from backend.services.telegram import set_webhook

router = APIRouter(tags=["health"])


@router.get("/health")
async def healthcheck():
    return {"status": "ok", "service": "revna"}


# ─── Admin endpoints ──────────────────────────────────────────────────────


@router.get("/admin/stats")
async def admin_stats(db: AsyncSession = Depends(get_db)):
    """Global dashboard summary."""
    # Total users
    total = (await db.execute(
        select(sa_func.count(User.id)).where(User.is_active.is_(True))
    )).scalar() or 0

    # Connected users
    garmin_count = (await db.execute(
        select(sa_func.count(User.id)).where(
            User.is_active.is_(True), User.garmin_email.isnot(None)
        )
    )).scalar() or 0

    google_count = (await db.execute(
        select(sa_func.count(User.id)).where(
            User.is_active.is_(True), User.google_refresh_token.isnot(None)
        )
    )).scalar() or 0

    # Users with data in last 7 days
    week_ago = datetime.date.today() - datetime.timedelta(days=7)
    active_with_data = (await db.execute(
        select(sa_func.count(sa_func.distinct(HealthSnapshot.user_id))).where(
            HealthSnapshot.date >= week_ago
        )
    )).scalar() or 0

    # Notifications today
    today_start = datetime.datetime.combine(
        datetime.date.today(), datetime.time.min, tzinfo=datetime.timezone.utc
    )
    notifs_today = (await db.execute(
        select(sa_func.count(NotificationSent.id)).where(
            NotificationSent.sent_at >= today_start
        )
    )).scalar() or 0

    # Notifications this week
    week_start = datetime.datetime.combine(
        week_ago, datetime.time.min, tzinfo=datetime.timezone.utc
    )
    notifs_week = (await db.execute(
        select(sa_func.count(NotificationSent.id)).where(
            NotificationSent.sent_at >= week_start
        )
    )).scalar() or 0

    # Total conversations
    total_messages = (await db.execute(
        select(sa_func.count(Conversation.id))
    )).scalar() or 0

    return {
        "total_users": total,
        "active_with_data": active_with_data,
        "connected_garmin": garmin_count,
        "connected_google_fit": google_count,
        "notifications_today": notifs_today,
        "notifications_week": notifs_week,
        "total_messages": total_messages,
    }


@router.get("/admin/users")
async def list_users(db: AsyncSession = Depends(get_db)):
    """List all users with connection status and latest data."""
    result = await db.execute(
        select(User).where(User.is_active.is_(True)).order_by(User.created_at.desc())
    )
    users = list(result.scalars().all())

    output = []
    for user in users:
        snap_result = await db.execute(
            select(HealthSnapshot)
            .where(HealthSnapshot.user_id == user.id)
            .order_by(HealthSnapshot.date.desc())
            .limit(1)
        )
        snapshot = snap_result.scalar_one_or_none()

        # Count conversations
        msg_count = (await db.execute(
            select(sa_func.count(Conversation.id)).where(
                Conversation.user_id == user.id
            )
        )).scalar() or 0

        user_data = {
            "id": str(user.id),
            "name": user.name,
            "telegram_username": user.telegram_username,
            "wearable_type": user.wearable_type,
            "has_garmin": user.garmin_email is not None,
            "has_google_fit": user.google_refresh_token is not None,
            "message_count": msg_count,
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


@router.get("/admin/users/{user_id}/detail")
async def user_detail(user_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Detailed view of a single user."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Last 7 days of snapshots
    week_ago = datetime.date.today() - datetime.timedelta(days=7)
    snaps = await db.execute(
        select(HealthSnapshot)
        .where(HealthSnapshot.user_id == user_id, HealthSnapshot.date >= week_ago)
        .order_by(HealthSnapshot.date.desc())
    )
    snapshots = [
        {
            "date": str(s.date),
            "sleep_score": s.sleep_score,
            "body_battery": s.body_battery,
            "resting_heart_rate": s.resting_heart_rate,
            "hrv_status": s.hrv_status,
            "avg_stress": s.avg_stress,
            "total_steps": s.total_steps,
            "total_sleep_minutes": s.total_sleep_minutes,
            "active_minutes": s.active_minutes,
            "spo2_avg": s.spo2_avg,
        }
        for s in snaps.scalars().all()
    ]

    # Last 10 notifications
    notifs = await db.execute(
        select(NotificationSent)
        .where(NotificationSent.user_id == user_id)
        .order_by(NotificationSent.sent_at.desc())
        .limit(10)
    )
    notifications = [
        {
            "type": n.notif_type,
            "message": (n.message or "")[:150],
            "sent_at": str(n.sent_at),
            "success": n.success,
        }
        for n in notifs.scalars().all()
    ]

    # Last 10 conversations
    convos = await db.execute(
        select(Conversation)
        .where(Conversation.user_id == user_id)
        .order_by(Conversation.created_at.desc())
        .limit(10)
    )
    conversations = [
        {
            "role": c.role,
            "text": c.text[:200],
            "msg_type": c.msg_type,
            "created_at": str(c.created_at),
        }
        for c in convos.scalars().all()
    ]

    # Last 5 feelings
    feels = await db.execute(
        select(Feeling)
        .where(Feeling.user_id == user_id)
        .order_by(Feeling.created_at.desc())
        .limit(5)
    )
    feelings = [
        {
            "mood": f.mood,
            "energy": f.energy,
            "pain": f.pain,
            "sentiment": f.sentiment,
            "needs_attention": f.needs_attention,
            "raw_text": (f.raw_text or "")[:100],
            "created_at": str(f.created_at),
        }
        for f in feels.scalars().all()
    ]

    return {
        "user": {
            "id": str(user.id),
            "name": user.name,
            "telegram_username": user.telegram_username,
            "telegram_chat_id": user.telegram_chat_id,
            "wearable_type": user.wearable_type,
            "has_garmin": user.garmin_email is not None,
            "has_google_fit": user.google_refresh_token is not None,
            "timezone": user.timezone,
            "language": user.language,
            "coaching_type": user.coaching_type,
            "created_at": str(user.created_at),
        },
        "snapshots": snapshots,
        "notifications": notifications,
        "conversations": conversations,
        "feelings": feelings,
    }


@router.get("/admin/notifications/recent")
async def recent_notifications(db: AsyncSession = Depends(get_db)):
    """Last 20 notifications across all users."""
    result = await db.execute(
        select(NotificationSent, User.name)
        .join(User, NotificationSent.user_id == User.id)
        .order_by(NotificationSent.sent_at.desc())
        .limit(20)
    )
    rows = result.all()

    notifications = [
        {
            "user_name": name,
            "type": n.notif_type,
            "message": (n.message or "")[:120],
            "sent_at": str(n.sent_at),
            "success": n.success,
        }
        for n, name in rows
    ]

    return {"notifications": notifications}


@router.post("/setup/telegram-webhook")
async def setup_telegram_webhook():
    """Register the Telegram webhook. Call once after deployment."""
    if not settings.telegram_webhook_url:
        return {"status": "error", "message": "TELEGRAM_WEBHOOK_URL not configured"}

    success = await set_webhook(settings.telegram_webhook_url)
    if success:
        return {"status": "ok", "webhook_url": settings.telegram_webhook_url}
    return {"status": "error", "message": "Failed to register webhook"}
