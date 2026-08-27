"""Phase 12: cryptographically secure OTP generation, hashing, and lifecycle.

OTPs are treated like passwords: the plaintext value is generated from a CSPRNG,
returned to the caller exactly once (and only surfaced in the API when
DEV_OTP_MODE is enabled for local development/testing), and NEVER stored. Only a
SHA-256 hash of the OTP is persisted, so a database leak cannot reveal usable
codes. Codes are single-use, short-lived, attempt-limited, and resend-throttled.
"""

from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from ..config import settings
from ..models.otp_verification import OTPVerification

# Purposes recorded on the OTP row so a single model serves both flows.
PURPOSE_EMAIL_VERIFICATION = "email_verification"
PURPOSE_PASSWORD_RESET = "password_reset"


def generate_otp() -> str:
    """Cryptographically secure numeric OTP of the configured length."""
    length = max(1, settings.OTP_LENGTH)
    # Ensure the leading digit can be zero: sample digits individually.
    return "".join(secrets.choice("0123456789") for _ in range(length))


def hash_otp(plain_otp: str) -> str:
    """Stable SHA-256 hex digest of an OTP for at-rest storage and lookup."""
    return hashlib.sha256(plain_otp.encode("utf-8")).hexdigest()


def verify_otp(plain_otp: str, otp_hash: str) -> bool:
    """Constant-time-ish comparison of a submitted OTP against a stored hash."""
    digest = hash_otp(plain_otp)
    return secrets.compare_digest(digest, (otp_hash or "").lower())


def _deactivate_pending(db: Session, user_id: str, purpose: str) -> None:
    """Mark any outstanding (unverified) OTPs for this purpose as used so only
    the most recent issuance is ever valid (single active OTP per user+purpose)."""
    db.query(OTPVerification).filter(
        OTPVerification.user_id == user_id,
        OTPVerification.purpose == purpose,
        OTPVerification.is_verified.is_(False),
    ).update({"is_verified": True}, synchronize_session=False)


def issue_otp(db: Session, user_id: str, purpose: str) -> str:
    """Create a new OTP row and return the plaintext value (caller delivers it).

    Single-use semantics: previously issued unverified codes for the same
    user+purpose are invalidated so only one code works at a time.
    """
    plain = generate_otp()
    _deactivate_pending(db, user_id, purpose)
    expires_at = datetime.utcnow() + timedelta(minutes=settings.OTP_EXPIRE_MINUTES)
    row = OTPVerification(
        id=str(uuid.uuid4()),
        user_id=user_id,
        otp_code=hash_otp(plain),
        purpose=purpose,
        expires_at=expires_at,
        is_verified=False,
        attempts=0,
        last_sent_at=datetime.utcnow(),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return plain


def get_latest_pending(db: Session, user_id: str, purpose: str) -> OTPVerification | None:
    """Most recent unverified, unexpired OTP row for the user+purpose (if any)."""
    now = datetime.utcnow()
    return (
        db.query(OTPVerification)
        .filter(
            OTPVerification.user_id == user_id,
            OTPVerification.purpose == purpose,
            OTPVerification.is_verified.is_(False),
            OTPVerification.expires_at > now,
        )
        .order_by(OTPVerification.created_at.desc())
        .first()
    )
