"""
Admin Router — user tier management, accessible only to is_admin=True users.
"""
import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_admin_user
from app.models.user import User
from app.schemas.user import UserRead

router = APIRouter()

VALID_TIERS = {"free", "pro"}


class TierUpdate(BaseModel):
    tier: str


class AdminUserRead(UserRead):
    """Extended user read for admin — includes tier and active status."""
    pass


# ── List all users ─────────────────────────────────────────────────────────────
@router.get("/users", response_model=List[AdminUserRead])
async def list_users(
    tier: Optional[str] = None,
    _admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """List all users. Optionally filter by tier."""
    stmt = select(User).order_by(User.created_at.desc())
    if tier:
        stmt = stmt.where(User.tier == tier)
    result = await db.execute(stmt)
    return result.scalars().all()


# ── Get single user ────────────────────────────────────────────────────────────
@router.get("/users/{user_id}", response_model=AdminUserRead)
async def get_user(
    user_id: uuid.UUID,
    _admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


# ── Upgrade / downgrade tier ──────────────────────────────────────────────────
@router.patch("/users/{user_id}/tier", response_model=AdminUserRead)
async def set_user_tier(
    user_id: uuid.UUID,
    data: TierUpdate,
    _admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Set a user's tier (free | pro). Callable only by admins."""
    if data.tier not in VALID_TIERS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid tier '{data.tier}'. Valid tiers: {sorted(VALID_TIERS)}",
        )

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    user.tier = data.tier
    await db.commit()
    await db.refresh(user)
    return user


# ── Toggle active status ───────────────────────────────────────────────────────
@router.patch("/users/{user_id}/active", response_model=AdminUserRead)
async def toggle_user_active(
    user_id: uuid.UUID,
    admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Toggle a user's active/inactive status. Admins cannot disable themselves."""
    if user_id == admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot disable your own account",
        )
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    user.is_active = not user.is_active
    await db.commit()
    await db.refresh(user)
    return user


# ── Self-service upgrade (demo / simulated) ───────────────────────────────────
# In production replace this with a real payment webhook from Stripe etc.
@router.post("/upgrade-demo", response_model=UserRead)
async def upgrade_to_pro_demo(
    current_user: User = Depends(get_admin_user),  # only admins can simulate for now
    db: AsyncSession = Depends(get_db),
):
    """Demo endpoint that upgrades the calling user to Pro."""
    current_user.tier = "pro"
    await db.commit()
    await db.refresh(current_user)
    return current_user
