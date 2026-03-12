"""User management endpoints."""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.models.user import User
from backend.services.wearable import generate_widget_session

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
    provider: str | None = None  # e.g., "GARMIN", "APPLE", "OURA"


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
        "has_terra": user.terra_user_id is not None,
    }


@router.post("/{user_id}/connect-wearable")
async def connect_wearable(
    user_id: uuid.UUID,
    data: ConnectWearableRequest | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Generate a Terra widget session URL for connecting a wearable."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Build provider filter
    providers = None
    if data and data.provider and data.provider != "ALL":
        providers = data.provider

    session = await generate_widget_session(
        reference_id=str(user.id),
        providers=providers,
    )
    if not session:
        raise HTTPException(status_code=500, detail="Failed to create widget session")

    return {
        "user_id": str(user.id),
        "widget_url": session.get("url"),
        "session_id": session.get("session_id"),
        "expires_in": session.get("expires_in"),
    }
