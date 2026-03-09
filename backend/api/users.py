"""User management endpoints (admin)."""

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.models.user import User

router = APIRouter(tags=["users"])


@router.get("/{user_id}/status")
async def user_status(user_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Get current status of a user (readiness, last notification, etc.)."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        return {"error": "user not found"}, 404
    return {
        "id": str(user.id),
        "name": user.name,
        "is_active": user.is_active,
        "wearable_type": user.wearable_type,
    }
