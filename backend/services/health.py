"""Revna — Health computations: readiness scoring, baselines, temporal context.

Adapted from coach/health.py:
- PostgreSQL (health_snapshots table) replaces InfluxDB queries
- user_id added to all operations (multi-tenant)
- All data comes from Terra API snapshots, not HA sensors
"""

import datetime
import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.health_data import HealthSnapshot
from backend.models.coach_history import CoachHistory

logger = logging.getLogger(__name__)


# ─── Health snapshot queries ─────────────────────────────────────────────────

async def get_latest_snapshot(
    db: AsyncSession, user_id: uuid.UUID,
) -> HealthSnapshot | None:
    """Get the most recent health snapshot for a user."""
    result = await db.execute(
        select(HealthSnapshot)
        .where(HealthSnapshot.user_id == user_id)
        .order_by(HealthSnapshot.date.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def get_snapshots(
    db: AsyncSession, user_id: uuid.UUID, days: int = 7,
) -> list[HealthSnapshot]:
    """Get health snapshots for the last N days."""
    cutoff = datetime.date.today() - datetime.timedelta(days=days)
    result = await db.execute(
        select(HealthSnapshot)
        .where(HealthSnapshot.user_id == user_id, HealthSnapshot.date >= cutoff)
        .order_by(HealthSnapshot.date.asc())
    )
    return list(result.scalars().all())


# ─── Readiness score ─────────────────────────────────────────────────────────

def compute_readiness_score(
    snapshot: HealthSnapshot | None,
) -> tuple[int, str, list[str]]:
    """Compute readiness score (0-100) from a health snapshot.

    Returns: (score, level, reasons)
    Level: "normal" (>=85), "light" (>=65), "reduced" (>=40), "rest" (<40)
    """
    if not snapshot:
        return 50, "normal", ["donnees sante indisponibles"]

    components = []
    reasons = []

    # Sleep score (weight 30%)
    if snapshot.sleep_score is not None:
        val = float(snapshot.sleep_score)
        components.append((val, 0.30))
        if val < 50:
            reasons.append(f"sommeil {int(val)}/100")

    # Body battery (weight 25%)
    if snapshot.body_battery is not None:
        val = float(snapshot.body_battery)
        components.append((val, 0.25))
        if val < 30:
            reasons.append(f"batterie {int(val)}%")

    # Stress inverted (weight 20%)
    if snapshot.avg_stress is not None:
        val = float(snapshot.avg_stress)
        components.append((max(0, 100 - val), 0.20))
        if val > 60:
            reasons.append(f"stress eleve ({int(val)})")

    # HRV ratio (weight 15%)
    if snapshot.hrv_status is not None:
        # Normalize HRV to 0-100 scale (typical range 20-80ms)
        hrv_score = max(0, min(100, (snapshot.hrv_status - 20) * (100 / 60)))
        components.append((hrv_score, 0.15))
        if snapshot.hrv_status < 30:
            reasons.append(f"VFC basse ({snapshot.hrv_status:.0f}ms)")

    # Sleep duration (weight 10%)
    if snapshot.total_sleep_minutes is not None:
        dur_hours = snapshot.total_sleep_minutes / 60
        if dur_hours < 5:
            dur_score = 20
        elif dur_hours < 6:
            dur_score = 50
        elif dur_hours < 7:
            dur_score = 70
        elif dur_hours < 8:
            dur_score = 90
        else:
            dur_score = 100
        components.append((dur_score, 0.10))
        if dur_hours < 6:
            h = int(dur_hours)
            m = int((dur_hours - h) * 60)
            reasons.append(f"sommeil court ({h}h{m:02d})")

    if not components:
        return 50, "normal", ["donnees sante indisponibles"]

    total_weight = sum(w for _, w in components)
    score = int(round(sum(v * w for v, w in components) / total_weight))
    score = max(0, min(100, score))

    if score >= 85:
        level = "normal"
    elif score >= 65:
        level = "light"
    elif score >= 40:
        level = "reduced"
    else:
        level = "rest"

    return score, level, reasons


# ─── Individual baselines ────────────────────────────────────────────────────

async def compute_individual_baselines(
    db: AsyncSession, user_id: uuid.UUID,
) -> dict | None:
    """Compute personal baselines from 14+ days of health snapshots.

    Returns dict with baselines per metric, or None if insufficient data.
    """
    snapshots = await get_snapshots(db, user_id, days=30)
    if len(snapshots) < 14:
        return None

    baselines = {}

    sleeps = [float(s.sleep_score) for s in snapshots if s.sleep_score is not None]
    if len(sleeps) >= 7:
        avg = sum(sleeps) / len(sleeps)
        sd = (sum((s - avg) ** 2 for s in sleeps) / len(sleeps)) ** 0.5
        baselines["sleep"] = {"mean": round(avg, 1), "sd": round(sd, 1),
                              "low": round(avg - sd, 1)}

    bbs = [float(s.body_battery) for s in snapshots if s.body_battery is not None]
    if len(bbs) >= 7:
        avg = sum(bbs) / len(bbs)
        baselines["body_battery"] = {"mean": round(avg, 1)}

    stresses = [float(s.avg_stress) for s in snapshots if s.avg_stress is not None]
    if len(stresses) >= 7:
        avg = sum(stresses) / len(stresses)
        baselines["stress"] = {"mean": round(avg, 1)}

    return baselines if baselines else None


async def build_baselines_context(db: AsyncSession, user_id: uuid.UUID) -> str:
    """Build context string with personal baselines for AI prompts."""
    baselines = await compute_individual_baselines(db, user_id)
    if not baselines:
        return ""

    lines = ["BASELINES PERSONNELLES (moyennes 30 jours du patient):"]
    if "sleep" in baselines:
        b = baselines["sleep"]
        lines.append(f"  Sommeil: moyenne {b['mean']}/100 (ecart-type {b['sd']}). "
                     f"En dessous de {b['low']} = inhabituel pour CE patient.")
    if "stress" in baselines:
        lines.append(f"  Stress moyen habituel: {baselines['stress']['mean']}/100")
    if "body_battery" in baselines:
        lines.append(f"  Body Battery moyenne: {baselines['body_battery']['mean']}%")
    lines.append("Utilise ces baselines pour qualifier 'bon/mauvais' RELATIVEMENT au patient.")
    return "\n".join(lines)


# ─── Temporal context ────────────────────────────────────────────────────────

async def build_temporal_context(
    db: AsyncSession, user_id: uuid.UUID,
    today_snapshot: HealthSnapshot | None = None,
) -> str:
    """Build multi-level temporal context string for AI prompts.

    Level 1: Yesterday vs today comparison
    Level 2: 7-day trends from coach history
    """
    lines = []
    today = datetime.date.today()
    yesterday = today - datetime.timedelta(days=1)

    # Yesterday's snapshot for comparison
    result = await db.execute(
        select(HealthSnapshot)
        .where(HealthSnapshot.user_id == user_id, HealthSnapshot.date == yesterday)
    )
    yesterday_snap = result.scalar_one_or_none()

    if yesterday_snap and today_snapshot:
        comp_lines = []
        comparisons = [
            ("sleep_score", "Sommeil", "/100"),
            ("body_battery", "Body Battery", "%"),
            ("avg_stress", "Stress", "/100"),
            ("total_steps", "Pas", ""),
        ]
        for attr, label, unit in comparisons:
            y_val = getattr(yesterday_snap, attr)
            t_val = getattr(today_snapshot, attr)
            if y_val is not None and t_val is not None:
                diff = int(t_val) - int(y_val)
                arrow = f"\u2191{diff}" if diff > 0 else (f"\u2193{abs(diff)}" if diff < 0 else "=")
                comp_lines.append(f"  {label}: {int(y_val)}{unit} -> {int(t_val)}{unit} ({arrow})")
        if comp_lines:
            lines.append("HIER vs AUJOURD'HUI:")
            lines.extend(comp_lines)

    # 7-day trends from coach history
    cutoff = today - datetime.timedelta(days=7)
    result = await db.execute(
        select(CoachHistory)
        .where(CoachHistory.user_id == user_id, CoachHistory.date >= cutoff)
        .order_by(CoachHistory.date.asc())
    )
    history = list(result.scalars().all())

    if len(history) >= 2:
        trend_lines = []
        scores = [h.readiness_score for h in history if h.readiness_score is not None]
        if scores:
            trend_lines.append(f"  Readiness: {' -> '.join(str(s) for s in scores)}")
        if trend_lines:
            lines.append("\nTENDANCES 7 JOURS:")
            lines.extend(trend_lines)

    return "\n".join(lines) if lines else ""


# ─── Health data formatting ─────────────────────────────────────────────────

def format_snapshot_for_prompt(snapshot: HealthSnapshot | None) -> str:
    """Format a health snapshot into a readable string for AI prompts."""
    if not snapshot:
        return "Aucune donnee disponible."

    lines = []

    if snapshot.sleep_score is not None:
        lines.append(f"- Sommeil: score {snapshot.sleep_score}/100")
    if snapshot.total_sleep_minutes is not None:
        h, m = divmod(snapshot.total_sleep_minutes, 60)
        lines.append(f"  Duree: {h}h{m:02d}")
    if snapshot.deep_sleep_minutes is not None:
        lines.append(
            f"  Stades: deep {snapshot.deep_sleep_minutes}min, "
            f"light {snapshot.light_sleep_minutes or 0}min, "
            f"REM {snapshot.rem_sleep_minutes or 0}min"
        )
    if snapshot.body_battery is not None:
        lines.append(f"- Body Battery: {snapshot.body_battery}%")
    if snapshot.hrv_status is not None:
        lines.append(f"- VFC: {snapshot.hrv_status:.0f}ms")
    if snapshot.resting_heart_rate is not None:
        lines.append(f"- FC repos: {snapshot.resting_heart_rate} bpm")
    if snapshot.spo2_avg is not None:
        lines.append(f"- SpO2: moy {snapshot.spo2_avg:.0f}%")
    if snapshot.avg_stress is not None:
        lines.append(f"- Stress moyen: {snapshot.avg_stress}/100")
    if snapshot.total_steps is not None:
        lines.append(f"- Pas: {snapshot.total_steps}")
    if snapshot.active_minutes is not None:
        lines.append(f"- Minutes actives: {snapshot.active_minutes}min")

    # Raw data may contain additional details from Terra
    raw = snapshot.raw_data or {}
    if raw.get("weight_kg"):
        lines.append(f"- Poids: {raw['weight_kg']}kg")
    if raw.get("body_fat_pct"):
        lines.append(f"- Masse grasse: {raw['body_fat_pct']}%")

    return "\n".join(lines) if lines else "Donnees limitees."


# ─── Data freshness ──────────────────────────────────────────────────────────

def compute_data_freshness(snapshot: HealthSnapshot | None) -> str:
    """Assess staleness of health data for AI prompt injection."""
    if not snapshot:
        return "ATTENTION DONNEES: Aucune donnee disponible. Adapte sans chiffres.\n"

    today = datetime.date.today()
    days_old = (today - snapshot.date).days

    if days_old == 0:
        return ""
    elif days_old == 1:
        return "QUALITE DES DONNEES: Donnees d'hier (pas encore de donnees pour aujourd'hui).\n"
    elif days_old <= 3:
        return f"QUALITE DES DONNEES: Dernieres donnees datent de {days_old} jours. Fiabilite moderee.\n"
    else:
        return f"ATTENTION DONNEES: Dernieres donnees datent de {days_old} jours. Fiabilite basse.\n"
