from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Enum as SQLEnum, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from .user import User


class FakeCallStatus(str, Enum):
    SCHEDULED = "SCHEDULED"
    TRIGGERED = "TRIGGERED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class FakeCall(Base):
    __tablename__ = "fake_calls"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    caller_name: Mapped[str] = mapped_column(String(255), nullable=False)
    caller_number: Mapped[str] = mapped_column(String(32), nullable=False)
    delay_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    ringtone: Mapped[str] = mapped_column(String(255), nullable=True)
    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, index=True)
    status: Mapped[FakeCallStatus] = mapped_column(SQLEnum(FakeCallStatus), nullable=False, default=FakeCallStatus.SCHEDULED)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    user: Mapped["User"] = relationship("User", back_populates="fake_calls")
