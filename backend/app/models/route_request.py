from __future__ import annotations

import uuid
from datetime import datetime
from typing import List, TYPE_CHECKING

from sqlalchemy import DateTime, Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from .route_result import RouteResult
    from .user import User


class RouteRequest(Base):
    __tablename__ = "route_requests"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    start_latitude: Mapped[float] = mapped_column(Float(9, 6), nullable=False)
    start_longitude: Mapped[float] = mapped_column(Float(9, 6), nullable=False)
    destination_latitude: Mapped[float] = mapped_column(Float(9, 6), nullable=False)
    destination_longitude: Mapped[float] = mapped_column(Float(9, 6), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    user: Mapped["User"] = relationship("User", back_populates="route_requests")
    results: Mapped[List["RouteResult"]] = relationship(
        "RouteResult",
        back_populates="route_request",
        cascade="all, delete-orphan",
    )
