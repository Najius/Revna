"""Revna — Telegram bot: message sending, check-ins, conversational replies.

Adapted from coach/telegram.py:
- Webhook-based (no polling) — incoming messages routed from api/webhooks.py
- httpx instead of urllib.request
- Multi-tenant (user_id, chat_id per user)
- Async operations
- Generalized prompts (no rehab-specific context)
"""

import datetime
import json
import logging
import re
import uuid

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import settings
from backend.core.constants import MEDICAL_DISCLAIMER
from backend.core.prompts import (
    PSY_TECHNIQUES,
    WELLNESS_SUGGESTIONS,
    HEALTH_DATA_INTERPRETATION,
    PROMPT_RULES,
)
from backend.services.ai import call_claude_api, call_claude_notification
from backend.services.health import (
    get_latest_snapshot,
    format_snapshot_for_prompt,
    build_temporal_context,
)
from backend.services.tracking import (
    can_send_notification,
    record_notification_sent,
    build_feelings_context,
    build_conversation_context,
    save_conversation_message,
    get_recent_conversations,
    can_reply_conversation,
)
from backend.services.wearable import generate_widget_session
from backend.services.garmin import test_garmin_credentials, sync_garmin_data
from backend.models.user import User
from backend.models.feeling import Feeling

logger = logging.getLogger(__name__)

# ─── Garmin connection flow state ────────────────────────────────────────────
# Simple in-memory state for MVP (use Redis in production)
_garmin_flow_state: dict[int, dict] = {}

# ─── Prompt injection patterns ──────────────────────────────────────────────

_INJECTION_PATTERNS = re.compile(
    r"(?:SYSTEM\s*(?:OVERRIDE|PROMPT|MESSAGE)|"
    r"IGNORE\s*(?:ALL\s*)?PREVIOUS|"
    r"OVERRIDE\s*(?:INSTRUCTIONS|RULES)|"
    r"NEW\s*INSTRUCTIONS|"
    r"ASSISTANT\s*MODE|"
    r"JAILBREAK|"
    r"DAN\s*MODE|"
    r"\[\s*SYSTEM\s*\]|"
    r"<\s*(?:system|instruction|admin))",
    re.IGNORECASE,
)
_MAX_INPUT_LENGTH = 500


# ─── Telegram API ───────────────────────────────────────────────────────────


async def send_telegram(
    chat_id: int,
    message: str,
    db: AsyncSession | None = None,
    user_id: uuid.UUID | None = None,
    msg_type: str = "notification",
    log_conversation: bool = True,
) -> bool:
    """Send a message via Telegram bot API. Returns True on success."""
    if not settings.telegram_bot_token:
        logger.error("No Telegram bot token configured")
        return False

    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "HTML",
    }

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage",
                json=payload,
            )
            resp.raise_for_status()
    except httpx.HTTPError as e:
        logger.error("Telegram send failed: %s", e)
        return False

    if log_conversation and db and user_id:
        await save_conversation_message(db, user_id, "coach", message, msg_type)

    return True


async def set_webhook(webhook_url: str) -> bool:
    """Register webhook URL with Telegram Bot API."""
    if not settings.telegram_bot_token:
        return False

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                f"https://api.telegram.org/bot{settings.telegram_bot_token}/setWebhook",
                json={"url": webhook_url, "allowed_updates": ["message"]},
            )
            resp.raise_for_status()
            result = resp.json()
            logger.info("Telegram webhook set: %s", result.get("description"))
            return result.get("ok", False)
    except httpx.HTTPError as e:
        logger.error("Telegram setWebhook failed: %s", e)
        return False


# ─── Input sanitization ─────────────────────────────────────────────────────


def _sanitize_input(text: str) -> str:
    """Sanitize user input against prompt injection and excessive length."""
    if not text:
        return ""
    text = text[:_MAX_INPUT_LENGTH]
    if _INJECTION_PATTERNS.search(text):
        logger.warning("Prompt injection pattern detected, stripping")
        text = _INJECTION_PATTERNS.sub("", text).strip()
    return text


# ─── Feelings parsing ───────────────────────────────────────────────────────


async def _parse_feelings(patient_text: str) -> dict:
    """Parse patient feelings using Claude Haiku. Returns parsed dict."""
    parse_prompt = f"""Analyse ce message d'un utilisateur qui suit sa sante.
Extrais les informations suivantes en JSON:

Message: "{patient_text}"

Retourne UNIQUEMENT ce JSON:
{{
  "mood": <1-10 ou null si pas mentionne>,
  "pain": <0-10 ou null si pas mentionne>,
  "energy": <1-10 ou null si pas mentionne>,
  "keywords": ["mot-cle 1", "mot-cle 2"],
  "sentiment": "positive|neutral|negative",
  "needs_attention": <true si la personne semble en detresse, false sinon>
}}"""

    parsed = call_claude_api(
        "Tu es un parser de texte. Extrais les informations demandees. JSON uniquement.",
        parse_prompt,
        model=settings.claude_model_haiku,
        max_tokens=200,
    )

    if not parsed:
        parsed = {
            "mood": None, "pain": None, "energy": None,
            "keywords": [], "sentiment": "neutral", "needs_attention": False,
        }
    return parsed


async def _store_feelings(
    db: AsyncSession, user_id: uuid.UUID,
    patient_text: str, parsed: dict,
) -> None:
    """Store parsed feelings in the database."""
    feeling = Feeling(
        user_id=user_id,
        raw_text=patient_text[:500],
        mood=str(parsed.get("mood")) if parsed.get("mood") is not None else None,
        energy=str(parsed.get("energy")) if parsed.get("energy") is not None else None,
        pain=str(parsed.get("pain")) if parsed.get("pain") is not None else None,
        sentiment=parsed.get("sentiment"),
        needs_attention=parsed.get("needs_attention", False),
    )
    db.add(feeling)
    await db.commit()


def _build_response_focus(parsed: dict) -> str:
    """Build response focus directive based on parsed feelings."""
    needs_attention = parsed.get("needs_attention", False)
    pain_level = parsed.get("pain")
    mood_level = parsed.get("mood")

    if needs_attention:
        return (
            "L'utilisateur semble en DETRESSE. Priorite: validation empathique, "
            "normalisation, technique d'auto-compassion."
        )
    elif pain_level and int(pain_level) >= 6:
        return (
            "Douleur significative. Priorite: validation, acceptation ACT, "
            "conseil repos/adaptation."
        )
    elif mood_level and int(mood_level) <= 4:
        return (
            "Moral bas. Priorite: validation chaleureuse, defusion cognitive, "
            "action engagee vers les valeurs."
        )
    return ""


# ─── Message classification ─────────────────────────────────────────────────


async def classify_message(
    db: AsyncSession, user_id: uuid.UUID, patient_text: str,
) -> str:
    """Classify incoming message based on conversation context.

    Returns one of: "checkin_reply", "follow_up", "spontaneous".
    """
    conversations = await get_recent_conversations(db, user_id, hours=1)

    # Find last coach message
    last_coach_msg = None
    for msg in reversed(conversations):
        if msg.role == "coach":
            last_coach_msg = msg
            break

    if not last_coach_msg or not last_coach_msg.created_at:
        return "spontaneous"

    now = datetime.datetime.now(datetime.timezone.utc)
    created = last_coach_msg.created_at
    if created.tzinfo is None:
        created = created.replace(tzinfo=datetime.timezone.utc)
    minutes_since = (now - created).total_seconds() / 60

    # Reply to a check-in (< 30 min after check-in sent)
    if last_coach_msg.msg_type in ("morning_checkin", "evening_checkin") and minutes_since < 30:
        return "checkin_reply"

    # Follow-up in ongoing conversation (< 15 min after last coach response)
    if minutes_since < 15:
        return "follow_up"

    return "spontaneous"


# ─── Reply handlers ─────────────────────────────────────────────────────────


async def _handle_checkin_reply(
    db: AsyncSession, user_id: uuid.UUID, user: User,
    patient_text: str, parsed: dict,
) -> str | None:
    """Handle a user reply to a morning/evening check-in."""
    snapshot = await get_latest_snapshot(db, user_id)
    health_str = format_snapshot_for_prompt(snapshot)
    temporal_ctx = await build_temporal_context(db, user_id, snapshot)
    feelings_ctx = await build_feelings_context(db, user_id)
    conversation_ctx = await build_conversation_context(db, user_id)

    response_focus = _build_response_focus(parsed)

    response_prompt = f"""L'utilisateur a repondu a ton check-in. Voici sa reponse:

"{patient_text}"

Analyse des ressentis: {json.dumps(parsed, ensure_ascii=False)}

{response_focus}

{conversation_ctx}

{temporal_ctx}

{feelings_ctx}

DONNEES SANTE ACTUELLES:
{health_str}

Genere une reponse Telegram HTML (5-10 lignes) qui:
1. VALIDE d'abord ce que l'utilisateur a exprime (empathie, pas de minimisation)
2. Contextualise avec les donnees objectives (BB, stress, sommeil) — "tes donnees confirment que..."
3. Propose UNE technique psy adaptee (voir matrice contextuelle)
4. Propose UNE suggestion bien-etre concrete (nutrition, activite, hydratation)
5. Termine par une note encourageante ou une question de suivi

INTERDIT: minimiser, donner des injonctions, ton clinique.
Format: HTML Telegram. Reponds UNIQUEMENT le message."""

    system_prompt = f"""Tu es un coach sante holistique bienveillant pour {user.name}.
Tu viens de recevoir la reponse de l'utilisateur a ton check-in.

{PSY_TECHNIQUES}

{WELLNESS_SUGGESTIONS}

{HEALTH_DATA_INTERPRETATION}

{PROMPT_RULES}"""

    return call_claude_notification(system_prompt, response_prompt,
                                    max_tokens=500, temperature=0.4)


async def _handle_spontaneous(
    db: AsyncSession, user_id: uuid.UUID, user: User,
    patient_text: str, parsed: dict,
) -> str | None:
    """Handle a spontaneous message (not a check-in reply)."""
    snapshot = await get_latest_snapshot(db, user_id)
    health_str = format_snapshot_for_prompt(snapshot)
    temporal_ctx = await build_temporal_context(db, user_id, snapshot)
    feelings_ctx = await build_feelings_context(db, user_id)
    conversation_ctx = await build_conversation_context(db, user_id)

    response_focus = _build_response_focus(parsed)

    response_prompt = f"""L'utilisateur t'envoie un message de sa propre initiative:

"{patient_text}"

Analyse des ressentis: {json.dumps(parsed, ensure_ascii=False)}

{response_focus}

{conversation_ctx}

{temporal_ctx}

{feelings_ctx}

DONNEES SANTE ACTUELLES:
{health_str}

Genere une reponse Telegram HTML (3-8 lignes) qui:
1. Reponds directement a ce que l'utilisateur dit ou demande
2. Si c'est une question pratique (exercice, activite, alimentation): reponse concrete basee sur les donnees de sante
3. Si c'est un partage emotionnel: VALIDE d'abord, puis contextualise avec les donnees objectives
4. Sois naturel et conversationnel — pas de structure rigide
5. Termine par une question de suivi seulement si c'est naturel

INTERDIT: minimiser, donner des injonctions, ton clinique, repeter des infos deja donnees.
Format: HTML Telegram. Reponds UNIQUEMENT le message."""

    system_prompt = f"""Tu es un coach sante holistique bienveillant pour {user.name}.

L'utilisateur t'ecrit de sa propre initiative — ce n'est PAS un check-in.
Reponds comme un vrai compagnon bienveillant: naturel, chaleureux, concis.
Adapte la longueur de ta reponse a la longueur du message.

{PSY_TECHNIQUES}

{WELLNESS_SUGGESTIONS}

{HEALTH_DATA_INTERPRETATION}

{PROMPT_RULES}"""

    return call_claude_notification(system_prompt, response_prompt,
                                    max_tokens=500, temperature=0.5)


async def _handle_follow_up(
    db: AsyncSession, user_id: uuid.UUID, user: User,
    patient_text: str, parsed: dict,
) -> str | None:
    """Handle a follow-up message in an ongoing conversation."""
    snapshot = await get_latest_snapshot(db, user_id)
    health_str = format_snapshot_for_prompt(snapshot)
    temporal_ctx = await build_temporal_context(db, user_id, snapshot)
    feelings_ctx = await build_feelings_context(db, user_id)
    conversation_ctx = await build_conversation_context(db, user_id)

    response_focus = _build_response_focus(parsed)

    response_prompt = f"""L'utilisateur continue la conversation en cours:

"{patient_text}"

Analyse des ressentis: {json.dumps(parsed, ensure_ascii=False)}

{response_focus}

{conversation_ctx}

{temporal_ctx}

{feelings_ctx}

DONNEES SANTE ACTUELLES:
{health_str}

Genere une reponse Telegram HTML (2-6 lignes) qui:
1. Tient compte du fil de conversation — ne repete PAS les informations deja donnees
2. Reponds directement a ce que l'utilisateur vient de dire
3. Sois concis — c'est une suite de conversation, pas un nouveau sujet
4. Si c'est une question: donne la reponse directement

INTERDIT: re-saluer, re-resumer les donnees, structure rigide.
Format: HTML Telegram. Reponds UNIQUEMENT le message."""

    system_prompt = f"""Tu es un coach sante holistique bienveillant pour {user.name}.

Tu es EN CONVERSATION avec l'utilisateur. Il repond a ton dernier message.
Sois concis et naturel. Ne repete pas ce que tu as deja dit.

{PSY_TECHNIQUES}

{WELLNESS_SUGGESTIONS}

{HEALTH_DATA_INTERPRETATION}

{PROMPT_RULES}"""

    return call_claude_notification(system_prompt, response_prompt,
                                    max_tokens=400, temperature=0.5)


# ─── Check-ins ──────────────────────────────────────────────────────────────


async def do_checkin(
    db: AsyncSession, user_id: uuid.UUID, user: User,
    checkin_time: str,
) -> dict:
    """Send a Telegram check-in (morning/evening). Returns result dict."""
    if checkin_time not in ("morning", "evening"):
        return {"status": "error", "reason": "invalid_time"}

    checkin_key = f"checkin_{checkin_time}"
    if not await can_send_notification(db, user_id, checkin_key):
        return {"status": "cooldown", "type": checkin_key}

    snapshot = await get_latest_snapshot(db, user_id)
    health_str = format_snapshot_for_prompt(snapshot)
    temporal_ctx = await build_temporal_context(db, user_id, snapshot)
    feelings_ctx = await build_feelings_context(db, user_id)

    if checkin_time == "morning":
        checkin_prompt = f"""Tu es un coach sante bienveillant et holistique pour {user.name}.

Il est 7h30, c'est le check-in du matin. Tu veux savoir comment l'utilisateur se sent
apres sa nuit, avant de commencer la journee.

{temporal_ctx}

{feelings_ctx}

DONNEES SANTE (nuit):
{health_str}

Genere un message Telegram HTML (5-8 lignes) qui:
1. Salue chaleureusement (emoji matin)
2. Resume les donnees de la nuit en 1-2 lignes (sommeil, BB au reveil, comparaison avec hier)
3. Pose la question: "Comment tu te sens ce matin?"
4. Demande specifiquement: humeur (1-10), douleur (0-10), energie (1-10)
5. Ton chaleureux et bienveillant

Format: HTML Telegram (<b>, <i>). Reponds UNIQUEMENT le message."""
    else:
        checkin_prompt = f"""Tu es un coach sante bienveillant et holistique pour {user.name}.

Il est 20h30, c'est le check-in du soir. Tu veux faire un bilan emotionnel
de la journee.

{temporal_ctx}

{feelings_ctx}

DONNEES SANTE (journee complete):
{health_str}

Genere un message Telegram HTML (5-8 lignes) qui:
1. Salue chaleureusement (emoji soir)
2. Resume la journee en 2-3 lignes (BB, stress, pas vs objectif, comparaison hier)
3. Pose la question: "Comment s'est passee ta journee?"
4. Demande specifiquement: douleur (0-10), moral (1-10), fatigue (1-10)
5. Ton chaleureux et bienveillant

Format: HTML Telegram (<b>, <i>). Reponds UNIQUEMENT le message."""

    system_prompt = f"""Tu es un coach sante holistique bienveillant.
Tu communiques via Telegram.

{WELLNESS_SUGGESTIONS}

{HEALTH_DATA_INTERPRETATION}

{PROMPT_RULES}"""

    message = call_claude_notification(
        system_prompt, checkin_prompt, max_tokens=400, temperature=0.5,
    )
    if not message:
        return {"status": "error", "type": checkin_key}

    chat_id = user.telegram_chat_id
    if not chat_id:
        return {"status": "error", "reason": "no_chat_id"}

    await send_telegram(
        chat_id, message, db=db, user_id=user_id,
        msg_type=f"{checkin_time}_checkin",
    )
    await record_notification_sent(db, user_id, checkin_key)
    logger.info("Sent %s check-in to user %s", checkin_time, user.name)
    return {"status": "ok", "type": checkin_key}


# ─── Main message router ────────────────────────────────────────────────────


async def process_reply(
    db: AsyncSession, user_id: uuid.UUID, user: User,
    patient_text: str,
) -> dict:
    """Process any incoming Telegram message. Routes to the right handler."""
    # Sanitize input
    patient_text = _sanitize_input(patient_text)
    if not patient_text:
        logger.debug("Empty after sanitization, skipping")
        return {"status": "rejected", "reason": "empty_after_sanitize"}

    logger.info("Processing message from %s: %s", user.name, patient_text[:80])

    # Classify message type
    msg_type = await classify_message(db, user_id, patient_text)
    logger.debug("Classified as: %s", msg_type)

    # Log the user message in conversation history
    await save_conversation_message(db, user_id, "user", patient_text, msg_type)

    # Parse feelings (always — for long-term tracking)
    parsed = await _parse_feelings(patient_text)
    await _store_feelings(db, user_id, patient_text, parsed)

    # Rate limit check for non-checkin replies
    if msg_type != "checkin_reply" and not await can_reply_conversation(db, user_id):
        logger.debug("Rate limited — skipping response for %s", user.name)
        return {"status": "rate_limited", "parsed": parsed}

    # Route to appropriate handler
    if msg_type == "checkin_reply":
        response = await _handle_checkin_reply(db, user_id, user, patient_text, parsed)
    elif msg_type == "follow_up":
        response = await _handle_follow_up(db, user_id, user, patient_text, parsed)
    else:
        response = await _handle_spontaneous(db, user_id, user, patient_text, parsed)

    if response:
        response += MEDICAL_DISCLAIMER
        chat_id = user.telegram_chat_id
        if chat_id:
            await send_telegram(
                chat_id, response, db=db, user_id=user_id,
                msg_type="conversation",
            )
        logger.info("Sent %s response to %s", msg_type, user.name)
        return {"status": "ok", "type": msg_type, "parsed": parsed}
    else:
        logger.warning("AI response generation failed (%s) for %s", msg_type, user.name)
        return {"status": "error", "type": msg_type, "parsed": parsed}


# ─── /start command ─────────────────────────────────────────────────────────


async def handle_start_command(
    db: AsyncSession, chat_id: int, telegram_username: str | None,
) -> None:
    """Handle /start command — onboard a new user or greet existing."""
    # Check if user already exists with this chat_id
    result = await db.execute(
        select(User).where(User.telegram_chat_id == chat_id)
    )
    existing = result.scalar_one_or_none()

    if existing:
        await send_telegram(
            chat_id,
            f"Salut <b>{existing.name}</b> ! Je suis toujours la. "
            f"Ecris-moi quand tu veux, je suis a l'ecoute.\n\n"
            f"Tape /connect pour connecter un wearable.",
        )
        return

    # Create new user
    name = telegram_username or f"User-{str(chat_id)[-4:]}"
    new_user = User(
        name=name,
        telegram_chat_id=chat_id,
        telegram_username=telegram_username,
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    welcome = (
        f"Bienvenue <b>{name}</b> ! Je suis Revna, ton coach sante personnel.\n\n"
        "Je vais t'accompagner au quotidien en analysant tes donnees de sante "
        "(sommeil, stress, activite) pour t'envoyer des conseils personnalises.\n\n"
        "Pour commencer, tape /connect pour connecter ton wearable "
        "(Garmin, Apple Watch, Oura, Whoop...).\n\n"
        "Tu peux m'ecrire a tout moment — je suis la pour toi."
    )
    await send_telegram(chat_id, welcome)
    logger.info("New user onboarded: %s (chat_id=%d)", name, chat_id)


async def handle_connect_command(db: AsyncSession, chat_id: int) -> None:
    """Handle /connect command — start Garmin connection flow."""
    result = await db.execute(
        select(User).where(User.telegram_chat_id == chat_id)
    )
    user = result.scalar_one_or_none()

    if not user:
        await send_telegram(
            chat_id,
            "Je ne te connais pas encore ! Envoie /start pour commencer.",
        )
        return

    # Check if already connected to Garmin
    if user.garmin_email:
        await send_telegram(
            chat_id,
            f"Tu es deja connecte a Garmin ({user.garmin_email}).\n\n"
            "Si tu veux changer de compte, envoie ton nouvel email Garmin Connect.",
        )
        _garmin_flow_state[chat_id] = {"step": "email", "user_id": str(user.id)}
        return

    # Start Garmin connection flow
    _garmin_flow_state[chat_id] = {"step": "email", "user_id": str(user.id)}
    await send_telegram(
        chat_id,
        "Pour connecter ta montre Garmin, j'ai besoin de tes identifiants "
        "Garmin Connect.\n\n"
        "<b>Etape 1/2</b>: Envoie-moi ton <b>email</b> Garmin Connect.",
    )
    logger.info("Started Garmin flow for user %s", user.name)


def is_in_garmin_flow(chat_id: int) -> bool:
    """Check if user is in Garmin connection flow."""
    return chat_id in _garmin_flow_state


async def handle_garmin_flow(db: AsyncSession, chat_id: int, text: str) -> None:
    """Handle Garmin connection flow steps."""
    state = _garmin_flow_state.get(chat_id)
    if not state:
        return

    step = state.get("step")
    user_id = state.get("user_id")

    if step == "email":
        # Validate email format
        if "@" not in text or "." not in text:
            await send_telegram(
                chat_id,
                "Cet email ne semble pas valide. Envoie ton email Garmin Connect.",
            )
            return

        state["email"] = text.strip()
        state["step"] = "password"
        await send_telegram(
            chat_id,
            "<b>Etape 2/2</b>: Maintenant, envoie-moi ton <b>mot de passe</b> "
            "Garmin Connect.\n\n"
            "<i>(Le message sera supprime apres verification)</i>",
        )

    elif step == "password":
        email = state.get("email")
        password = text.strip()

        await send_telegram(chat_id, "Verification en cours...")

        # Test credentials
        if await test_garmin_credentials(email, password):
            # Save to database
            result = await db.execute(
                select(User).where(User.telegram_chat_id == chat_id)
            )
            user = result.scalar_one_or_none()

            if user:
                user.garmin_email = email
                user.garmin_password = password
                user.wearable_type = "garmin"
                await db.commit()

                # Clear flow state
                del _garmin_flow_state[chat_id]

                await send_telegram(
                    chat_id,
                    "Connexion reussie ! Ta montre Garmin est maintenant connectee.\n\n"
                    "Je vais synchroniser tes donnees... Un instant.",
                )

                # Initial sync
                try:
                    snapshots = await sync_garmin_data(db, user, days_back=3)
                    if snapshots:
                        await send_telegram(
                            chat_id,
                            f"J'ai recupere {len(snapshots)} jour(s) de donnees !\n\n"
                            "Je vais maintenant t'envoyer des conseils personnalises "
                            "bases sur ton sommeil, ton stress et ton activite.\n\n"
                            "A demain matin pour ton premier check-in !",
                        )
                    else:
                        await send_telegram(
                            chat_id,
                            "Connexion etablie ! Les donnees seront synchronisees "
                            "dans les prochaines heures.",
                        )
                except Exception as e:
                    logger.error("Initial Garmin sync failed: %s", e)
                    await send_telegram(
                        chat_id,
                        "Connexion etablie ! Je synchroniserai tes donnees bientot.",
                    )

                logger.info("Garmin connected for user %s", user.name)
        else:
            await send_telegram(
                chat_id,
                "Identifiants incorrects. Verifie ton email et mot de passe "
                "Garmin Connect et reessaie.\n\n"
                "Envoie ton <b>email</b> Garmin Connect.",
            )
            state["step"] = "email"
            if "email" in state:
                del state["email"]
