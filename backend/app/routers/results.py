import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.dependencies import get_current_user
from app.models.query import Query as QueryModel
from app.models.result import Result, DataPoint
from app.models.user import User
from app.schemas.result import ResultRead, CountryResultRead

router = APIRouter()


@router.get("/{query_id}", response_model=ResultRead)
async def get_result(
    query_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Verify ownership
    q_result = await db.execute(
        select(QueryModel).where(
            QueryModel.id == query_id,
            QueryModel.user_id == current_user.id,
        )
    )
    query = q_result.scalar_one_or_none()
    if not query:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Query not found")

    r_result = await db.execute(
        select(Result)
        .where(Result.query_id == query_id)
        .options(selectinload(Result.data_points))
    )
    result = r_result.scalar_one_or_none()
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Result not ready yet")

    return result


@router.get("/{query_id}/geojson")
async def get_geojson(
    query_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    q_result = await db.execute(
        select(QueryModel).where(
            QueryModel.id == query_id,
            QueryModel.user_id == current_user.id,
        )
    )
    if not q_result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Query not found")

    r_result = await db.execute(
        select(Result).where(Result.query_id == query_id)
    )
    result = r_result.scalar_one_or_none()
    if not result or not result.geojson:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="GeoJSON not available")

    return result.geojson


@router.get("/{query_id}/timeline")
async def get_timeline(
    query_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    q_result = await db.execute(
        select(QueryModel).where(
            QueryModel.id == query_id,
            QueryModel.user_id == current_user.id,
        )
    )
    if not q_result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Query not found")

    dp_result = await db.execute(
        select(DataPoint)
        .join(Result)
        .where(Result.query_id == query_id)
        .order_by(DataPoint.timestamp)
    )
    data_points = dp_result.scalars().all()

    # Group by timestamp
    timeline: dict = {}
    for dp in data_points:
        year = dp.timestamp[:4]
        if year not in timeline:
            timeline[year] = []
        timeline[year].append({
            "country_code": dp.country_code,
            "entity_name": dp.entity_name,
            "field_name": dp.field_name,
            "field_value": dp.field_value,
            "is_null": dp.is_null,
        })

    return {"years": sorted(timeline.keys()), "data": timeline}


@router.get("/{query_id}/country/{country_code}", response_model=CountryResultRead)
async def get_country_result(
    query_id: uuid.UUID,
    country_code: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    q_result = await db.execute(
        select(QueryModel).where(
            QueryModel.id == query_id,
            QueryModel.user_id == current_user.id,
        )
    )
    if not q_result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Query not found")

    dp_result = await db.execute(
        select(DataPoint)
        .join(Result)
        .where(
            Result.query_id == query_id,
            DataPoint.country_code == country_code.upper(),
        )
        .order_by(DataPoint.field_name, DataPoint.timestamp)
    )
    data_points = dp_result.scalars().all()

    if not data_points:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No data for country {country_code}",
        )

    # Build sparkline data per field
    sparklines: dict = {}
    for dp in data_points:
        if dp.field_name not in sparklines:
            sparklines[dp.field_name] = {"years": [], "values": []}
        if not dp.is_null:
            sparklines[dp.field_name]["years"].append(dp.timestamp[:4])
            sparklines[dp.field_name]["values"].append(dp.field_value)

    return CountryResultRead(
        country_code=country_code.upper(),
        entity_name=data_points[0].entity_name,
        data_points=data_points,
        sparklines=sparklines,
    )
