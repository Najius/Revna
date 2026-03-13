"""Revna — Google Fit integration for Pixel Watch.

Uses Google Fit REST API with OAuth2 to fetch health data.
"""

import datetime
import logging
import uuid
from urllib.parse import urlencode

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import settings
from backend.models.health_data import HealthSnapshot
from backend.models.user import User
from backend.services.wearable import upsert_snapshot

logger = logging.getLogger(__name__)

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_FIT_BASE = "https://www.googleapis.com/fitness/v1/users/me"

# Scopes needed for health data
GOOGLE_FIT_SCOPES = " ".join([
    "https://www.googleapis.com/auth/fitness.sleep.read",
    "https://www.googleapis.com/auth/fitness.heart_rate.read",
    "https://www.googleapis.com/auth/fitness.activity.read",
    "https://www.googleapis.com/auth/fitness.body.read",
    "https://www.googleapis.com/auth/fitness.oxygen_saturation.read",
])


def build_oauth_url(user_id: uuid.UUID) -> str:
    """Build Google OAuth2 authorization URL.

    Uses user_id as the state parameter to link back after callback.
    """
    params = {
        "client_id": settings.google_client_id,
        "redirect_uri": settings.google_redirect_uri,
        "response_type": "code",
        "scope": GOOGLE_FIT_SCOPES,
        "access_type": "offline",
        "prompt": "consent",
        "state": str(user_id),
    }
    return f"{GOOGLE_AUTH_URL}?{urlencode(params)}"


async def exchange_code_for_tokens(code: str) -> dict | None:
    """Exchange authorization code for access + refresh tokens."""
    payload = {
        "code": code,
        "client_id": settings.google_client_id,
        "client_secret": settings.google_client_secret,
        "redirect_uri": settings.google_redirect_uri,
        "grant_type": "authorization_code",
    }
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(GOOGLE_TOKEN_URL, data=payload)
            resp.raise_for_status()
            return resp.json()
    except httpx.HTTPError as e:
        logger.error("Google token exchange failed: %s", e)
        return None


async def refresh_access_token(refresh_token: str) -> str | None:
    """Get a fresh access token using a refresh token."""
    payload = {
        "refresh_token": refresh_token,
        "client_id": settings.google_client_id,
        "client_secret": settings.google_client_secret,
        "grant_type": "refresh_token",
    }
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(GOOGLE_TOKEN_URL, data=payload)
            resp.raise_for_status()
            return resp.json().get("access_token")
    except httpx.HTTPError as e:
        logger.error("Google token refresh failed: %s", e)
        return None


def _millis(dt: datetime.datetime) -> int:
    """Convert datetime to milliseconds since epoch."""
    return int(dt.timestamp() * 1000)


def _time_range(target_date: datetime.date) -> tuple[int, int]:
    """Return (start_millis, end_millis) for a given date."""
    start = datetime.datetime.combine(target_date, datetime.time.min, tzinfo=datetime.timezone.utc)
    end = datetime.datetime.combine(target_date, datetime.time.max, tzinfo=datetime.timezone.utc)
    return _millis(start), _millis(end)


async def _aggregate_request(
    access_token: str,
    data_type: str,
    start_millis: int,
    end_millis: int,
) -> dict | None:
    """Make a Google Fit aggregate request."""
    payload = {
        "aggregateBy": [{"dataTypeName": data_type}],
        "bucketByTime": {"durationMillis": 86400000},  # 1 day
        "startTimeMillis": start_millis,
        "endTimeMillis": end_millis,
    }
    headers = {"Authorization": f"Bearer {access_token}"}
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{GOOGLE_FIT_BASE}/dataset:aggregate",
                json=payload,
                headers=headers,
            )
            resp.raise_for_status()
            return resp.json()
    except httpx.HTTPError as e:
        logger.warning("Google Fit aggregate failed for %s: %s", data_type, e)
        return None


async def _get_sleep_sessions(
    access_token: str,
    start_millis: int,
    end_millis: int,
) -> dict | None:
    """Fetch sleep sessions from Google Fit."""
    headers = {"Authorization": f"Bearer {access_token}"}
    params = {
        "startTime": datetime.datetime.fromtimestamp(
            start_millis / 1000, tz=datetime.timezone.utc
        ).isoformat(),
        "endTime": datetime.datetime.fromtimestamp(
            end_millis / 1000, tz=datetime.timezone.utc
        ).isoformat(),
        "activityType": 72,  # Sleep activity type
    }
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                f"{GOOGLE_FIT_BASE}/sessions",
                params=params,
                headers=headers,
            )
            resp.raise_for_status()
            return resp.json()
    except httpx.HTTPError as e:
        logger.warning("Google Fit sleep sessions failed: %s", e)
        return None


def _extract_int_value(agg_result: dict | None) -> int | None:
    """Extract a single integer value from an aggregate response."""
    if not agg_result:
        return None
    for bucket in agg_result.get("bucket", []):
        for dataset in bucket.get("dataset", []):
            for point in dataset.get("point", []):
                for val in point.get("value", []):
                    if "intVal" in val:
                        return val["intVal"]
                    if "fpVal" in val:
                        return int(val["fpVal"])
    return None


def _extract_float_value(agg_result: dict | None) -> float | None:
    """Extract a single float value from an aggregate response."""
    if not agg_result:
        return None
    for bucket in agg_result.get("bucket", []):
        for dataset in bucket.get("dataset", []):
            for point in dataset.get("point", []):
                for val in point.get("value", []):
                    if "fpVal" in val:
                        return val["fpVal"]
                    if "intVal" in val:
                        return float(val["intVal"])
    return None


async def fetch_daily_data(
    access_token: str, target_date: datetime.date,
) -> dict:
    """Fetch all health data for a given date from Google Fit."""
    start_ms, end_ms = _time_range(target_date)
    fields = {}

    # Steps
    steps_data = await _aggregate_request(
        access_token, "com.google.step_count.delta", start_ms, end_ms,
    )
    steps = _extract_int_value(steps_data)
    if steps is not None:
        fields["total_steps"] = steps

    # Heart rate (resting)
    hr_data = await _aggregate_request(
        access_token, "com.google.heart_rate.bpm", start_ms, end_ms,
    )
    hr = _extract_float_value(hr_data)
    if hr is not None:
        fields["resting_heart_rate"] = int(hr)

    # Active minutes
    active_data = await _aggregate_request(
        access_token, "com.google.active_minutes", start_ms, end_ms,
    )
    active = _extract_int_value(active_data)
    if active is not None:
        fields["active_minutes"] = active

    # Sleep (from sessions)
    sleep_data = await _get_sleep_sessions(access_token, start_ms, end_ms)
    if sleep_data and sleep_data.get("session"):
        total_sleep_ms = 0
        for session in sleep_data["session"]:
            start = int(session.get("startTimeMillis", 0))
            end = int(session.get("endTimeMillis", 0))
            total_sleep_ms += end - start
        if total_sleep_ms > 0:
            fields["total_sleep_minutes"] = total_sleep_ms // 60000

    # SpO2
    spo2_data = await _aggregate_request(
        access_token, "com.google.oxygen_saturation", start_ms, end_ms,
    )
    spo2 = _extract_float_value(spo2_data)
    if spo2 is not None:
        fields["spo2_avg"] = spo2

    return fields


async def sync_google_fit_data(
    db: AsyncSession, user: User, days_back: int = 1,
) -> list[HealthSnapshot]:
    """Sync Google Fit data for a user. Returns list of upserted snapshots."""
    if not user.google_refresh_token:
        logger.warning("User %s has no Google refresh token", user.id)
        return []

    access_token = await refresh_access_token(user.google_refresh_token)
    if not access_token:
        logger.error("Failed to refresh Google token for user %s", user.id)
        return []

    snapshots = []
    today = datetime.date.today()

    for i in range(days_back):
        target_date = today - datetime.timedelta(days=i)
        fields = await fetch_daily_data(access_token, target_date)

        if fields:
            snapshot = await upsert_snapshot(
                db, user.id, target_date, fields,
                raw_data={"google_fit": fields},
            )
            snapshots.append(snapshot)

    logger.info("Google Fit synced %d snapshots for user %s", len(snapshots), user.id)
    return snapshots
