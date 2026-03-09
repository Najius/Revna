"""Revna — Notification prompt builders, dispatch, and health monitoring.

Adapted from coach/notifications.py:
- PostgreSQL replaces HA sensors & InfluxDB
- user_id added (multi-tenant)
- Async operations
- Generalized prompts (no rehab-specific context)
- Telegram sending delegated to services/telegram.py (Phase 3)
"""

import datetime
import logging
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.constants import (
    NOTIFICATION_TYPES,
    ESSENTIAL_NOTIFICATIONS,
    MEDICAL_DISCLAIMER,
    SILENT_DAY_READINESS_THRESHOLD,
)
from backend.core.prompts import (
    PSY_TECHNIQUES,
    WELLNESS_SUGGESTIONS,
    HEALTH_DATA_INTERPRETATION,
    SAFETY_DECISION_TREE,
    PROMPT_RULES,
)
from backend.services.ai import call_claude_notification
from backend.services.health import (
    get_latest_snapshot,
    compute_readiness_score,
    format_snapshot_for_prompt,
    compute_data_freshness,
    build_baselines_context,
    build_temporal_context,
)
from backend.services.tracking import (
    can_send_notification,
    record_notification_sent,
    get_coach_history,
    build_feelings_context,
    build_streak_context,
    build_effectiveness_context,
    record_advice_given,
)
from backend.services.telegram import send_telegram
from backend.models.user import User

logger = logging.getLogger(__name__)


# ─── Time context ────────────────────────────────────────────────────────────


def _get_time_context() -> tuple[str, str]:
    """Return time-of-day context for AI prompts."""
    hour = datetime.datetime.now().hour
    if hour < 10:
        return "matin", (
            "Le patient vient de se lever ou est en debut de matinee. "
            "La Body Battery devrait etre au plus haut de la journee. "
            "Le stress devrait etre au plus bas. "
            "Des valeurs basses a cette heure sont plus inquietantes qu'en fin de journee."
        )
    elif hour < 14:
        return "milieu de journee", (
            "La matinee est bien avancee. "
            "La Body Battery a normalement baisse de 10-20% depuis le reveil. "
            "Le stress augmente avec l'activite professionnelle/quotidienne. "
            "Les pas devraient etre a 30-40% de l'objectif."
        )
    elif hour < 18:
        return "apres-midi", (
            "L'apres-midi est entame. "
            "La Body Battery continue de baisser (perte de 3-5%/heure en activite). "
            "Le stress peut etre eleve sans que ce soit anormal apres une journee active. "
            "Les pas devraient etre a 50-70% de l'objectif."
        )
    else:
        return "soir", (
            "C'est la fin de journee. "
            "La Body Battery est normalement au plus bas — c'est attendu. "
            "Le stress cumule de la journee peut etre eleve sans etre inquietant. "
            "Les metriques refletent la journee entiere, pas un instant isole."
        )


# ─── Prompt builders ─────────────────────────────────────────────────────────


async def build_notification_prompt(
    db: AsyncSession,
    user_id: uuid.UUID,
    user: User,
    notif_type: str,
) -> tuple[str | None, str | None]:
    """Build system + user prompts for contextual AI notification.

    Returns (system_prompt, user_prompt) or (None, None) for unknown types.
    """
    hour = datetime.datetime.now().hour
    time_period, time_context = _get_time_context()

    # Gather health data
    snapshot = await get_latest_snapshot(db, user_id)
    health_str = format_snapshot_for_prompt(snapshot)
    freshness = compute_data_freshness(snapshot)

    # Gather contextual data
    temporal_ctx = await build_temporal_context(db, user_id, snapshot)
    feelings_ctx = await build_feelings_context(db, user_id)
    history = await get_coach_history(db, user_id)
    streak_ctx = build_streak_context(history)
    baselines_ctx = await build_baselines_context(db, user_id)
    effectiveness_ctx = await build_effectiveness_context(db, user_id)

    system_prompt = f"""Tu es un coach sante holistique bienveillant, specialise dans l'accompagnement
de personnes actives qui suivent leur sante via un wearable.

{PSY_TECHNIQUES}

{WELLNESS_SUGGESTIONS}

{HEALTH_DATA_INTERPRETATION}

PATIENT: {user.name}
HEURE: {hour}h ({time_period})
CONTEXTE TEMPOREL: {time_context}

{PROMPT_RULES}

{SAFETY_DECISION_TREE}

REGLES NOTIFICATIONS SUPPLEMENTAIRES:
- Concis (3-8 lignes max), concret et personnalise
- Commence par emoji + titre <b>
- 1-2 conseils actionnables specifiques a l'heure
- Ne PAS repeter les donnees brutes, les interpreter
- VALIDER le ressenti avant de conseiller
- Utilise les COMPARAISONS TEMPORELLES (hier vs aujourd'hui, tendance 7j)
- Propose UNE micro-intervention psy OU UNE suggestion bien-etre adaptee au contexte
- Si alerte: contextualiser sans alarmer
- Si felicitation: celebrer chaleureusement
- Reponds UNIQUEMENT le message Telegram, rien d'autre"""

    # Build context block from all available data
    ctx_block = ""
    if freshness:
        ctx_block += f"\n{freshness}\n"
    if temporal_ctx:
        ctx_block += f"\n{temporal_ctx}\n"
    if feelings_ctx:
        ctx_block += f"\n{feelings_ctx}\n"
    if streak_ctx:
        ctx_block += f"\n{streak_ctx}\n"
    if baselines_ctx:
        ctx_block += f"\n{baselines_ctx}\n"
    if effectiveness_ctx:
        ctx_block += f"\n{effectiveness_ctx}\n"

    # ─── Per-type user prompts ────────────────────────────────────────────────

    type_prompts: dict[str, str] = {}

    type_prompts["morning_report"] = f"""NOTIFICATION: Rapport matinal (08h00)
OBJECTIF: Resumer la nuit, evaluer la recuperation, donner le ton de la journee.
{ctx_block}
DONNEES SANTE:
{health_str}

Genere un message Telegram HTML concis (5-8 lignes) qui:
1. Compare la nuit avec les precedentes (tendance sommeil) — utilise fragmentation et stades si disponibles
2. Compare la BB au reveil vs hier matin, mentionne la recharge nocturne
3. Indique clairement le type de journee: active, moderee, ou calme — base sur les signaux croises
4. Propose UNE technique mindfulness matinale adaptee
5. Suggere un aliment/boisson pour bien demarrer
6. Si ressenti du patient disponible, l'integrer"""

    type_prompts["poor_sleep"] = f"""NOTIFICATION: Alerte sommeil insuffisant
{ctx_block}
DONNEES SANTE:
{health_str}

Le score de sommeil est bas (< 50). Contextualise:
- Compare avec les nuits precedentes (tendance)
- Si la Body Battery est correcte (>50) malgre un mauvais score sommeil, le corps a quand meme recupere — rassure
- Si les deux sont bas, c'est plus serieux

Message (4-6 lignes):
1. Qualifie la gravite EN CONTEXTE avec comparaison temporelle
2. Valide le ressenti si le patient a communique de la fatigue
3. Conseil concret pour la journee (pas pour ce soir)
4. Propose une technique: respiration ou auto-compassion si pattern de mauvais sommeil"""

    type_prompts["sedentary"] = f"""NOTIFICATION: Rappel anti-sedentarite (> 2h assis)
{ctx_block}
DONNEES SANTE:
{health_str}

Il est {hour}h. Message (3-5 lignes):
1. Rappel amical (pas culpabilisant)
2. UNE suggestion concrete adaptee a l'heure et a la BB actuelle
3. Rappel hydratation si pertinent
4. Compare les pas actuels avec hier a la meme heure si disponible"""

    type_prompts["steps_evening"] = f"""NOTIFICATION: Bilan des pas a 18h
{ctx_block}
DONNEES SANTE:
{health_str}

Genere un message (4-6 lignes) qui:
1. Donne le nombre de pas exact et le % de l'objectif
2. Compare avec hier
3. Integre etages montes, calories actives et temps sedentaire si disponibles
4. Si < 50%: encourage une marche du soir
5. Si 50-99%: motive pour finir
6. Si >= 100%: celebre + mentionne la tendance 7j"""

    type_prompts["high_stress"] = f"""NOTIFICATION: Alerte stress eleve (> 70/100)
{ctx_block}
DONNEES SANTE:
{health_str}

Il est {hour}h. Message (4-6 lignes):
1. Contextualise: est-ce anormal pour l'heure? Compare avec la tendance
2. Regarde le % de stress eleve et la Body Battery pour croiser
3. Valide le ressenti du patient si disponible
4. Propose UNE technique precise: respiration ancrage 2min OU technique 5-4-3-2-1
5. Suggestion bien-etre: tisane camomille, marche en nature, bain chaud selon l'heure"""

    type_prompts["low_body_battery"] = f"""NOTIFICATION: Body Battery critique (< 20%)
{ctx_block}
DONNEES SANTE:
{health_str}

Il est {hour}h. Message (4-6 lignes):
1. Qualifie la gravite SELON L'HEURE avec comparaison vs hier
2. Identifie la cause probable en croisant sommeil, stress, activite
3. Utilise l'acceptation: "ton corps a travaille, c'est normal qu'il demande du repos"
4. Conseil adapte: sieste si matin, pause si aprem, rien d'alarmant si soir
5. Suggestion nutrition/hydratation adaptee"""

    type_prompts["weekly_summary"] = f"""NOTIFICATION: Bilan hebdomadaire (dimanche 20h)
{ctx_block}
DONNEES SANTE (fin de semaine):
{health_str}

Genere un bilan structure (12-18 lignes):
1. <b>ACTIVITE</b>: minutes d'intensite vs objectif, activites de la semaine, comparaison semaine precedente
2. <b>SOMMEIL</b>: tendance 7 nuits (score moyen, fragmentation, deep sleep moyen), nuits meilleures/pires
3. <b>RECUPERATION</b>: tendance VFC 7 nuits (hausse/baisse/stable), BB moyenne, FC repos evolution
4. <b>STRESS</b>: patterns recurrents de la semaine (pics, periodes calmes)
5. <b>COMPOSITION</b>: evolution poids/masse grasse si variation notable
6. <b>BIEN-ETRE</b>: resume les ressentis de la semaine si disponibles
7. <b>SEMAINE PROCHAINE</b>: 2-3 objectifs concrets bases sur les tendances
8. Technique psy adaptee au bilan global
9. Note globale avec emoji couleur et comparaison avec la semaine precedente"""

    type_prompts["low_spo2"] = f"""NOTIFICATION: SpO2 basse detectee (< 85%)
{ctx_block}
DONNEES SANTE:
{health_str}

Message SOBRE (3-4 lignes):
1. Signale le fait objectivement sans dramatiser
2. Recommande de surveiller les prochaines nuits
3. Si ca se repete, consulter un medecin
4. NE PAS diagnostiquer"""

    type_prompts["steps_goal_reached"] = f"""NOTIFICATION: Objectif de pas atteint!
{ctx_block}
DONNEES SANTE:
{health_str}

Il est {hour}h. Message de FELICITATION (3-5 lignes):
1. Celebre l'accomplissement avec enthousiasme
2. Si atteint avant 15h: souligne que c'est tot, impressionnant
3. Si atteint tard: la persistence paie
4. Compare avec la tendance 7j des pas
5. Suggestion post-effort: hydratation, collation proteinee, etirements"""

    type_prompts["monday_activity"] = f"""NOTIFICATION: Rappel d'activite du lundi
{ctx_block}
DONNEES SANTE:
{health_str}

C'est lundi. Message motivant (4-6 lignes):
1. Lance la semaine sur une note positive
2. Rappelle l'objectif d'intensite hebdomadaire
3. Propose UNE activite concrete adaptee a l'etat du jour
4. Proposition nutrition"""

    type_prompts["evening_report"] = f"""NOTIFICATION: Bilan complet de la journee (20h)
{ctx_block}
DONNEES SANTE COMPLETES:
{health_str}

Genere un bilan de journee structure et complet (12-18 lignes):
1. Ouvre avec une evaluation globale en 1 phrase en <i>italique</i>
2. <b>SOMMEIL</b>: score et duree, mentionne fragmentation et stades si disponibles, comparaison 3 dernieres nuits
3. <b>ENERGIE</b>: timeline BB avec drains significatifs, recharge nocturne, comparaison hier
4. <b>STRESS</b>: stress moyen, patterns par periode (matin/aprem/soir), pics > 50
5. <b>ACTIVITE</b>: pas vs objectif, comparaison hier, calories, derniere activite sportive
6. <b>CARDIO</b>: FC repos, tendance VFC 7 nuits (hausse/baisse/stable), SpO2
7. <b>BIEN-ETRE</b>: integre le ressenti du patient si disponible
8. <b>DEMAIN</b>: 1-2 conseils pour optimiser la nuit

Format: emojis + gras HTML, compact et lisible."""

    type_prompts["chronic_fatigue"] = f"""NOTIFICATION: Alerte fatigue chronique
{ctx_block}
DONNEES SANTE:
{health_str}

Message EMPATHIQUE (6-10 lignes) qui:
1. Nomme le pattern avec bienveillance: "Je remarque que ca fait plusieurs nuits difficiles d'affilee..."
2. Valide l'emotion: "C'est tout a fait normal de sentir la fatigue s'accumuler"
3. Explique POURQUOI c'est important:
   - Sommeil profond = reparation musculaire
   - VFC basse = systeme nerveux fatigue
   - Fragmentation = pas de cycles complets
4. Propose un PLAN CONCRET pour casser le cycle (3 actions):
   - Ce soir: routine pre-sommeil (douche tiede, pas d'ecran, 4-7-8)
   - Demain: reduire l'activite, sieste 20min avant 15h
   - Cette semaine: horaires reguliers (+/- 30min)
5. Rassure: "C'est un cycle, pas un etat permanent — on va le casser ensemble"
6. Propose une technique psy: auto-compassion ou defusion cognitive"""

    type_prompts["recovery_protocol"] = f"""NOTIFICATION: Protocole de recuperation post-activite
{ctx_block}
DONNEES SANTE:
{health_str}

Message POSITIF (5-8 lignes) qui:
1. Felicite pour l'activite realisee avec enthousiasme
2. Rappelle que la recuperation fait PARTIE de l'entrainement, pas une pause
3. Adapte les conseils selon l'etat actuel:
   - Hydratation, proteines, etirements doux
   - Marche legere ok, pas d'effort intense, sommeil prioritaire
4. Croise avec l'etat de sante actuel (BB, stress, sommeil)"""

    type_prompts["readiness_prediction"] = f"""NOTIFICATION: Prediction pour demain
{ctx_block}
DONNEES SANTE:
{health_str}

Message PROSPECTIF (5-8 lignes) qui:
1. Resume la journee en 1 ligne
2. Anticipe la forme de demain en se basant sur les tendances
3. Propose 2-3 actions CE SOIR pour optimiser la nuit:
   - Si tendance basse: routine sommeil stricte, pas d'ecran, 4-7-8, temperature chambre 18-19C
   - Si tendance haute: maintenir le rythme, celebrer la bonne forme
4. Termine par une note positive adaptee au contexte"""

    user_prompt = type_prompts.get(notif_type)
    if not user_prompt:
        return None, None

    return system_prompt, user_prompt


async def build_health_bilan_prompt(
    db: AsyncSession,
    user_id: uuid.UUID,
    user: User,
) -> tuple[str, str]:
    """Build Claude prompt for personalized daily health analysis (JSON output)."""
    snapshot = await get_latest_snapshot(db, user_id)
    health_str = format_snapshot_for_prompt(snapshot)
    freshness = compute_data_freshness(snapshot)
    time_period, time_context = _get_time_context()
    hour = datetime.datetime.now().hour

    readiness_score, readiness_level, _ = compute_readiness_score(snapshot)

    temporal_ctx = await build_temporal_context(db, user_id, snapshot)
    feelings_ctx = await build_feelings_context(db, user_id)
    baselines_ctx = await build_baselines_context(db, user_id)

    system_prompt = f"""Tu es un coach sante holistique avec une double expertise:
1) Analyse de donnees de sante (wearables)
2) Communication bienveillante et personnalisee

{PSY_TECHNIQUES}

{WELLNESS_SUGGESTIONS}

{HEALTH_DATA_INTERPRETATION}

Tu analyses les donnees de sante de {user.name}.

HEURE ACTUELLE: {hour}h ({time_period})
CONTEXTE TEMPOREL: {time_context}

PRINCIPES D'ANALYSE:
- Contextualise TOUT par rapport a l'heure actuelle
- Le matin (avant 10h): les pas et l'activite sont naturellement bas — NE PAS critiquer. Commente les donnees de la NUIT
- L'apres-midi/soir: les pas et l'activite refletent la journee — peut etre commente
- REGLE STRICTE score "activity" avant 10h: IGNORER completement les pas du jour. Baser le score sur les minutes d'intensite de la veille et la tendance 7j. Score minimum 50/100 le matin
- Commence "summary" par un mot bienveillant
- "focus" doit valider l'etat emotionnel avant de donner le conseil
- Utilise les comparaisons temporelles
- Integre les ressentis du patient si disponibles

{SAFETY_DECISION_TREE}

{PROMPT_RULES}

Reponds UNIQUEMENT en JSON valide (pas de markdown, pas de texte autour)."""

    extra_ctx = ""
    if freshness:
        extra_ctx += f"\n{freshness}\n"
    if temporal_ctx:
        extra_ctx += f"\n{temporal_ctx}\n"
    if feelings_ctx:
        extra_ctx += f"\n{feelings_ctx}\n"
    if baselines_ctx:
        extra_ctx += f"\n{baselines_ctx}\n"

    user_prompt = f"""{extra_ctx}DONNÉES DE SANTÉ DU JOUR:
{health_str}

READINESS: niveau={readiness_level}, score={readiness_score}/100

Analyse ces données et retourne:
{{
  "summary": "Résumé en 1 phrase de l'état général",
  "scores": {{
    "sleep": {{"value": int, "max": 100, "emoji": "🟢/🟡/🔴", "comment": "court commentaire"}},
    "recovery": {{"value": int, "max": 100, "emoji": "🟢/🟡/🔴", "comment": "court commentaire"}},
    "stress": {{"value": int, "max": 100, "emoji": "🟢/🟡/🔴", "comment": "court commentaire"}},
    "cardio": {{"value": int, "max": 100, "emoji": "🟢/🟡/🔴", "comment": "court commentaire"}},
    "activity": {{"value": int, "max": 100, "emoji": "🟢/🟡/🔴", "comment": "court commentaire"}}
  }},
  "do_today": ["3-5 recommandations concrètes pour aujourd'hui"],
  "avoid_today": ["2-3 choses à ÉVITER aujourd'hui"],
  "focus": "Le conseil le plus important du jour en 1 phrase"
}}

Sois concret et personnalisé."""

    return system_prompt, user_prompt


# ─── Formatters ──────────────────────────────────────────────────────────────


def format_health_bilan(bilan: dict) -> str:
    """Format Claude health bilan JSON as a Telegram message."""
    lines = ["\U0001f3e5 <b>Bilan santé du jour</b>", ""]
    lines.append(f"<i>{bilan.get('summary', '')}</i>")
    lines.append("")

    # Before 10h, override activity score (steps naturally ~0 in the morning)
    hour = datetime.datetime.now().hour
    scores = bilan.get("scores", {})
    if hour < 10 and "activity" in scores:
        act = scores["activity"]
        if isinstance(act.get("value"), (int, float)) and act["value"] < 50:
            act["value"] = 50
            act["emoji"] = "\U0001f7e2"
            if act.get("comment"):
                act["comment"] = act["comment"].replace("Seulement", "").strip()
                act["comment"] += " (normal le matin, score base sur tendance)"

    for key, label in [
        ("sleep", "Sommeil"),
        ("recovery", "Récupération"),
        ("stress", "Stress"),
        ("cardio", "Cardio"),
        ("activity", "Activité"),
    ]:
        s = scores.get(key, {})
        emoji = s.get("emoji", "\u26aa")
        val = s.get("value", "?")
        comment = s.get("comment", "")
        lines.append(f"{emoji} <b>{label}</b> : {val}/100 \u00b7 {comment}")

    do_list = bilan.get("do_today", [])
    if do_list:
        lines.append("")
        lines.append("\u2705 <b>À faire aujourd'hui</b>")
        for item in do_list:
            lines.append(f"  \u2192 {item}")

    avoid_list = bilan.get("avoid_today", [])
    if avoid_list:
        lines.append("")
        lines.append("\U0001f6ab <b>À éviter</b>")
        for item in avoid_list:
            lines.append(f"  \u2192 {item}")

    focus = bilan.get("focus", "")
    if focus:
        lines.append("")
        lines.append(f"\U0001f4a1 <b>{focus}</b>")

    return "\n".join(lines)


# ─── Silent day check ────────────────────────────────────────────────────────


async def _is_silent_day(db: AsyncSession, user_id: uuid.UUID) -> bool:
    """Check if today is a 'silent day' (high readiness suppresses non-essential).

    Reduces notification fatigue when the user is doing well.
    """
    snapshot = await get_latest_snapshot(db, user_id)
    score, _, _ = compute_readiness_score(snapshot)
    if score >= SILENT_DAY_READINESS_THRESHOLD:
        logger.debug("Silent day: readiness %d >= %d", score, SILENT_DAY_READINESS_THRESHOLD)
        return True
    return False


# ─── Dispatch ─────────────────────────────────────────────────────────────────


async def do_ai_notify(
    db: AsyncSession,
    user_id: uuid.UUID,
    user: User,
    notif_type: str,
) -> dict:
    """Send an AI contextual notification. Returns result dict.

    Handles: cooldown check, silent day suppression, prompt building,
    AI call, and effectiveness tracking.
    Telegram sending is delegated to services/telegram.py (Phase 3).
    """
    config = NOTIFICATION_TYPES.get(notif_type)
    if not config:
        logger.warning("Unknown notification type: %s", notif_type)
        return {"status": "error", "reason": f"Unknown type: {notif_type}"}

    logger.info("Notification %s for user %s (%s)", notif_type, user.name, config["label"])

    # Silent day: suppress non-essential
    if notif_type not in ESSENTIAL_NOTIFICATIONS:
        if await _is_silent_day(db, user_id):
            return {"status": "silent_day", "type": notif_type}

    # Cooldown check
    if not await can_send_notification(db, user_id, notif_type):
        return {"status": "cooldown", "type": notif_type}

    # Build prompts
    system_prompt, user_prompt = await build_notification_prompt(
        db, user_id, user, notif_type,
    )
    if not system_prompt:
        return {"status": "error", "reason": f"No prompt for type: {notif_type}"}

    # Call Claude
    message = call_claude_notification(
        system_prompt,
        user_prompt,
        max_tokens=config["max_tokens"],
        temperature=config["temperature"],
    )

    if message:
        message += MEDICAL_DISCLAIMER
        if user.telegram_chat_id:
            await send_telegram(
                user.telegram_chat_id, message,
                db=db, user_id=user_id, msg_type=notif_type,
            )
        logger.info("Generated %s for user %s", notif_type, user.name)
        await record_notification_sent(db, user_id, notif_type, message=message)

        # Track advice effectiveness (before metrics for J+1 comparison)
        snapshot = await get_latest_snapshot(db, user_id)
        readiness, _, _ = compute_readiness_score(snapshot)
        sleep = int(snapshot.sleep_score) if snapshot and snapshot.sleep_score else None
        await record_advice_given(
            db, user_id, notif_type, readiness=readiness, sleep=sleep,
        )

        return {"status": "ok", "type": notif_type, "message": message, "ai": True}
    else:
        fallback = f"<b>{config['label']}</b>\n\nAnalyse IA indisponible."
        logger.warning("AI failed for %s, generated fallback", notif_type)
        await record_notification_sent(
            db, user_id, notif_type, message=fallback, success=False,
        )
        return {"status": "fallback", "type": notif_type, "message": fallback, "ai": False}


async def do_health_monitor(
    db: AsyncSession,
    user_id: uuid.UUID,
    user: User,
) -> dict:
    """Run multi-signal health analysis with priority waterfall.

    Priority order (only the highest-priority alert fires):
    1. Chronic fatigue (most serious)
    2. Recovery protocol
    3. Readiness prediction (evening only)

    Returns dict with status and actions taken.
    """
    actions: list[dict] = []
    hour = datetime.datetime.now().hour

    # 1. Chronic fatigue: detect 5+ consecutive bad nights
    # TODO Phase 4: implement detect_chronic_fatigue() from wearable history

    # 2. Recovery protocol: detect recent intense activity
    # TODO Phase 4: implement detect_post_activity_recovery() from wearable data

    # 3. Readiness prediction (evening only, 19h-21h)
    if 19 <= hour <= 21:
        snapshot = await get_latest_snapshot(db, user_id)
        if snapshot:
            score, _, _ = compute_readiness_score(snapshot)
            if score < 45:
                logger.info("Low readiness for user %s: %d/100", user.name, score)
                if await can_send_notification(db, user_id, "readiness_prediction"):
                    result = await do_ai_notify(db, user_id, user, "readiness_prediction")
                    actions.append({
                        "type": "readiness_prediction",
                        "result": result.get("status"),
                        "score": score,
                    })

    if not actions:
        logger.debug("Health monitor: no alerts for user %s", user.name)

    return {"status": "ok", "actions": actions}
