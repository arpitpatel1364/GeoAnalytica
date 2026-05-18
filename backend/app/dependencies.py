from datetime import datetime, timezone
from typing import Optional
import uuid

from fastapi import Depends, HTTPException, Query, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models.user import User
from app.services.auth_service import decode_access_token

security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )

    result = await db.execute(select(User).where(User.id == uuid.UUID(user_id)))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled",
        )

    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    return current_user


async def get_admin_user(
    current_user: User = Depends(get_current_user),
) -> User:
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user


async def check_query_limit(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Check and enforce daily query limit based on user tier."""
    # Determine daily limit by tier
    tier = current_user.tier
    if tier == "pro":
        daily_limit = settings.MAX_PRO_QUERIES_PER_DAY
    else:
        daily_limit = settings.MAX_FREE_QUERIES_PER_DAY

    now = datetime.now(timezone.utc)

    # Reset counter if it's a new day
    if current_user.queries_today_reset_at:
        reset_date = current_user.queries_today_reset_at.date()
        if reset_date < now.date():
            current_user.queries_today = 0
            current_user.queries_today_reset_at = now
    else:
        current_user.queries_today_reset_at = now

    if current_user.queries_today >= daily_limit:
        if tier == "pro":
            detail = (
                f"Pro tier daily limit reached: {daily_limit} queries/day. "
                "Contact support if you need a higher limit."
            )
        else:
            detail = (
                f"Free tier limit reached: {daily_limit} queries/day. "
                "Upgrade to Pro for 500 queries/day and unlimited fields."
            )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=detail,
        )

    current_user.queries_today += 1
    await db.commit()
    return current_user


def get_pagination(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
):
    return {"offset": (page - 1) * page_size, "limit": page_size}
