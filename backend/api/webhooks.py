"""Webhook endpoints — Telegram, Terra & Google OAuth."""

import uuid

import structlog
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import settings
from backend.database import get_db
from backend.models.user import User
from backend.services.telegram import (
    handle_start_command,
    handle_connect_command,
    handle_garmin_command,
    handle_pixelwatch_command,
    handle_garmin_flow,
    is_in_garmin_flow,
    process_reply,
    send_telegram,
    answer_callback_query,
)
from backend.services.google_fit import exchange_code_for_tokens, sync_google_fit_data
from backend.services.wearable import process_terra_webhook, verify_terra_signature

logger = structlog.get_logger()

router = APIRouter(tags=["webhooks"])


@router.post("/telegram")
async def telegram_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    """Receive inbound Telegram messages and route to bot logic."""
    body = await request.json()
    update_id = body.get("update_id")

    # Handle inline button callbacks
    callback_query = body.get("callback_query")
    if callback_query:
        cb_id = callback_query.get("id")
        chat_id = callback_query.get("message", {}).get("chat", {}).get("id")
        data = callback_query.get("data", "")

        await answer_callback_query(cb_id)

        if data == "connect_garmin" and chat_id:
            await handle_garmin_command(db, chat_id)
        elif data == "connect_pixelwatch" and chat_id:
            await handle_pixelwatch_command(db, chat_id)

        return {"ok": True}

    message = body.get("message")

    if not message:
        logger.debug("webhook.telegram.no_message", update_id=update_id)
        return {"ok": True}

    chat_id = message.get("chat", {}).get("id")
    text = message.get("text", "").strip()
    username = message.get("from", {}).get("username")

    if not chat_id or not text:
        logger.debug("webhook.telegram.skip", chat_id=chat_id, has_text=bool(text))
        return {"ok": True}

    logger.info("webhook.telegram", update_id=update_id, chat_id=chat_id, text=text[:80])

    # /start command — onboarding
    if text.startswith("/start"):
        await handle_start_command(db, chat_id, username)
        return {"ok": True}

    # /connect command — wearable connection menu
    if text.startswith("/connect"):
        await handle_connect_command(db, chat_id)
        return {"ok": True}

    # /garmin command — direct Garmin login
    if text.startswith("/garmin"):
        await handle_garmin_command(db, chat_id)
        return {"ok": True}

    # /pixelwatch command — Pixel Watch via Terra/Google
    if text.startswith("/pixelwatch"):
        await handle_pixelwatch_command(db, chat_id)
        return {"ok": True}

    # Check if user is in Garmin connection flow
    if is_in_garmin_flow(chat_id):
        await handle_garmin_flow(db, chat_id, text)
        return {"ok": True}

    # Look up user by chat_id
    result = await db.execute(
        select(User).where(User.telegram_chat_id == chat_id)
    )
    user = result.scalar_one_or_none()

    if not user:
        logger.warning("webhook.telegram.unknown_user", chat_id=chat_id)
        await send_telegram(
            chat_id,
            "Je ne te connais pas encore ! Envoie /start pour commencer.",
        )
        return {"ok": True}

    if not user.is_active:
        logger.info("webhook.telegram.inactive_user", user_id=str(user.id))
        return {"ok": True}

    # Route to main message processor
    if settings.pause_ai:
        await send_telegram(chat_id, "Je suis en pause pour le moment. A bientot !")
        return {"ok": True}
    await process_reply(db, user.id, user, text)
    return {"ok": True}


@router.post("/terra")
async def terra_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    """Receive Terra API data pushes (wearable sync)."""
    raw_body = (await request.body()).decode()
    signature = request.headers.get("terra-signature", "")

    if signature and not verify_terra_signature(raw_body, signature):
        logger.warning("webhook.terra.invalid_signature")
        return {"ok": False, "error": "invalid signature"}

    body = await request.json()
    logger.info("webhook.terra", event_type=body.get("type"))

    result = await process_terra_webhook(db, body)
    return {"ok": True, **result}


@router.get("/google/callback")
async def google_oauth_callback(
    code: str = "",
    state: str = "",
    error: str = "",
    db: AsyncSession = Depends(get_db),
):
    """Handle Google OAuth2 callback after user authorizes Google Fit access."""
    if error or not code:
        logger.warning("webhook.google.oauth_error", error=error)
        return HTMLResponse(
            "<h2>Connexion echouee</h2><p>Retourne sur Telegram et reessaie /pixelwatch</p>"
        )

    # state = user_id
    try:
        user_id = uuid.UUID(state)
    except ValueError:
        logger.error("webhook.google.invalid_state", state=state)
        return HTMLResponse("<h2>Erreur</h2><p>Lien invalide.</p>")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        logger.error("webhook.google.user_not_found", user_id=state)
        return HTMLResponse("<h2>Erreur</h2><p>Utilisateur introuvable.</p>")

    # Exchange code for tokens
    tokens = await exchange_code_for_tokens(code)
    if not tokens or "refresh_token" not in tokens:
        logger.error("webhook.google.token_exchange_failed", user_id=state)
        if user.telegram_chat_id:
            await send_telegram(
                user.telegram_chat_id,
                "Erreur lors de la connexion Google Fit. Reessaie /pixelwatch.",
            )
        return HTMLResponse(
            "<h2>Connexion echouee</h2><p>Retourne sur Telegram et reessaie /pixelwatch</p>"
        )

    # Save refresh token
    user.google_refresh_token = tokens["refresh_token"]
    user.wearable_type = "pixel_watch"
    await db.commit()

    logger.info("webhook.google.connected", user=user.name)

    # Notify user via Telegram
    if user.telegram_chat_id:
        await send_telegram(
            user.telegram_chat_id,
            "Connexion Google Fit reussie ! Ta Pixel Watch est connectee.\n\n"
            "Je synchronise tes donnees... Un instant.",
        )

        # Initial sync
        try:
            snapshots = await sync_google_fit_data(db, user, days_back=3)
            if snapshots:
                await send_telegram(
                    user.telegram_chat_id,
                    f"J'ai recupere {len(snapshots)} jour(s) de donnees !\n\n"
                    "Je vais maintenant t'envoyer des conseils personnalises.\n\n"
                    "A demain matin pour ton premier check-in !",
                )
            else:
                await send_telegram(
                    user.telegram_chat_id,
                    "Connexion etablie ! Les donnees seront synchronisees "
                    "dans les prochaines heures.",
                )
        except Exception as e:
            logger.error("Initial Google Fit sync failed: %s", e)
            await send_telegram(
                user.telegram_chat_id,
                "Connexion etablie ! Je synchroniserai tes donnees bientot.",
            )

    return HTMLResponse(
        "<h2>Connexion reussie !</h2>"
        "<p>Tu peux fermer cette page et retourner sur Telegram.</p>"
    )
