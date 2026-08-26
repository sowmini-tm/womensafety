from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import List, TYPE_CHECKING

from sqlalchemy import DateTime, Enum as SQLEnum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from .user import User


class SOSStatus(str, Enum):
    ACTIVE = "ACTIVE"
    CANCELLED = "CANCELLED"
    RESOLVED = "RESOLVED"


class SOSIncident(Base):
    __tablename__ = "sos_incidents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    latitude: Mapped[float] = mapped_column(nullable=False)
    longitude: Mapped[float] = mapped_column(nullable=False)
    status: Mapped[SOSStatus] = mapped_column(SQLEnum(SOSStatus), nullable=False, default=SOSStatus.ACTIVE, index=True)
    activated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    cancelled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    user: Mapped["User"] = relationship("User", back_populates="sos_incidents")
    audio_recordings: Mapped[List["AudioRecording"]] = relationship(
        "AudioRecording",
        back_populates="sos_incident",
        cascade="all, delete-orphan",
    )
    video_recordings: Mapped[List["VideoRecording"]] = relationship(
        "VideoRecording",
        back_populates="sos_incident",
        cascade="all, delete-orphan",
    )
    notifications: Mapped[List["Notification"]] = relationship(
        "Notification",
        back_populates="sos_incident",
        cascade="all, delete-orphan",
    )
