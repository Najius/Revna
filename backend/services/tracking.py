"""Revna — Notification dedup, cooldowns, streaks, effectiveness tracking.

Adapted from coach/tracking.py:
- PostgreSQL (via ORM) replaces JSON file storage
- user_id added to all operations (multi-tenant)
- Redis replaces in-memory sent log for cooldowns
"""

import datetime
import logging
import uuid

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.constants import (
    NOTIFICATION_COOLDOWNS,
    NOTIFICATION_CONFLICT_GROUPS,
    NOTIFICATION_TYPES,
    CONVERSATION_HISTORY_HOURS,
    CONVERSATION_MAX_PER_HOUR,
)
from backend.config import settings
from backend.models.notification import NotificationSent
from backend.models.conversation import Conversation
from backend.models.feeling import Feeling
from backend.models.effectiveness import AdviceEffectiveness
from backend.models.coach_history import CoachHistory

logger = logging.getLogger(__name__)


# ─── Notification deduplication ──────────────────────────────────────────────

async def can_send_notification(
    db: AsyncSession, user_id: uuid.UUID, notif_type: str
) -> bool:
    """Check if a notification can be sent (cooldown + daily + burst + conflicts)."""
    now = datetime.datetime.now(datetime.timezone.utc)

    # 1. Per-type cooldown
    cooldown_secs = NOTIFICATION_COOLDOWNS.get(notif_type, 3600)
    cooldown_since = now - datetime.timedelta(seconds=cooldown_secs)
    result = await db.execute(
        select(NotificationSent)
        .where(
            NotificationSent.user_id == user_id,
            NotificationSent.notif_type == notif_type,
            NotificationSent.sent_at >= cooldown_since,
        )
        .limit(1)
    )
    if result.scalar_one_or_none():
        logger.debug("BLOCKED %s: cooldown %ds", notif_type, cooldown_secs)
        return False

    # 2. Daily limit
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    result = await db.execute(
        select(func.count())
        .select_from(NotificationSent)
        .where(
            NotificationSent.user_id == user_id,
            NotificationSent.sent_at >= today_start,
        )
    )
    daily_count = result.scalar() or 0
    if daily_count >= settings.max_daily_notifications:
        logger.debug("BLOCKED: daily limit %d reached", settings.max_daily_notifications)
        return False

    # 3. Burst limit
    burst_since = now - datetime.timedelta(minutes=settings.burst_window_minutes)
    result = await db.execute(
        select(func.count())
        .select_from(NotificationSent)
        .where(
            NotificationSent.user_id == user_id,
            NotificationSent.sent_at >= burst_since,
        )
    )
    burst_count = result.scalar() or 0
    if burst_count >= settings.max_burst_notifications:
        logger.debug("BLOCKED: burst limit %d in %dmin",
                      settings.max_burst_notifications, settings.burst_window_minutes)
        return False

    # 4. Conflict groups
    blockers = NOTIFICATION_CONFLICT_GROUPS.get(notif_type)
    if blockers:
        conflict_since = now - datetime.timedelta(minutes=30)
        result = await db.execute(
            select(NotificationSent.notif_type)
            .where(
                NotificationSent.user_id == user_id,
                NotificationSent.notif_type.in_(blockers),
                NotificationSent.sent_at >= conflict_since,
            )
            .limit(1)
        )
        blocker = result.scalar_one_or_none()
        if blocker:
            logger.debug("BLOCKED %s: conflicts with recent '%s'", notif_type, blocker)
            return False

    return True


async def record_notification_sent(
    db: AsyncSession, user_id: uuid.UUID, notif_type: str,
    message: str | None = None, success: bool = True,
) -> None:
    """Record that a notification was sent."""
    notif = NotificationSent(
        user_id=user_id,
        notif_type=notif_type,
        message=message,
        success=success,
    )
    db.add(notif)
    await db.commit()
    logger.debug("Recorded %s sent for user %s", notif_type, user_id)


# ─── Feelings ────────────────────────────────────────────────────────────────

async def get_recent_feelings(
    db: AsyncSession, user_id: uuid.UUID, days: int = 3
) -> list[Feeling]:
    """Load recent feelings entries for a user."""
    cutoff = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=days)
    result = await db.execute(
        select(Feeling)
        .where(Feeling.user_id == user_id, Feeling.created_at >= cutoff)
        .order_by(Feeling.created_at.desc())
        .limit(10)
    )
    return list(result.scalars().all())


async def build_feelings_context(db: AsyncSession, user_id: uuid.UUID) -> str:
    """Build context string from recent feelings data for AI prompts."""
    feelings = await get_recent_feelings(db, user_id)
    if not feelings:
        return ""

    lines = ["RESSENTIS RECENTS DU PATIENT (donnees subjectives):"]
    for f in feelings:
        date_str = f.created_at.strftime("%Y-%m-%d") if f.created_at else "?"
        time_str = f.created_at.strftime("%Hh%M") if f.created_at else "?"
        mood = f.mood or "?"
        energy = f.energy or "?"
        pain = f.pain or "?"
        lines.append(f"  [{date_str} {time_str}] Humeur:{mood}, Douleur:{pain}, Energie:{energy}")
        if f.raw_text:
            lines.append(f'    Verbatim: "{f.raw_text[:150]}"')

    return "\n".join(lines)


# ─── Coach History ───────────────────────────────────────────────────────────

async def get_coach_history(
    db: AsyncSession, user_id: uuid.UUID, days: int = 90
) -> list[CoachHistory]:
    """Load coach history entries for a user (last N days)."""
    cutoff = datetime.date.today() - datetime.timedelta(days=days)
    result = await db.execute(
        select(CoachHistory)
        .where(CoachHistory.user_id == user_id, CoachHistory.date >= cutoff)
        .order_by(CoachHistory.date.asc())
    )
    return list(result.scalars().all())


# ─── Conversation Log ────────────────────────────────────────────────────────

async def save_conversation_message(
    db: AsyncSession, user_id: uuid.UUID,
    role: str, text: str, msg_type: str | None = None,
) -> None:
    """Append a message to the conversation log."""
    conv = Conversation(
        user_id=user_id,
        role=role,
        text=text[:2000],
        msg_type=msg_type,
    )
    db.add(conv)
    await db.commit()


async def get_recent_conversations(
    db: AsyncSession, user_id: uuid.UUID, hours: int = CONVERSATION_HISTORY_HOURS,
) -> list[Conversation]:
    """Load conversation messages from the last N hours."""
    cutoff = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=hours)
    result = await db.execute(
        select(Conversation)
        .where(Conversation.user_id == user_id, Conversation.created_at >= cutoff)
        .order_by(Conversation.created_at.asc())
    )
    return list(result.scalars().all())


async def can_reply_conversation(db: AsyncSession, user_id: uuid.UUID) -> bool:
    """Check conversation rate limits (max messages per hour)."""
    one_hour_ago = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=1)
    result = await db.execute(
        select(func.count())
        .select_from(Conversation)
        .where(
            Conversation.user_id == user_id,
            Conversation.role == "coach",
            Conversation.created_at >= one_hour_ago,
        )
    )
    count = result.scalar() or 0
    if count >= CONVERSATION_MAX_PER_HOUR:
        logger.debug("Rate limit: %d msgs in last hour for user %s", count, user_id)
        return False
    return True


async def build_conversation_context(
    db: AsyncSession, user_id: uuid.UUID, max_messages: int = 10,
) -> str:
    """Format recent conversation history for Claude prompts."""
    messages = await get_recent_conversations(db, user_id)
    if not messages:
        return ""
    recent = messages[-max_messages:]
    lines = ["HISTORIQUE CONVERSATION RECENTE:"]
    for msg in recent:
        time_str = msg.created_at.strftime("%Hh%M") if msg.created_at else "?"
        role_label = "Coach" if msg.role == "coach" else "Patient"
        text = msg.text[:300] + "..." if len(msg.text) > 300 else msg.text
        lines.append(f"[{role_label} {time_str}] {text}")
    return "\n".join(lines)


# ─── Streak tracking ─────────────────────────────────────────────────────────

def compute_workout_streak(history_entries: list[CoachHistory]) -> tuple[int, int]:
    """Compute current workout streak and best streak from coach history.

    Returns (current_streak, best_streak).
    """
    if not history_entries:
        return 0, 0

    # Current streak: count backwards from most recent day
    current = 0
    for entry in reversed(history_entries):
        bilan = entry.health_bilan or {}
        completed = bilan.get("completed_workouts", 0)
        total = bilan.get("total_workouts", 0)
        if total > 0 and completed > 0:
            current += 1
        else:
            break

    # Best streak: scan forward
    best = 0
    streak = 0
    for entry in history_entries:
        bilan = entry.health_bilan or {}
        completed = bilan.get("completed_workouts", 0)
        total = bilan.get("total_workouts", 0)
        if total > 0 and completed > 0:
            streak += 1
            best = max(best, streak)
        else:
            streak = 0

    return current, best


def build_streak_context(history_entries: list[CoachHistory]) -> str:
    """Build a motivational context string about workout streaks."""
    current, best = compute_workout_streak(history_entries)
    if current == 0:
        return ""

    if current >= 5:
        return (
            f"SERIE EN COURS: {current} jours consecutifs de seances completees! "
            f"(record: {best}j) — Celebre cette constance avec fierte."
        )
    elif current >= 3:
        return (
            f"SERIE EN COURS: {current} jours consecutifs! "
            f"Souligne le progres concret."
        )
    elif current >= 1 and best >= 3:
        return (
            f"SERIE ACTUELLE: {current} jour(s). Record: {best}j. "
            f"Encourage positivement."
        )
    return ""


# ─── Advice effectiveness tracking ──────────────────────────────────────────

async def record_advice_given(
    db: AsyncSession, user_id: uuid.UUID, notif_type: str,
    readiness: int | None = None, sleep: int | None = None,
) -> None:
    """Record that advice was given, with 'before' metrics for later comparison."""
    record = AdviceEffectiveness(
        user_id=user_id,
        notif_type=notif_type,
        readiness_before=readiness,
        sleep_before=sleep,
    )
    db.add(record)
    await db.commit()
    logger.debug("Recorded advice: %s (readiness=%s, sleep=%s)", notif_type, readiness, sleep)


async def update_advice_outcomes(
    db: AsyncSession, user_id: uuid.UUID,
    readiness_today: int, sleep_today: int,
) -> None:
    """Fill in 'after' metrics for yesterday's pending advice records."""
    yesterday = datetime.date.today() - datetime.timedelta(days=1)
    yesterday_start = datetime.datetime.combine(yesterday, datetime.time.min, tzinfo=datetime.timezone.utc)
    yesterday_end = datetime.datetime.combine(yesterday, datetime.time.max, tzinfo=datetime.timezone.utc)

    result = await db.execute(
        select(AdviceEffectiveness)
        .where(
            AdviceEffectiveness.user_id == user_id,
            AdviceEffectiveness.recorded_at >= yesterday_start,
            AdviceEffectiveness.recorded_at <= yesterday_end,
            AdviceEffectiveness.readiness_after.is_(None),
        )
    )
    pending = list(result.scalars().all())
    for record in pending:
        record.readiness_after = readiness_today
        record.sleep_after = sleep_today
        record.delta_readiness = readiness_today - (record.readiness_before or 0)

    if pending:
        await db.commit()
        logger.debug("Updated %d effectiveness records with outcomes", len(pending))


async def compute_advice_effectiveness(
    db: AsyncSession, user_id: uuid.UUID,
) -> dict | None:
    """Aggregate effectiveness stats by notification type.

    Returns dict: {notif_type: {count, positive_pct, avg_delta}} or None.
    """
    cutoff = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=90)
    result = await db.execute(
        select(AdviceEffectiveness)
        .where(
            AdviceEffectiveness.user_id == user_id,
            AdviceEffectiveness.readiness_after.isnot(None),
            AdviceEffectiveness.recorded_at >= cutoff,
        )
    )
    records = list(result.scalars().all())
    if len(records) < 5:
        return None

    by_type: dict[str, list[int]] = {}
    for r in records:
        if r.readiness_before is None or r.readiness_after is None:
            continue
        delta = r.readiness_after - r.readiness_before
        by_type.setdefault(r.notif_type or "unknown", []).append(delta)

    stats = {}
    for nt, deltas in by_type.items():
        if len(deltas) < 2:
            continue
        positive = sum(1 for d in deltas if d > 0)
        stats[nt] = {
            "count": len(deltas),
            "positive_pct": round(positive / len(deltas) * 100),
            "avg_delta": round(sum(deltas) / len(deltas), 1),
        }

    return stats if stats else None


async def build_effectiveness_context(db: AsyncSession, user_id: uuid.UUID) -> str:
    """Build context string about which advice types work best."""
    stats = await compute_advice_effectiveness(db, user_id)
    if not stats:
        return ""

    lines = ["EFFICACITE DES CONSEILS (readiness J+1 apres notification):"]
    for nt, s in sorted(stats.items(), key=lambda x: x[1]["avg_delta"], reverse=True):
        label = NOTIFICATION_TYPES.get(nt, {}).get("label", nt)
        sign = "+" if s["avg_delta"] > 0 else ""
        lines.append(
            f"  {label}: {sign}{s['avg_delta']} readiness moy "
            f"({s['positive_pct']}% positif, n={s['count']})"
        )

    best = max(stats.items(), key=lambda x: x[1]["avg_delta"])
    worst = min(stats.items(), key=lambda x: x[1]["avg_delta"])
    best_label = NOTIFICATION_TYPES.get(best[0], {}).get("label", best[0])
    worst_label = NOTIFICATION_TYPES.get(worst[0], {}).get("label", worst[0])

    if best[1]["avg_delta"] > 0:
        lines.append(f"  PLUS EFFICACE: {best_label} — renforce ce type de conseil.")
    if worst[1]["avg_delta"] < -2:
        lines.append(f"  MOINS EFFICACE: {worst_label} — ajuste l'approche.")

    return "\n".join(lines)
