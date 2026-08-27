"""Phase 12 tests: OTP verification + password recovery."""
import uuid

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services import notification_service
from conftest import TestingSessionLocal

client = TestClient(app)


@pytest.fixture(autouse=True)
def _mock_email(monkeypatch):
    """Never send real email; record delivered payloads for assertions."""
    captured = {}

    def fake_send_email(to_email, subject, body):
        captured["to"] = to_email
        captured["subject"] = subject
        captured["body"] = body
        return {"status": "sent", "provider": "sendgrid"}

    monkeypatch.setattr(notification_service.NotificationService, "send_email", staticmethod(fake_send_email))
    return captured


def _register(email=None, password="StrongPass123!"):
    suffix = uuid.uuid4().hex[:10]
    email = email or f"otp-{suffix}@example.com"
    mobile = f"+1{int(suffix, 16) % 900000000 + 1000000000}"
    resp = client.post(
        "/api/auth/register",
        json={"email": email, "mobile_number": mobile, "password": password},
    )
    assert resp.status_code == 201, resp.text
    return email


def _request_verification(email):
    resp = client.post("/api/auth/register/resend-verification", json={"email": email})
    assert resp.status_code == 200, resp.text
    assert resp.json().get("dev_otp"), "DEV_OTP_MODE should expose the code in tests"
    return resp.json()["dev_otp"]


# --- OTP generation / storage -------------------------------------------------

def test_otp_generation_is_secure_and_only_hash_stored():
    from app.models.otp_verification import OTPVerification
    from app.models.user import User

    email = _register()
    _request_verification(email)
    with TestingSessionLocal() as db:
        user = db.query(User).filter(User.email == email).first()
        pending = (
            db.query(OTPVerification)
            .filter(OTPVerification.user_id == user.id)
            .order_by(OTPVerification.created_at.desc())
            .first()
        )
        assert pending is not None
        # Plaintext OTP is never stored — only a SHA-256 hex hash (64 chars).
        assert len(pending.otp_code) == 64
        assert not pending.otp_code.isdigit()


# --- registration verification -------------------------------------------------

def test_successful_email_verification():
    email = _register()
    otp = _request_verification(email)
    resp = client.post("/api/auth/register/verify", json={"email": email, "otp": otp})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["email_verified"] is True

    with TestingSessionLocal() as db:
        from app.models.user import User

        user = db.query(User).filter(User.email == email).first()
        assert user.is_verified is True


def test_wrong_otp_rejected():
    email = _register()
    _request_verification(email)
    resp = client.post("/api/auth/register/verify", json={"email": email, "otp": "000000"})
    assert resp.status_code == 400


def test_otp_is_single_use():
    email = _register()
    otp = _request_verification(email)
    assert client.post("/api/auth/register/verify", json={"email": email, "otp": otp}).status_code == 200
    # Reusing the same (now-verified) code must fail.
    resp = client.post("/api/auth/register/verify", json={"email": email, "otp": otp})
    assert resp.status_code == 400


def test_expired_otp_rejected():
    import datetime
    from app.models.otp_verification import OTPVerification
    from app.models.user import User

    email = _register()
    otp = _request_verification(email)
    with TestingSessionLocal() as db:
        user = db.query(User).filter(User.email == email).first()
        row = (
            db.query(OTPVerification)
            .filter(OTPVerification.user_id == user.id)
            .order_by(OTPVerification.created_at.desc())
            .first()
        )
        # Expire the very OTP we captured, without issuing a new one.
        row.expires_at = datetime.datetime.utcnow() - datetime.timedelta(minutes=1)
        db.commit()

    resp = client.post("/api/auth/register/verify", json={"email": email, "otp": otp})
    assert resp.status_code == 400


def test_attempt_limit_locks_code():
    email = _register()
    otp = _request_verification(email)
    from app.config import settings

    for _ in range(settings.OTP_MAX_ATTEMPTS):
        resp = client.post("/api/auth/register/verify", json={"email": email, "otp": "999999"})
        assert resp.status_code == 400

    # Even the correct code is now rejected after exhausting attempts.
    locked = client.post("/api/auth/register/verify", json={"email": email, "otp": otp})
    assert locked.status_code == 400


def test_resend_is_throttled():
    email = _register()
    _request_verification(email)
    # Second immediate resend should be throttled: dev_otp absent, same generic message.
    resp = client.post("/api/auth/register/resend-verification", json={"email": email})
    assert resp.status_code == 200
    assert "dev_otp" not in resp.json() or resp.json().get("dev_otp") is None


def test_enumeration_safe_for_unknown_email():
    resp = client.post(
        "/api/auth/register/resend-verification",
        json={"email": f"nobody-{uuid.uuid4()}@example.com"},
    )
    assert resp.status_code == 200
    assert "dev_otp" not in resp.json() or resp.json().get("dev_otp") is None


# --- password reset -----------------------------------------------------------

def _request_reset(email):
    resp = client.post("/api/auth/forgot-password", json={"email": email})
    assert resp.status_code == 200, resp.text
    assert resp.json().get("dev_otp")
    return resp.json()["dev_otp"]


def test_password_reset_request_and_successful_reset():
    email = _register(password="OldPass123!")
    otp = _request_reset(email)

    resp = client.post(
        "/api/auth/reset-password",
        json={"email": email, "otp": otp, "new_password": "NewPass456!"},
    )
    assert resp.status_code == 200, resp.text

    # Old password no longer works; new one does.
    assert client.post("/api/auth/login", json={"email": email, "password": "OldPass123!"}).status_code == 401
    login = client.post("/api/auth/login", json={"email": email, "password": "NewPass456!"})
    assert login.status_code == 200


def test_reset_wrong_otp_rejected():
    email = _register()
    _request_reset(email)
    resp = client.post(
        "/api/auth/reset-password",
        json={"email": email, "otp": "000000", "new_password": "NewPass456!"},
    )
    assert resp.status_code == 400


def test_reset_otp_single_use():
    email = _register(password="OldPass123!")
    otp = _request_reset(email)
    assert client.post(
        "/api/auth/reset-password",
        json={"email": email, "otp": otp, "new_password": "NewPass456!"},
    ).status_code == 200
    second = client.post(
        "/api/auth/reset-password",
        json={"email": email, "otp": otp, "new_password": "AnotherPass789!"},
    )
    assert second.status_code == 400


def test_reset_applies_password_policy():
    email = _register()
    otp = _request_reset(email)
    resp = client.post(
        "/api/auth/reset-password",
        json={"email": email, "otp": otp, "new_password": "weak"},  # too short
    )
    assert resp.status_code == 422  # schema-level policy rejects weak password


def test_reset_enumeration_safe():
    # No such user: generic 200 with no code, never leaks existence.
    resp = client.post(
        "/api/auth/forgot-password",
        json={"email": f"ghost-{uuid.uuid4()}@example.com"},
    )
    assert resp.status_code == 200
    assert "dev_otp" not in resp.json() or resp.json().get("dev_otp") is None


def test_verify_unknown_email_enumeration_safe():
    resp = client.post(
        "/api/auth/register/verify",
        json={"email": f"ghost-{uuid.uuid4()}@example.com", "otp": "123456"},
    )
    assert resp.status_code == 400
    assert "Verification code is invalid or has expired" in resp.json()["detail"]


# --- regression: existing auth still works -------------------------------------

def test_login_regression_after_verification_flow():
    email = _register()
    # Even though this account is unverified, existing behaviour still allows login.
    login = client.post("/api/auth/login", json={"email": email, "password": "StrongPass123!"})
    assert login.status_code == 200
    assert "access_token" in login.json()


