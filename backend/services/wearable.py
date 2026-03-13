"""Revna — Terra API client for wearable health data sync.

New service (no HA equivalent — replaces HA Garmin integration + InfluxDB).
Handles: widget sessions, data fetching, webhook ingestion, snapshot upsert.
"""

import datetime
import hashlib
import hmac
import logging
import time
import uuid

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import settings
from backend.models.health_data import HealthSnapshot
from backend.models.user import User

logger = logging.getLogger(__name__)

TERRA_BASE_URL = "https://api.tryterra.co/v2"


# ─── Terra API client ──────────────────────────────────────────────────────


def _terra_headers() -> dict[str, str]:
    """Build authentication headers for Terra API."""
    return {
        "dev-id": settings.terra_dev_id,
        "x-api-key": settings.terra_api_key,
        "Content-Type": "application/json",
    }


async def generate_widget_session(
    reference_id: str,
    providers: str = "",
    language: str = "fr",
    success_url: str = "",
    failure_url: str = "",
) -> dict | None:
    """Generate a Terra widget session URL for user wearable connection.

    Returns dict with {session_id, url, expires_in} or None on failure.
    """
    if not settings.terra_api_key or not settings.terra_dev_id:
        logger.error("Terra API credentials not configured")
        return None

    payload = {
        "reference_id": reference_id,
        "providers": providers,
        "language": language,
    }
    if success_url:
        payload["auth_success_redirect_url"] = success_url
    if failure_url:
        payload["auth_failure_redirect_url"] = failure_url

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                f"{TERRA_BASE_URL}/auth/generateWidgetSession",
                headers=_terra_headers(),
                json=payload,
            )
            resp.raise_for_status()
            result = resp.json()
            logger.info("Widget session created for ref=%s", reference_id)
            return result
    except httpx.HTTPError as e:
        logger.error("Terra widget session failed: %s", e)
        return None


async def fetch_sleep_data(
    terra_user_id: str,
    start_date: datetime.date,
    end_date: datetime.date | None = None,
) -> dict | None:
    """Fetch sleep data from Terra API."""
    params = {
        "user_id": terra_user_id,
        "start_date": start_date.isoformat(),
    }
    if end_date:
        params["end_date"] = end_date.isoformat()

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                f"{TERRA_BASE_URL}/sleep",
                headers=_terra_headers(),
                params=params,
            )
            resp.raise_for_status()
            return resp.json()
    except httpx.HTTPError as e:
        logger.error("Terra sleep fetch failed: %s", e)
        return None


async def fetch_daily_data(
    terra_user_id: str,
    start_date: datetime.date,
    end_date: datetime.date | None = None,
) -> dict | None:
    """Fetch daily activity summary from Terra API."""
    params = {
        "user_id": terra_user_id,
        "start_date": start_date.isoformat(),
    }
    if end_date:
        params["end_date"] = end_date.isoformat()

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                f"{TERRA_BASE_URL}/daily",
                headers=_terra_headers(),
                params=params,
            )
            resp.raise_for_status()
            return resp.json()
    except httpx.HTTPError as e:
        logger.error("Terra daily fetch failed: %s", e)
        return None


async def fetch_body_data(
    terra_user_id: str,
    start_date: datetime.date,
    end_date: datetime.date | None = None,
) -> dict | None:
    """Fetch body metrics from Terra API."""
    params = {
        "user_id": terra_user_id,
        "start_date": start_date.isoformat(),
    }
    if end_date:
        params["end_date"] = end_date.isoformat()

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                f"{TERRA_BASE_URL}/body",
                headers=_terra_headers(),
                params=params,
            )
            resp.raise_for_status()
            return resp.json()
    except httpx.HTTPError as e:
        logger.error("Terra body fetch failed: %s", e)
        return None


# ─── Webhook signature verification ────────────────────────────────────────


def verify_terra_signature(body: str, signature_header: str) -> bool:
    """Verify Terra webhook signature (HMAC-SHA256).

    Signature header format: "t=1234567890, v1=abc123..."
    """
    if not settings.terra_webhook_secret:
        logger.warning("No Terra webhook secret configured — skipping verification")
        return True

    try:
        parts = {}
        for pair in signature_header.split(", "):
            k, v = pair.split("=", 1)
            parts[k] = v

        timestamp = int(parts.get("t", "0"))

        # Reject if older than 5 minutes (replay protection)
        if abs(time.time() - timestamp) > 300:
            logger.warning("Terra webhook timestamp too old: %d", timestamp)
            return False

        # Compute expected signature
        signed_payload = f"{timestamp}.{body}"
        expected = hmac.new(
            settings.terra_webhook_secret.encode(),
            signed_payload.encode(),
            hashlib.sha256,
        ).hexdigest()

        # Check against all v* signatures
        received = [v for k, v in parts.items() if k.startswith("v")]
        return any(hmac.compare_digest(expected, sig) for sig in received)

    except (ValueError, KeyError) as e:
        logger.error("Terra signature parse error: %s", e)
        return False


# ─── Data extraction from Terra payloads ───────────────────────────────────


def _extract_sleep_fields(sleep_data: dict) -> dict:
    """Extract HealthSnapshot fields from a Terra sleep payload."""
    fields = {}

    # Sleep duration
    durations = sleep_data.get("sleep_durations_data", {})
    asleep = durations.get("asleep", {})
    total_seconds = asleep.get("duration_asleep_state_seconds")
    if total_seconds is not None:
        fields["total_sleep_minutes"] = int(total_seconds / 60)

    # Sleep stages (in seconds → minutes)
    for terra_key, db_field in [
        ("duration_in_deep_seconds", "deep_sleep_minutes"),
        ("duration_in_light_seconds", "light_sleep_minutes"),
        ("duration_in_rem_seconds", "rem_sleep_minutes"),
    ]:
        val = asleep.get(terra_key)
        if val is not None:
            fields[db_field] = int(val / 60)

    # Heart rate data from sleep
    hr_data = sleep_data.get("heart_rate_data", {})
    summary = hr_data.get("summary", {})
    if summary.get("resting_hr_bpm"):
        fields["resting_heart_rate"] = int(summary["resting_hr_bpm"])
    if summary.get("avg_hrv_rmssd"):
        fields["hrv_status"] = float(summary["avg_hrv_rmssd"])

    # Enrichment scores
    enrichment = sleep_data.get("data_enrichment", {})
    if enrichment.get("sleep_score") is not None:
        fields["sleep_score"] = int(enrichment["sleep_score"])

    # SpO2 from sleep
    oxygen = sleep_data.get("oxygen_data", {})
    if oxygen.get("avg_saturation_percentage"):
        fields["spo2_avg"] = float(oxygen["avg_saturation_percentage"])

    return fields


def _extract_daily_fields(daily_data: dict) -> dict:
    """Extract HealthSnapshot fields from a Terra daily payload."""
    fields = {}

    # Steps
    distance = daily_data.get("distance_data", {})
    if distance.get("steps") is not None:
        fields["total_steps"] = int(distance["steps"])

    # Active minutes
    active = daily_data.get("active_durations_data", {})
    active_seconds = active.get("activity_seconds")
    if active_seconds is not None:
        fields["active_minutes"] = int(active_seconds / 60)

    # Heart rate from daily
    hr_data = daily_data.get("heart_rate_data", {})
    summary = hr_data.get("summary", {})
    if summary.get("resting_hr_bpm"):
        fields["resting_heart_rate"] = int(summary["resting_hr_bpm"])
    if summary.get("avg_hrv_rmssd"):
        fields["hrv_status"] = float(summary["avg_hrv_rmssd"])

    # Stress from enrichment
    enrichment = daily_data.get("data_enrichment", {})
    if enrichment.get("stress_score") is not None:
        fields["avg_stress"] = int(enrichment["stress_score"])

    # Readiness → body_battery (Terra's unified readiness metric)
    if enrichment.get("readiness_score") is not None:
        fields["body_battery"] = int(enrichment["readiness_score"])

    return fields


def _extract_date_from_metadata(data: dict) -> datetime.date | None:
    """Extract the date from a Terra data payload's metadata."""
    metadata = data.get("metadata", {})
    start_time = metadata.get("start_time") or metadata.get("end_time")
    if not start_time:
        return None
    try:
        dt = datetime.datetime.fromisoformat(start_time.replace("Z", "+00:00"))
        return dt.date()
    except (ValueError, AttributeError):
        return None


# ─── Snapshot upsert ────────────────────────────────────────────────────────


async def upsert_snapshot(
    db: AsyncSession,
    user_id: uuid.UUID,
    date: datetime.date,
    fields: dict,
    raw_data: dict | None = None,
) -> HealthSnapshot:
    """Insert or update a HealthSnapshot for a given user+date.

    Merges new fields into existing snapshot (doesn't overwrite with None).
    """
    result = await db.execute(
        select(HealthSnapshot).where(
            HealthSnapshot.user_id == user_id,
            HealthSnapshot.date == date,
        )
    )
    snapshot = result.scalar_one_or_none()

    if snapshot:
        # Update only non-None fields
        for key, value in fields.items():
            if value is not None:
                setattr(snapshot, key, value)
        if raw_data:
            existing_raw = snapshot.raw_data or {}
            existing_raw.update(raw_data)
            snapshot.raw_data = existing_raw
    else:
        snapshot = HealthSnapshot(
            user_id=user_id,
            date=date,
            raw_data=raw_data,
            **fields,
        )
        db.add(snapshot)

    await db.commit()
    await db.refresh(snapshot)
    logger.info("Upserted snapshot for user %s on %s", user_id, date)
    return snapshot


# ─── Webhook ingestion ─────────────────────────────────────────────────────


async def process_terra_webhook(db: AsyncSession, payload: dict) -> dict:
    """Process an incoming Terra webhook payload.

    Handles: sleep, daily, body data events + user events.
    Returns result dict.
    """
    event_type = payload.get("type", "unknown")
    user_info = payload.get("user", {})
    terra_user_id = user_info.get("user_id")
    reference_id = user_info.get("reference_id")

    logger.info(
        "Terra webhook: type=%s, terra_user=%s, ref=%s",
        event_type, terra_user_id, reference_id,
    )

    # User events (no data to process)
    if event_type in ("user_reauth", "access_revoked", "auth"):
        logger.info("Terra user event: %s for %s", event_type, terra_user_id)
        return {"status": "ok", "event": event_type}

    # Look up internal user
    user = await _resolve_user(db, terra_user_id, reference_id)
    if not user:
        logger.warning("Terra webhook: no matching user for terra=%s ref=%s",
                       terra_user_id, reference_id)
        return {"status": "error", "reason": "unknown_user"}

    # Store terra_user_id if not set yet
    if terra_user_id and not user.terra_user_id:
        user.terra_user_id = terra_user_id
        await db.commit()

    data_items = payload.get("data", [])
    if not data_items:
        return {"status": "ok", "event": event_type, "items": 0}

    processed = 0
    for item in data_items:
        snapshot_date = _extract_date_from_metadata(item)
        if not snapshot_date:
            logger.warning("Terra webhook: missing date in metadata")
            continue

        fields = {}
        raw_section = {}

        if event_type == "sleep":
            fields = _extract_sleep_fields(item)
            raw_section["sleep"] = item
        elif event_type == "daily":
            fields = _extract_daily_fields(item)
            raw_section["daily"] = item
        elif event_type == "body":
            # Body data → store in raw_data for health.py to pick up
            body = item.get("body_data", item)
            raw_section["body"] = body
            if body.get("weight_kg"):
                raw_section.setdefault("weight_kg", body["weight_kg"])
            if body.get("body_fat_percentage"):
                raw_section.setdefault("body_fat_pct", body["body_fat_percentage"])
        else:
            # Activity, nutrition, etc. — store raw for future use
            raw_section[event_type] = item

        if fields or raw_section:
            await upsert_snapshot(db, user.id, snapshot_date, fields, raw_section)
            processed += 1

    logger.info("Terra webhook processed: %d items for user %s", processed, user.name)
    return {"status": "ok", "event": event_type, "items": processed}


async def _resolve_user(
    db: AsyncSession,
    terra_user_id: str | None,
    reference_id: str | None,
) -> User | None:
    """Find internal user by terra_user_id or reference_id."""
    if terra_user_id:
        result = await db.execute(
            select(User).where(User.terra_user_id == terra_user_id)
        )
        user = result.scalar_one_or_none()
        if user:
            return user

    if reference_id:
        # reference_id is our user UUID (as string)
        try:
            uid = uuid.UUID(reference_id)
            result = await db.execute(
                select(User).where(User.id == uid)
            )
            return result.scalar_one_or_none()
        except ValueError:
            pass

    return None


# ─── Sync all active users ────────────────────────────────────────────────


async def sync_user_data(db: AsyncSession, user: User) -> dict:
    """Fetch and store latest health data for a single user.

    Pulls sleep + daily data for today and yesterday from Terra API.
    """
    if not user.terra_user_id:
        return {"status": "skip", "reason": "no_terra_user_id"}

    today = datetime.date.today()
    yesterday = today - datetime.timedelta(days=1)
    results = {"user": user.name, "snapshots": 0}

    # Fetch sleep data
    sleep_resp = await fetch_sleep_data(user.terra_user_id, yesterday, today)
    if sleep_resp and sleep_resp.get("data"):
        for item in sleep_resp["data"]:
            snap_date = _extract_date_from_metadata(item)
            if snap_date:
                fields = _extract_sleep_fields(item)
                await upsert_snapshot(db, user.id, snap_date, fields, {"sleep": item})
                results["snapshots"] += 1

    # Fetch daily data
    daily_resp = await fetch_daily_data(user.terra_user_id, yesterday, today)
    if daily_resp and daily_resp.get("data"):
        for item in daily_resp["data"]:
            snap_date = _extract_date_from_metadata(item)
            if snap_date:
                fields = _extract_daily_fields(item)
                await upsert_snapshot(db, user.id, snap_date, fields, {"daily": item})
                results["snapshots"] += 1

    logger.info("Synced %d snapshots for user %s", results["snapshots"], user.name)
    return results


async def sync_all_active_users(db: AsyncSession) -> list[dict]:
    """Sync wearable data for all active users with a Terra connection."""
    result = await db.execute(
        select(User).where(
            User.is_active.is_(True),
            User.terra_user_id.isnot(None),
        )
    )
    users = list(result.scalars().all())
    logger.info("Syncing wearable data for %d active users", len(users))

    results = []
    for user in users:
        try:
            r = await sync_user_data(db, user)
            results.append(r)
        except Exception:
            logger.exception("Sync failed for user %s", user.name)
            results.append({"user": user.name, "status": "error"})

    return results
