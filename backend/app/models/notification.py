from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum as SQLEnum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from .sos_incident import SOSIncident
    from .user import User


class NotificationType(str, Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    ALERT = "ALERT"


class NotificationStatus(str, Enum):
    PENDING = "PENDING"
    SENT = "SENT"
    FAILED = "FAILED"


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    sos_incident_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("sos_incidents.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    type: Mapped[NotificationType] = mapped_column(SQLEnum(NotificationType), nullable=False, index=True)
    recipient: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[NotificationStatus] = mapped_column(SQLEnum(NotificationStatus), nullable=False, default=NotificationStatus.PENDING, index=True)
    sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    user: Mapped["User"] = relationship("User", back_populates="notifications")
    sos_incident: Mapped["SOSIncident"] = relationship("SOSIncident", back_populates="notifications")
