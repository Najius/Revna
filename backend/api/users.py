"""User management endpoints."""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.models.user import User
from backend.services.google_fit import build_oauth_url

router = APIRouter(tags=["users"])


# ─── Schemas ──────────────────────────────────────────────────────────────────

class UserRegister(BaseModel):
    name: str
    email: EmailStr


class UserResponse(BaseModel):
    user_id: str
    name: str
    email: str


class ConnectWearableRequest(BaseModel):
    provider: str | None = None  # "garmin" or "pixel_watch"


# ─── Registration ─────────────────────────────────────────────────────────────

class UserLogin(BaseModel):
    email: EmailStr


@router.post("/register", response_model=UserResponse)
async def register_user(data: UserRegister, db: AsyncSession = Depends(get_db)):
    """Register a new user from the onboarding page."""
    # Check if email already exists
    result = await db.execute(select(User).where(User.email == data.email))
    existing = result.scalar_one_or_none()

    if existing:
        # Return existing user instead of error (idempotent)
        return UserResponse(
            user_id=str(existing.id),
            name=existing.name,
            email=existing.email,
        )

    # Create new user
    user = User(
        name=data.name,
        email=data.email,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    return UserResponse(
        user_id=str(user.id),
        name=user.name,
        email=user.email,
    )


@router.post("/login", response_model=UserResponse)
async def login_user(data: UserLogin, db: AsyncSession = Depends(get_db)):
    """Login with email — returns user info if account exists."""
    result = await db.execute(select(User).where(User.email == data.email))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="No account found with this email")

    return UserResponse(
        user_id=str(user.id),
        name=user.name,
        email=user.email,
    )


@router.get("/{user_id}/status")
async def user_status(user_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Get current status of a user (readiness, last notification, etc.)."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {
        "id": str(user.id),
        "name": user.name,
        "is_active": user.is_active,
        "wearable_type": user.wearable_type,
        "has_garmin": user.garmin_email is not None,
        "has_google_fit": user.google_refresh_token is not None,
    }


@router.post("/{user_id}/connect-wearable")
async def connect_wearable(
    user_id: uuid.UUID,
    data: ConnectWearableRequest | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Return connection instructions for Garmin or Pixel Watch."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    provider = (data.provider or "").lower() if data else ""

    if provider == "pixel_watch":
        return {
            "user_id": str(user.id),
            "provider": "pixel_watch",
            "oauth_url": build_oauth_url(user.id),
        }
    elif provider == "garmin":
        return {
            "user_id": str(user.id),
            "provider": "garmin",
            "method": "telegram",
            "instructions": "Use /garmin command in the Telegram bot to connect.",
        }
    else:
        return {
            "user_id": str(user.id),
            "supported_providers": ["garmin", "pixel_watch"],
            "instructions": "Use /connect in the Telegram bot, or specify a provider.",
        }
