import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.api_key import ApiKey
from app.models.user import User
from app.schemas.api_key import ApiKeyCreate, ApiKeyRead, ApiKeyTestResult
from app.services.encryption_service import encrypt_key, decrypt_key
from app.services.direct_api_fetcher import test_api_key_connection

router = APIRouter()


def _mask_key(key: str) -> str:
    if len(key) <= 8:
        return "X" * len(key)
    return "X" * (len(key) - 4) + key[-4:]


@router.get("", response_model=List[ApiKeyRead])
async def list_api_keys(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ApiKey).where(ApiKey.user_id == current_user.id)
    )
    return result.scalars().all()


@router.post("", response_model=ApiKeyRead, status_code=status.HTTP_201_CREATED)
async def add_api_key(
    data: ApiKeyCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Check if service already exists for user
    existing = await db.execute(
        select(ApiKey).where(
            ApiKey.user_id == current_user.id,
            ApiKey.service_name == data.service_name,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"API key for {data.service_name} already exists. Delete it first.",
        )

    encrypted = encrypt_key(data.api_key)
    key_preview = _mask_key(data.api_key)

    api_key = ApiKey(
        user_id=current_user.id,
        service_name=data.service_name,
        encrypted_key=encrypted,
        key_preview=key_preview,
        is_valid=True,
    )
    db.add(api_key)
    await db.commit()
    await db.refresh(api_key)
    return api_key


@router.post("/{key_id}/test", response_model=ApiKeyTestResult)
async def test_api_key(
    key_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ApiKey).where(
            ApiKey.id == key_id,
            ApiKey.user_id == current_user.id,
        )
    )
    api_key = result.scalar_one_or_none()
    if not api_key:
        raise HTTPException(status_code=404, detail="API key not found")

    raw_key = decrypt_key(api_key.encrypted_key)
    test_result = await test_api_key_connection(api_key.service_name, raw_key)

    from datetime import datetime, timezone
    api_key.is_valid = test_result.success
    api_key.last_tested_at = datetime.now(timezone.utc)
    if test_result.rate_limit_info:
        api_key.rate_limit_info = test_result.rate_limit_info
    await db.commit()

    return test_result


@router.delete("/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_api_key(
    key_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ApiKey).where(
            ApiKey.id == key_id,
            ApiKey.user_id == current_user.id,
        )
    )
    api_key = result.scalar_one_or_none()
    if not api_key:
        raise HTTPException(status_code=404, detail="API key not found")
    await db.delete(api_key)
    await db.commit()
