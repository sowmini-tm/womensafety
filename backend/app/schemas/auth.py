from __future__ import annotations

import re
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, field_validator


class UserCreate(BaseModel):
    email: EmailStr
    mobile_number: str
    password: str

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, value: str) -> str:
        """Minimal registration policy; deliberately NOT applied on login so
        accounts created before this rule can still sign in."""
        if (
            len(value) < 8
            or not re.search(r"[A-Za-z]", value)
            or not re.search(r"\d", value)
        ):
            raise ValueError(
                "Password must be at least 8 characters long and contain both letters and numbers"
            )
        return value


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    email: EmailStr
    mobile_number: str
    is_active: bool


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    sub: str
    exp: Optional[int]


# --- Phase 12: OTP verification / password recovery -------------------------


class VerifyEmailRequest(BaseModel):
    email: EmailStr
    otp: str


class ResendVerificationRequest(BaseModel):
    email: EmailStr


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    email: EmailStr
    otp: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def validate_new_password_strength(cls, value: str) -> str:
        if (
            len(value) < 8
            or not re.search(r"[A-Za-z]", value)
            or not re.search(r"\d", value)
        ):
            raise ValueError(
                "Password must be at least 8 characters long and contain both letters and numbers"
            )
        return value


class OTPDeliveryResult(BaseModel):
    """Generic, enumeration-safe response for OTP issuance endpoints."""

    message: str
    # Exposed ONLY when DEV_OTP_MODE is true; never present in production.
    dev_otp: Optional[str] = None


class VerifyEmailResponse(BaseModel):
    message: str
    email_verified: bool
