import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user, check_query_limit
from app.models.project import Project
from app.models.query import Query as QueryModel
from app.models.user import User
from app.schemas.query import QueryCreate, QueryRead, QueryHistoryItem
from app.workers.tasks import run_query_task

router = APIRouter()


@router.post("", response_model=QueryRead, status_code=status.HTTP_201_CREATED)
async def create_query(
    data: QueryCreate,
    current_user: User = Depends(check_query_limit),
    db: AsyncSession = Depends(get_db),
):
    # Verify project belongs to user
    proj_result = await db.execute(
        select(Project).where(
            Project.id == data.project_id,
            Project.user_id == current_user.id,
        )
    )
    project = proj_result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    query = QueryModel(
        project_id=data.project_id,
        user_id=current_user.id,
        instruction_text=data.instruction_text,
        mode=data.mode,
        status="pending",
    )
    db.add(query)

    # Increment project query count
    project.query_count += 1

    await db.commit()
    await db.refresh(query)

    # Dispatch async Celery task
    run_query_task.apply_async(
        args=[str(query.id)],
        queue="queries",
        countdown=0,
    )

    return query


@router.get("/history", response_model=List[QueryHistoryItem])
async def get_query_history(
    project_id: Optional[uuid.UUID] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(QueryModel).where(QueryModel.user_id == current_user.id)
    if project_id:
        stmt = stmt.where(QueryModel.project_id == project_id)
    stmt = stmt.order_by(QueryModel.created_at.desc()).limit(100)

    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/{query_id}", response_model=QueryRead)
async def get_query(
    query_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(QueryModel).where(
            QueryModel.id == query_id,
            QueryModel.user_id == current_user.id,
        )
    )
    query = result.scalar_one_or_none()
    if not query:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Query not found")
    return query


@router.post("/{query_id}/rerun", response_model=QueryRead, status_code=status.HTTP_201_CREATED)
async def rerun_query(
    query_id: uuid.UUID,
    current_user: User = Depends(check_query_limit),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(QueryModel).where(
            QueryModel.id == query_id,
            QueryModel.user_id == current_user.id,
        )
    )
    original = result.scalar_one_or_none()
    if not original:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Query not found")

    new_query = QueryModel(
        project_id=original.project_id,
        user_id=current_user.id,
        instruction_text=original.instruction_text,
        mode=original.mode,
        status="pending",
    )
    db.add(new_query)

    # Keep project query_count and last_query_at in sync
    proj_result = await db.execute(
        select(Project).where(Project.id == original.project_id)
    )
    project = proj_result.scalar_one_or_none()
    if project:
        project.query_count += 1

    await db.commit()
    await db.refresh(new_query)

    run_query_task.apply_async(
        args=[str(new_query.id)],
        queue="queries",
    )
    return new_query


@router.delete("/{query_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_query(
    query_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(QueryModel).where(
            QueryModel.id == query_id,
            QueryModel.user_id == current_user.id,
        )
    )
    query = result.scalar_one_or_none()
    if not query:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Query not found")
    await db.delete(query)
    await db.commit()
