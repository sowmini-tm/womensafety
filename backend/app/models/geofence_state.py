from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class GeofenceState(Base):
    """Persistent inside/outside state per (user, geofence) pair.

    One row per user+geofence so entry/exit detection fires only on real
    transitions instead of on every location update. ``last_seen_inside`` is
    NULL until the first location for that pair is evaluated, which makes the
    first observation deterministic and transition-free.
    """

    __tablename__ = "geofence_states"
    __table_args__ = (
        UniqueConstraint("user_id", "geofence_id", name="uq_geofence_states_user_geofence"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    geofence_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("geofences.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    last_seen_inside: Mapped[bool] = mapped_column(Boolean, nullable=True)
    last_distance_meters: Mapped[float] = mapped_column(Float, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )
