from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import datetime
from typing import Optional, Union

from sqlalchemy import Boolean, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


def generate_share_token() -> str:
    """Cryptographically secure random share token.

    32 bytes from the OS CSPRNG, hex-encoded to 64 chars. Withholding the token
    from the database (only its SHA-256 hash is stored) makes the raw value a
    bearer secret that is unguessable and unrecoverable if the DB leaks.
    """
    return secrets.token_hex(32)


def hash_share_token(raw_token: str) -> str:
    """Stable SHA-256 hex digest of a share token for at-rest storage/lookup."""
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


class LocationShareSession(Base):
    """An explicit live-location sharing session owned by one user.

    Only ONE active session per owner exists: starting a new session while an
    old one is still active deactivates it first. The share token handed to
    emergency contacts is never stored in plaintext — ``share_token_hash`` holds
    its SHA-256 digest so a database leak cannot reveal valid tokens.
    """

    __tablename__ = "location_share_sessions"
    __table_args__ = (
        UniqueConstraint("user_id", "is_active", name="uq_location_share_sessions_active_owner"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    share_token_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    stopped_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    user = relationship("User")