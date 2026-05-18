from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.user import UserRead, UserUpdate, PasswordChangeRequest, UserStats
from app.services.auth_service import hash_password, verify_password
from app.config import settings

router = APIRouter()

# Tier limits mapping — single source of truth for the API
TIER_LIMITS = {
    "free": {
        "queries_per_day":        settings.MAX_FREE_QUERIES_PER_DAY,
        "fields_per_query":       settings.MAX_FREE_FIELDS_PER_QUERY,
        "export_rows":            settings.MAX_FREE_EXPORT_ROWS,
        "concurrent_queries":     settings.MAX_FREE_CONCURRENT_QUERIES,
        "api_keys":               3,
        "alerts":                 5,
        "ai_narrative":           False,
        "scheduled_exports":      False,
        "advanced_analytics":     False,
        "priority_support":       False,
    },
    "pro": {
        "queries_per_day":        settings.MAX_PRO_QUERIES_PER_DAY,
        "fields_per_query":       settings.MAX_PRO_FIELDS_PER_QUERY,
        "export_rows":            settings.MAX_PRO_EXPORT_ROWS,
        "concurrent_queries":     settings.MAX_PRO_CONCURRENT_QUERIES,
        "api_keys":               25,
        "alerts":                 50,
        "ai_narrative":           True,
        "scheduled_exports":      True,
        "advanced_analytics":     True,
        "priority_support":       True,
    },
}


@router.get("/me", response_model=UserRead)
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.put("/me", response_model=UserRead)
async def update_me(
    data: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if data.full_name is not None:
        current_user.full_name = data.full_name
    if data.preferences is not None:
        current_user.preferences = data.preferences
    await db.commit()
    await db.refresh(current_user)
    return current_user


@router.post("/me/change-password", status_code=status.HTTP_204_NO_CONTENT)
async def change_password(
    data: PasswordChangeRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not verify_password(data.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )
    current_user.hashed_password = hash_password(data.new_password)
    await db.commit()


@router.get("/me/stats", response_model=UserStats)
async def get_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy import select, func
    from app.models.project import Project
    from app.models.query import Query
    from app.models.api_key import ApiKey
    from app.models.alert import Alert
    from datetime import datetime, timezone
    from app.config import settings

    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    projects_count = (await db.execute(
        select(func.count()).where(Project.user_id == current_user.id)
    )).scalar_one()

    total_queries_month = (await db.execute(
        select(func.count()).where(
            Query.user_id == current_user.id,
            Query.created_at >= month_start,
        )
    )).scalar_one()

    api_keys_connected = (await db.execute(
        select(func.count()).where(
            ApiKey.user_id == current_user.id,
            ApiKey.is_valid == True,  # noqa: E712
        )
    )).scalar_one()

    alerts_active = (await db.execute(
        select(func.count()).where(
            Alert.user_id == current_user.id,
            Alert.is_active == True,  # noqa: E712
        )
    )).scalar_one()

    return UserStats(
        queries_today=current_user.queries_today,
        queries_today_limit=TIER_LIMITS[current_user.tier]["queries_per_day"],
        total_queries_month=total_queries_month,
        api_keys_connected=api_keys_connected,
        alerts_active=alerts_active,
        projects_count=projects_count,
    )


# ── Tier information ───────────────────────────────────────────────────────────
@router.get("/me/tier")
async def get_tier_info(
    current_user: User = Depends(get_current_user),
):
    """Returns the user's current tier and all associated feature limits."""
    tier = current_user.tier
    limits = TIER_LIMITS.get(tier, TIER_LIMITS["free"])
    return {
        "tier":        tier,
        "is_premium":  tier == "pro",
        "limits":      limits,
        "display_name": "Pro" if tier == "pro" else "Free",
    }


# ── Simulated self-service upgrade (replace with payment provider in production) ───
@router.post("/me/upgrade", response_model=UserRead)
async def upgrade_to_pro(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Demo upgrade endpoint — promotes the current user to Pro tier.
    In production, replace this with a Stripe webhook / payment flow.
    """
    if current_user.tier == "pro":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You are already on the Pro plan",
        )
    current_user.tier = "pro"
    await db.commit()
    await db.refresh(current_user)
    return current_user


# ── Admin-only: downgrade any user back to free ────────────────────────────────
@router.post("/me/downgrade", response_model=UserRead)
async def downgrade_to_free(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Downgrade the current user back to the Free tier."""
    if current_user.tier == "free":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You are already on the Free plan",
        )
    current_user.tier = "free"
    await db.commit()
    await db.refresh(current_user)
    return current_user
