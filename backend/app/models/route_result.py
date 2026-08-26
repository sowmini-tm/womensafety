from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum as SQLEnum, Float, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from .route_request import RouteRequest


class RouteType(str, Enum):
    RECOMMENDED = "RECOMMENDED"
    ALTERNATIVE = "ALTERNATIVE"


class RouteResult(Base):
    __tablename__ = "route_results"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    route_request_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("route_requests.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    route_type: Mapped[RouteType] = mapped_column(SQLEnum(RouteType), nullable=False, index=True)
    distance: Mapped[float] = mapped_column(Float(10, 2), nullable=False)
    estimated_duration: Mapped[float] = mapped_column(Float(10, 2), nullable=False)
    risk_score: Mapped[int] = mapped_column(Integer, nullable=False)
    route_data: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    route_request: Mapped["RouteRequest"] = relationship("RouteRequest", back_populates="results")
