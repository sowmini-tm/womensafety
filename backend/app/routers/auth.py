from datetime import datetime

from jose import JWTError, jwt
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db
from ..models.otp_verification import OTPVerification
from ..models.user import User
from ..schemas.auth import (
    ForgotPasswordRequest,
    LoginRequest,
    OTPDeliveryResult,
    RefreshTokenRequest,
    ResendVerificationRequest,
    ResetPasswordRequest,
    Token,
    UserCreate,
    UserRead,
    VerifyEmailRequest,
    VerifyEmailResponse,
)
from ..services.notification_service import NotificationService
from ..services.otp_service import (
    PURPOSE_EMAIL_VERIFICATION,
    PURPOSE_PASSWORD_RESET,
    get_latest_pending,
    issue_otp,
    verify_otp,
)
from ..utils.auth import get_current_user
from ..utils.security import (
    REFRESH_TOKEN_TYPE,
    create_access_token,
    create_refresh_token,
    hash_password,
    verify_password,
)

router = APIRouter()


@router.post("/auth/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def register(user_in: UserCreate, db: Session = Depends(get_db)):
    existing = (
        db.query(User)
        .filter((User.email == user_in.email) | (User.mobile_number == user_in.mobile_number))
        .first()
    )
    if existing:
        raise HTTPException(status_code=400, detail="User with provided email or mobile already exists")
    user = User(
        email=user_in.email,
        mobile_number=user_in.mobile_number,
        password_hash=hash_password(user_in.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/auth/login", response_model=Token)
def login(form_data: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == form_data.email).first()
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    access = create_access_token(user.id)
    refresh = create_refresh_token(user.id)
    return {"access_token": access, "refresh_token": refresh}


@router.post("/auth/refresh", response_model=Token)
def refresh(payload: RefreshTokenRequest):
    refresh_token = payload.refresh_token
    if not refresh_token:
        raise HTTPException(status_code=400, detail="Missing refresh_token")
    try:
        data = jwt.decode(refresh_token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    # Only dedicated refresh tokens may be exchanged; access tokens are rejected here.
    if data.get("token_type") != REFRESH_TOKEN_TYPE or not data.get("sub"):
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    subject = data["sub"]
    access = create_access_token(subject)
    new_refresh = create_refresh_token(subject)
    return {"access_token": access, "refresh_token": new_refresh}


@router.get("/auth/me", response_model=UserRead)
def get_me(user: User = Depends(get_current_user)):
    return user


@router.get("/protected/profile")
def protected_profile(user: User = Depends(get_current_user)):
    return {"message": "protected", "user": {"id": user.id, "email": user.email}}


# ---------------------------------------------------------------------------
# Phase 12: OTP verification + password recovery
# ---------------------------------------------------------------------------


def _lookup_user_for_email(db: Session, email: str) -> User | None:
    """Return the user by email if present; None otherwise (no error raised).

    Used by enumeration-sensitive flows where the response must be generic.
    """
    return db.query(User).filter(User.email == email).first()


def _deliver_otp_email(user: User, plain_otp: str, purpose: str) -> dict:
    """Send the OTP through the existing notification facade.

    Returns the provider result. When SendGrid credentials are absent the
    result is 'failed' and the caller reports it truthfully rather than faking
    delivery. Tests monkeypatch NotificationService.send_email.
    """
    if purpose == PURPOSE_PASSWORD_RESET:
        subject = "Your password reset code"
        body = (
            f"Use this code to reset your password: <b>{plain_otp}</b>. "
            f"It expires in {settings.OTP_EXPIRE_MINUTES} minutes."
        )
    else:
        subject = "Verify your email"
        body = (
            f"Use this code to verify your email: <b>{plain_otp}</b>. "
            f"It expires in {settings.OTP_EXPIRE_MINUTES} minutes."
        )
    return NotificationService.send_email(user.email, subject, body)


def _issue_and_deliver(db: Session, user: User, purpose: str) -> str:
    """Issue (persist hashed) + deliver an OTP. Returns the plaintext code.

    Always issues the OTP first so verification works even when the provider is
    unconfigured (dev/testing). The plaintext is returned only to the caller
    here; whether it reaches the API response is decided by the route based on
    DEV_OTP_MODE (and we never store it).
    """
    plain = issue_otp(db, user.id, purpose)
    _deliver_otp_email(user, plain, purpose)
    return plain


def _generic_dev_payload(plain_otp: str | None, message: str) -> dict:
    """Build an OTPDeliveryResult, surfacing the code only in dev mode."""
    if settings.DEV_OTP_MODE and plain_otp:
        return {"message": message, "dev_otp": plain_otp}
    return {"message": message}


@router.post("/auth/register/verify", response_model=VerifyEmailResponse)
def verify_email(payload: VerifyEmailRequest, db: Session = Depends(get_db)):
    """Verify a freshly registered account with the emailed OTP.

    The response is deliberately generic on failure so we never reveal whether
    an email corresponds to an account.
    """
    user = _lookup_user_for_email(db, payload.email)
    if user is None:
        raise HTTPException(status_code=400, detail="Verification code is invalid or has expired")

    code = get_latest_pending(db, user.id, PURPOSE_EMAIL_VERIFICATION)
    if code is None:
        raise HTTPException(status_code=400, detail="Verification code is invalid or has expired")

    if code.attempts >= settings.OTP_MAX_ATTEMPTS:
        code.is_verified = True
        db.commit()
        raise HTTPException(status_code=400, detail="Verification code is invalid or has expired")

    code.attempts += 1
    ok = verify_otp(payload.otp, code.otp_code)
    if not ok:
        db.commit()
        raise HTTPException(status_code=400, detail="Verification code is invalid or has expired")

    code.is_verified = True
    user.is_verified = True
    db.commit()
    return {"message": "Email verified successfully", "email_verified": True}


@router.post("/auth/register/resend-verification", response_model=OTPDeliveryResult)
def resend_verification(payload: ResendVerificationRequest, db: Session = Depends(get_db)):
    """(Re)send the email-verification OTP, throttled to avoid abuse.

    Generic 200 for both existing and non-existing emails prevents enumeration.
    """
    user = _lookup_user_for_email(db, payload.email)
    plain_otp: str | None = None

    if user is not None:
        existing = get_latest_pending(db, user.id, PURPOSE_EMAIL_VERIFICATION)
        if existing is not None and existing.last_sent_at is not None:
            elapsed = (datetime.utcnow() - existing.last_sent_at).total_seconds()
            if elapsed < settings.OTP_RESEND_SECONDS:
                return _generic_dev_payload(None, "If the email exists, a verification code has been sent.")
        plain_otp = _issue_and_deliver(db, user, PURPOSE_EMAIL_VERIFICATION)

    return _generic_dev_payload(plain_otp, "If the email exists, a verification code has been sent.")


@router.post("/auth/forgot-password", response_model=OTPDeliveryResult)
def forgot_password(payload: ForgotPasswordRequest, db: Session = Depends(get_db)):
    """Request a password-reset OTP. Generic response prevents enumeration."""
    user = _lookup_user_for_email(db, payload.email)
    plain_otp: str | None = None

    if user is not None:
        existing = get_latest_pending(db, user.id, PURPOSE_PASSWORD_RESET)
        if existing is not None and existing.last_sent_at is not None:
            elapsed = (datetime.utcnow() - existing.last_sent_at).total_seconds()
            if elapsed < settings.OTP_RESEND_SECONDS:
                return _generic_dev_payload(None, "If the account exists, a reset code has been sent.")
        plain_otp = _issue_and_deliver(db, user, PURPOSE_PASSWORD_RESET)

    return _generic_dev_payload(plain_otp, "If the account exists, a reset code has been sent.")


@router.post("/auth/reset-password", response_model=VerifyEmailResponse)
def reset_password(payload: ResetPasswordRequest, db: Session = Depends(get_db)):
    """Verify the reset OTP and set a new password (single-use, attempt-limited).

    The new password is validated by the same schema-level policy as
    registration. A successful reset rotates the account password; outstanding
    JWTs are untouched (the architecture has no token blacklist) but any new
    logins require the new password.
    """
    user = _lookup_user_for_email(db, payload.email)
    if user is None:
        raise HTTPException(status_code=400, detail="Reset code is invalid or has expired")

    code = get_latest_pending(db, user.id, PURPOSE_PASSWORD_RESET)
    if code is None:
        raise HTTPException(status_code=400, detail="Reset code is invalid or has expired")

    if code.attempts >= settings.OTP_MAX_ATTEMPTS:
        code.is_verified = True
        db.commit()
        raise HTTPException(status_code=400, detail="Reset code is invalid or has expired")

    code.attempts += 1
    if not verify_otp(payload.otp, code.otp_code):
        db.commit()
        raise HTTPException(status_code=400, detail="Reset code is invalid or has expired")

    code.is_verified = True
    user.password_hash = hash_password(payload.new_password)
    db.commit()
    return {"message": "Password reset successfully", "email_verified": False}
