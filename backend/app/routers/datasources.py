import uuid
import os
from typing import List
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.dependencies import get_current_user
from app.models.datasource import Datasource
from app.models.user import User
from app.schemas.datasource import DatasourceRead

router = APIRouter()

# Use configurable upload dir; default to a directory in the project root
UPLOAD_DIR = os.environ.get("UPLOAD_DIR", str(Path(__file__).resolve().parent.parent.parent / "uploads"))
os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.get("", response_model=List[DatasourceRead])
async def list_datasources(
    project_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Datasource).where(
            Datasource.project_id == project_id,
            Datasource.user_id == current_user.id,
        )
    )
    return result.scalars().all()


@router.post("/upload", response_model=DatasourceRead, status_code=status.HTTP_201_CREATED)
async def upload_datasource(
    project_id: uuid.UUID = Form(...),
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    content = await file.read()
    file_path = os.path.join(UPLOAD_DIR, f"{uuid.uuid4()}_{file.filename}")

    with open(file_path, "wb") as f:
        f.write(content)

    ds = Datasource(
        project_id=project_id,
        user_id=current_user.id,
        name=file.filename or "upload",
        source_type="upload",
        file_path=file_path,
        file_size_bytes=len(content),
    )
    db.add(ds)
    await db.commit()
    await db.refresh(ds)
    return ds


@router.delete("/{datasource_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_datasource(
    datasource_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Datasource).where(
            Datasource.id == datasource_id,
            Datasource.user_id == current_user.id,
        )
    )
    ds = result.scalar_one_or_none()
    if not ds:
        raise HTTPException(status_code=404, detail="Datasource not found")
    if ds.file_path and os.path.exists(ds.file_path):
        os.remove(ds.file_path)
    await db.delete(ds)
    await db.commit()
