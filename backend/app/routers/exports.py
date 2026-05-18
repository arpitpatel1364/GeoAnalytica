import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.dependencies import get_current_user
from app.models.export import Export
from app.models.query import Query as QueryModel
from app.models.result import Result
from app.models.user import User
from app.schemas.export import ExportCreate, ExportRead
from app.services.export_service import ExportService

router = APIRouter()

MIME_TYPES = {
    "csv": "text/csv",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "pdf": "application/pdf",
    "json": "application/json",
}

SCHEDULE_INTERVALS = {
    "daily": timedelta(days=1),
    "weekly": timedelta(weeks=1),
    "monthly": timedelta(days=30),
}


@router.get("/{query_id}/{format}")
async def download_export(
    query_id: uuid.UUID,
    format: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if format not in MIME_TYPES:
        raise HTTPException(status_code=400, detail=f"Unsupported format: {format}")

    q_result = await db.execute(
        select(QueryModel).where(
            QueryModel.id == query_id,
            QueryModel.user_id == current_user.id,
        )
    )
    query = q_result.scalar_one_or_none()
    if not query:
        raise HTTPException(status_code=404, detail="Query not found")

    r_result = await db.execute(
        select(Result)
        .where(Result.query_id == query_id)
        .options(selectinload(Result.data_points))
    )
    result = r_result.scalar_one_or_none()
    if not result:
        raise HTTPException(status_code=404, detail="Result not available")

    service = ExportService()

    if format == "csv":
        data = service.generate_csv(result)
    elif format == "xlsx":
        data = service.generate_xlsx(result, query)
    elif format == "pdf":
        data = service.generate_pdf(result, query)
    elif format == "json":
        data = service.generate_json(result)
    else:
        raise HTTPException(status_code=400, detail="Unsupported format")

    filename = f"geoanalytica_{str(query_id)[:8]}_{format}"
    return Response(
        content=data,
        media_type=MIME_TYPES[format],
        headers={"Content-Disposition": f'attachment; filename="{filename}.{format}"'},
    )


@router.post("/schedule", response_model=ExportRead, status_code=status.HTTP_201_CREATED)
async def schedule_export(
    data: ExportCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if data.is_scheduled and not data.schedule_frequency:
        raise HTTPException(status_code=400, detail="schedule_frequency required for scheduled exports")

    now = datetime.now(timezone.utc)
    next_run = None
    if data.is_scheduled and data.schedule_frequency:
        interval = SCHEDULE_INTERVALS.get(data.schedule_frequency, timedelta(days=1))
        next_run = now + interval

    export = Export(
        user_id=current_user.id,
        query_id=data.query_id,
        format=data.format,
        is_scheduled=data.is_scheduled,
        schedule_frequency=data.schedule_frequency,
        schedule_email=str(data.schedule_email) if data.schedule_email else None,
        next_run_at=next_run,
    )
    db.add(export)
    await db.commit()
    await db.refresh(export)
    return export
