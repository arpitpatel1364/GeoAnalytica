import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Result(Base):
    __tablename__ = "results"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    query_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("queries.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    summary_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    key_findings: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)
    anomalies: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)
    data_quality_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    stats_summary: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    correlation_matrix: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    entity_rankings: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)
    geojson: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    total_points: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    null_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    outlier_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    # Relationships
    query: Mapped["Query"] = relationship("Query", back_populates="result")  # noqa: F821
    data_points: Mapped[list["DataPoint"]] = relationship(
        "DataPoint", back_populates="result", cascade="all, delete-orphan",
        lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<Result {self.id} [{self.total_points} points]>"


class DataPoint(Base):
    __tablename__ = "data_points"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    result_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("results.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    entity_name: Mapped[str] = mapped_column(String(255), nullable=False)
    country_code: Mapped[Optional[str]] = mapped_column(String(10), nullable=True, index=True)
    latitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    longitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    field_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    field_value: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    timestamp: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    source_type: Mapped[str] = mapped_column(String(10), nullable=False, default="web")
    source_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    source_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    confidence_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    is_null: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_outlier: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    outlier_reason: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    conflicts: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)
    cluster_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Relationships
    result: Mapped["Result"] = relationship("Result", back_populates="data_points")

    def __repr__(self) -> str:
        return f"<DataPoint {self.entity_name} {self.field_name} {self.timestamp}>"
