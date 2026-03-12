"""Revna — Garmin Connect integration using garminconnect library.

Direct login with user credentials (like Home Assistant).
"""

import logging
from datetime import date, timedelta
from typing import Any
import uuid

from garminconnect import Garmin, GarminConnectAuthenticationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.health_data import HealthSnapshot
from backend.models.user import User

logger = logging.getLogger(__name__)


class GarminService:
    """Service for interacting with Garmin Connect."""

    def __init__(self, email: str, password: str):
        self.email = email
        self.password = password
        self.client: Garmin | None = None

    def login(self) -> bool:
        """Authenticate with Garmin Connect. Returns True on success."""
        try:
            self.client = Garmin(self.email, self.password)
            self.client.login()
            logger.info("Garmin login successful for %s", self.email)
            return True
        except GarminConnectAuthenticationError as e:
            logger.error("Garmin authentication failed: %s", e)
            return False
        except Exception as e:
            logger.error("Garmin login error: %s", e)
            return False

    def get_daily_stats(self, target_date: date | None = None) -> dict[str, Any] | None:
        """Fetch daily stats for a given date."""
        if not self.client:
            logger.error("Not logged in to Garmin")
            return None

        if target_date is None:
            target_date = date.today()

        try:
            date_str = target_date.isoformat()

            stats = {
                "date": target_date,
                "user_summary": None,
                "sleep": None,
                "stress": None,
                "heart_rate": None,
                "body_battery": None,
                "hrv": None,
            }

            # User daily summary (steps, active minutes, etc.)
            try:
                stats["user_summary"] = self.client.get_stats(date_str)
            except Exception as e:
                logger.warning("Failed to get user summary: %s", e)

            # Sleep data
            try:
                stats["sleep"] = self.client.get_sleep_data(date_str)
            except Exception as e:
                logger.warning("Failed to get sleep data: %s", e)

            # Stress data
            try:
                stats["stress"] = self.client.get_stress_data(date_str)
            except Exception as e:
                logger.warning("Failed to get stress data: %s", e)

            # Heart rate
            try:
                stats["heart_rate"] = self.client.get_heart_rates(date_str)
            except Exception as e:
                logger.warning("Failed to get heart rate: %s", e)

            # Body battery
            try:
                stats["body_battery"] = self.client.get_body_battery(date_str)
            except Exception as e:
                logger.warning("Failed to get body battery: %s", e)

            # HRV
            try:
                stats["hrv"] = self.client.get_hrv_data(date_str)
            except Exception as e:
                logger.warning("Failed to get HRV: %s", e)

            return stats

        except Exception as e:
            logger.error("Error fetching Garmin stats: %s", e)
            return None


def parse_garmin_to_snapshot(user_id: uuid.UUID, garmin_data: dict) -> HealthSnapshot:
    """Convert Garmin data to HealthSnapshot model."""
    target_date = garmin_data.get("date", date.today())

    # Parse user summary
    summary = garmin_data.get("user_summary") or {}
    total_steps = summary.get("totalSteps")
    active_minutes = None
    if summary.get("moderateIntensityMinutes") or summary.get("vigorousIntensityMinutes"):
        moderate = summary.get("moderateIntensityMinutes", 0) or 0
        vigorous = summary.get("vigorousIntensityMinutes", 0) or 0
        active_minutes = moderate + vigorous

    # Parse sleep
    sleep_data = garmin_data.get("sleep") or {}
    daily_sleep = sleep_data.get("dailySleepDTO") or {}
    sleep_score = daily_sleep.get("sleepScores", {}).get("overall", {}).get("value")
    total_sleep_minutes = None
    if daily_sleep.get("sleepTimeSeconds"):
        total_sleep_minutes = daily_sleep.get("sleepTimeSeconds", 0) // 60
    deep_sleep_minutes = None
    if daily_sleep.get("deepSleepSeconds"):
        deep_sleep_minutes = daily_sleep.get("deepSleepSeconds", 0) // 60
    light_sleep_minutes = None
    if daily_sleep.get("lightSleepSeconds"):
        light_sleep_minutes = daily_sleep.get("lightSleepSeconds", 0) // 60
    rem_sleep_minutes = None
    if daily_sleep.get("remSleepSeconds"):
        rem_sleep_minutes = daily_sleep.get("remSleepSeconds", 0) // 60

    # Parse stress
    stress_data = garmin_data.get("stress") or {}
    avg_stress = stress_data.get("avgStressLevel")

    # Parse heart rate
    hr_data = garmin_data.get("heart_rate") or {}
    resting_hr = hr_data.get("restingHeartRate")

    # Parse body battery
    bb_data = garmin_data.get("body_battery") or []
    body_battery = None
    if bb_data and isinstance(bb_data, list) and len(bb_data) > 0:
        # Get the latest body battery value
        latest = bb_data[-1] if bb_data else {}
        body_battery = latest.get("charged") or latest.get("bodyBatteryLevel")

    # Parse HRV
    hrv_data = garmin_data.get("hrv") or {}
    hrv_summary = hrv_data.get("hrvSummary") or {}
    hrv_status = hrv_summary.get("lastNightAvg") or hrv_summary.get("weeklyAvg")

    # SpO2 (if available in summary)
    spo2_avg = summary.get("averageSpo2") or summary.get("latestSpo2")

    return HealthSnapshot(
        user_id=user_id,
        date=target_date,
        sleep_score=sleep_score,
        body_battery=body_battery,
        resting_heart_rate=resting_hr,
        hrv_status=hrv_status,
        avg_stress=avg_stress,
        total_steps=total_steps,
        active_minutes=active_minutes,
        total_sleep_minutes=total_sleep_minutes,
        deep_sleep_minutes=deep_sleep_minutes,
        light_sleep_minutes=light_sleep_minutes,
        rem_sleep_minutes=rem_sleep_minutes,
        spo2_avg=spo2_avg,
        raw_data=garmin_data,
    )


async def sync_garmin_data(
    db: AsyncSession,
    user: User,
    days_back: int = 1,
) -> list[HealthSnapshot]:
    """Sync Garmin data for a user. Returns list of created/updated snapshots."""
    if not user.garmin_email or not user.garmin_password:
        logger.warning("User %s has no Garmin credentials", user.id)
        return []

    # Login to Garmin
    service = GarminService(user.garmin_email, user.garmin_password)
    if not service.login():
        logger.error("Failed to login to Garmin for user %s", user.id)
        return []

    snapshots = []
    today = date.today()

    for i in range(days_back):
        target_date = today - timedelta(days=i)

        # Check if we already have data for this date
        result = await db.execute(
            select(HealthSnapshot).where(
                HealthSnapshot.user_id == user.id,
                HealthSnapshot.date == target_date,
            )
        )
        existing = result.scalar_one_or_none()

        # Fetch data from Garmin
        garmin_data = service.get_daily_stats(target_date)
        if not garmin_data:
            continue

        if existing:
            # Update existing snapshot
            snapshot = parse_garmin_to_snapshot(user.id, garmin_data)
            existing.sleep_score = snapshot.sleep_score
            existing.body_battery = snapshot.body_battery
            existing.resting_heart_rate = snapshot.resting_heart_rate
            existing.hrv_status = snapshot.hrv_status
            existing.avg_stress = snapshot.avg_stress
            existing.total_steps = snapshot.total_steps
            existing.active_minutes = snapshot.active_minutes
            existing.total_sleep_minutes = snapshot.total_sleep_minutes
            existing.deep_sleep_minutes = snapshot.deep_sleep_minutes
            existing.light_sleep_minutes = snapshot.light_sleep_minutes
            existing.rem_sleep_minutes = snapshot.rem_sleep_minutes
            existing.spo2_avg = snapshot.spo2_avg
            existing.raw_data = snapshot.raw_data
            snapshots.append(existing)
        else:
            # Create new snapshot
            snapshot = parse_garmin_to_snapshot(user.id, garmin_data)
            db.add(snapshot)
            snapshots.append(snapshot)

    await db.commit()
    logger.info("Synced %d snapshots for user %s", len(snapshots), user.id)
    return snapshots


async def test_garmin_credentials(email: str, password: str) -> bool:
    """Test if Garmin credentials are valid."""
    service = GarminService(email, password)
    return service.login()
