"""Revna — Background job scheduler (replaces HA automations).

Uses APScheduler to run periodic coaching jobs for all active users:
- Morning adapt + report
- Health monitoring scans
- Evening report / weekly summary
- Check-ins (morning + evening)
- Wearable data sync
- System audit
"""

import datetime
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import select

from backend.database import async_session
from backend.models.user import User
from backend.services.health import (
    get_latest_snapshot,
    compute_readiness_score,
)
from backend.services.notifications import (
    do_ai_notify,
    do_health_monitor,
    build_health_bilan_prompt,
    format_health_bilan,
)
from backend.services.telegram import do_checkin, send_telegram
from backend.services.tracking import (
    record_notification_sent,
    update_advice_outcomes,
)
from backend.services.wearable import sync_all_active_users
from backend.services.garmin import sync_garmin_data
from backend.services.google_fit import sync_google_fit_data
from backend.services.ai import call_claude_api

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


# ─── Helpers ────────────────────────────────────────────────────────────────


async def _get_active_users():
    """Load all active users with a Telegram chat_id."""
    async with async_session() as db:
        result = await db.execute(
            select(User).where(
                User.is_active.is_(True),
                User.telegram_chat_id.isnot(None),
            )
        )
        return list(result.scalars().all())


async def _for_each_user(func, *args, **kwargs):
    """Run an async function for each active user with a fresh DB session."""
    users = await _get_active_users()
    for user in users:
        try:
            async with async_session() as db:
                await func(db, user, *args, **kwargs)
        except Exception:
            logger.exception("Job failed for user %s", user.name)


# ─── Jobs ───────────────────────────────────────────────────────────────────


async def job_morning_adapt():
    """07:30 — AI adapt + morning report for each active user."""
    logger.info("JOB: morning_adapt started")

    async def _run(db, user):
        # Generate health bilan
        system_prompt, user_prompt = await build_health_bilan_prompt(db, user.id, user)
        bilan = call_claude_api(system_prompt, user_prompt)

        if bilan:
            message = format_health_bilan(bilan)
            if user.telegram_chat_id:
                await send_telegram(
                    user.telegram_chat_id, message,
                    db=db, user_id=user.id, msg_type="morning_report",
                )
            await record_notification_sent(db, user.id, "morning_report", message=message)

            # Update yesterday's advice effectiveness
            snapshot = await get_latest_snapshot(db, user.id)
            if snapshot:
                score, _, _ = compute_readiness_score(snapshot)
                sleep = int(snapshot.sleep_score) if snapshot.sleep_score else 0
                await update_advice_outcomes(db, user.id, score, sleep)
        else:
            # Fallback: send morning_report notification
            await do_ai_notify(db, user.id, user, "morning_report")

        logger.info("Morning adapt done for %s", user.name)

    await _for_each_user(_run)


async def job_morning_fallback():
    """09:30 — Fallback if morning_adapt didn't run for some users."""
    logger.info("JOB: morning_fallback started")

    async def _run(db, user):
        from backend.services.tracking import can_send_notification
        if await can_send_notification(db, user.id, "morning_report"):
            logger.info("Morning fallback: sending report for %s", user.name)
            await do_ai_notify(db, user.id, user, "morning_report")

    await _for_each_user(_run)


async def job_health_monitor():
    """11h, 14h, 17h, 20h — Multi-signal health scan."""
    logger.info("JOB: health_monitor started")

    async def _run(db, user):
        await do_health_monitor(db, user.id, user)

    await _for_each_user(_run)


async def job_steps_evening():
    """18:00 — Evening steps summary."""
    logger.info("JOB: steps_evening started")

    async def _run(db, user):
        await do_ai_notify(db, user.id, user, "steps_evening")

    await _for_each_user(_run)


async def job_evening_report():
    """20:00 — Full day report (or weekly summary on Sunday)."""
    logger.info("JOB: evening_report started")

    async def _run(db, user):
        today = datetime.date.today()
        if today.weekday() == 6:  # Sunday
            await do_ai_notify(db, user.id, user, "weekly_summary")
        else:
            await do_ai_notify(db, user.id, user, "evening_report")

    await _for_each_user(_run)


async def job_morning_checkin():
    """07:45 — Morning check-in."""
    logger.info("JOB: morning_checkin started")

    async def _run(db, user):
        await do_checkin(db, user.id, user, "morning")

    await _for_each_user(_run)


async def job_evening_checkin():
    """22:00 — Evening check-in."""
    logger.info("JOB: evening_checkin started")

    async def _run(db, user):
        await do_checkin(db, user.id, user, "evening")

    await _for_each_user(_run)


async def job_monday_activity():
    """Monday 09:00 — Weekly activity motivation."""
    logger.info("JOB: monday_activity started")

    async def _run(db, user):
        await do_ai_notify(db, user.id, user, "monday_activity")

    await _for_each_user(_run)


async def job_sync_wearables():
    """Every 30 min — Sync Terra data for all active users."""
    logger.info("JOB: sync_wearables started")
    async with async_session() as db:
        results = await sync_all_active_users(db)
        total = sum(r.get("snapshots", 0) for r in results)
        logger.info("Wearable sync done: %d snapshots across %d users", total, len(results))


async def job_sync_garmin():
    """Every 2 hours — Sync Garmin data for users with Garmin credentials."""
    logger.info("JOB: sync_garmin started")

    async with async_session() as db:
        # Get users with Garmin credentials
        result = await db.execute(
            select(User).where(
                User.is_active.is_(True),
                User.garmin_email.isnot(None),
                User.garmin_password.isnot(None),
            )
        )
        users = list(result.scalars().all())

        total_snapshots = 0
        for user in users:
            try:
                snapshots = await sync_garmin_data(db, user, days_back=1)
                total_snapshots += len(snapshots)
                logger.info("Garmin sync for %s: %d snapshots", user.name, len(snapshots))
            except Exception:
                logger.exception("Garmin sync failed for user %s", user.name)

        logger.info("Garmin sync done: %d snapshots across %d users", total_snapshots, len(users))


async def job_sync_google_fit():
    """Every 2 hours — Sync Google Fit data for Pixel Watch users."""
    logger.info("JOB: sync_google_fit started")

    async with async_session() as db:
        result = await db.execute(
            select(User).where(
                User.is_active.is_(True),
                User.google_refresh_token.isnot(None),
            )
        )
        users = list(result.scalars().all())

        total_snapshots = 0
        for user in users:
            try:
                snapshots = await sync_google_fit_data(db, user, days_back=1)
                total_snapshots += len(snapshots)
                logger.info("Google Fit sync for %s: %d snapshots", user.name, len(snapshots))
            except Exception:
                logger.exception("Google Fit sync failed for user %s", user.name)

        logger.info("Google Fit sync done: %d snapshots across %d users", total_snapshots, len(users))


async def job_daily_audit():
    """03:00 — System audit (data freshness, API health)."""
    logger.info("JOB: daily_audit started")

    async with async_session() as db:
        # Check Terra users
        result = await db.execute(
            select(User).where(
                User.is_active.is_(True),
                User.terra_user_id.isnot(None),
            )
        )
        terra_users = list(result.scalars().all())

        # Check Garmin users
        result = await db.execute(
            select(User).where(
                User.is_active.is_(True),
                User.garmin_email.isnot(None),
            )
        )
        garmin_users = list(result.scalars().all())

        # Check Google Fit users
        result = await db.execute(
            select(User).where(
                User.is_active.is_(True),
                User.google_refresh_token.isnot(None),
            )
        )
        google_users = list(result.scalars().all())

        # Combine and deduplicate
        all_users = {u.id: u for u in terra_users + garmin_users + google_users}.values()

        stale_users = []
        for user in all_users:
            snapshot = await get_latest_snapshot(db, user.id)
            if not snapshot:
                stale_users.append(f"{user.name}: no data")
            else:
                days_old = (datetime.date.today() - snapshot.date).days
                if days_old > 2:
                    stale_users.append(f"{user.name}: {days_old}d old")

        if stale_users:
            logger.warning("Stale data users: %s", ", ".join(stale_users))
        else:
            logger.info("Daily audit: all users have fresh data")

        logger.info("Audit: %d Terra users, %d Garmin users, %d Google Fit users",
                     len(terra_users), len(garmin_users), len(google_users))


# ─── Scheduler setup ───────────────────────────────────────────────────────


def setup_scheduler() -> AsyncIOScheduler:
    """Configure and return the scheduler with all jobs.

    Call scheduler.start() after FastAPI startup.
    """
    # Morning sequence
    scheduler.add_job(job_morning_adapt, CronTrigger(hour=7, minute=30),
                      id="morning_adapt", replace_existing=True)
    scheduler.add_job(job_morning_checkin, CronTrigger(hour=7, minute=45),
                      id="morning_checkin", replace_existing=True)
    scheduler.add_job(job_morning_fallback, CronTrigger(hour=9, minute=30),
                      id="morning_fallback", replace_existing=True)

    # Health monitoring (4x/day)
    scheduler.add_job(job_health_monitor, CronTrigger(hour="11,14,17,20", minute=0),
                      id="health_monitor", replace_existing=True)

    # Evening sequence
    scheduler.add_job(job_steps_evening, CronTrigger(hour=18, minute=0),
                      id="steps_evening", replace_existing=True)
    scheduler.add_job(job_evening_report, CronTrigger(hour=20, minute=0),
                      id="evening_report", replace_existing=True)
    scheduler.add_job(job_evening_checkin, CronTrigger(hour=22, minute=0),
                      id="evening_checkin", replace_existing=True)

    # Weekly
    scheduler.add_job(job_monday_activity, CronTrigger(day_of_week="mon", hour=9, minute=0),
                      id="monday_activity", replace_existing=True)

    # Wearable sync (every 30 min for Terra)
    scheduler.add_job(job_sync_wearables, CronTrigger(minute="*/30"),
                      id="sync_wearables", replace_existing=True)

    # Garmin sync (every 2 hours — less frequent to avoid rate limits)
    scheduler.add_job(job_sync_garmin, CronTrigger(hour="*/2", minute=15),
                      id="sync_garmin", replace_existing=True)

    # Google Fit sync (every 2 hours for Pixel Watch users)
    scheduler.add_job(job_sync_google_fit, CronTrigger(hour="*/2", minute=30),
                      id="sync_google_fit", replace_existing=True)

    # System audit (nightly)
    scheduler.add_job(job_daily_audit, CronTrigger(hour=3, minute=0),
                      id="daily_audit", replace_existing=True)

    logger.info("Scheduler configured with %d jobs", len(scheduler.get_jobs()))
    return scheduler
