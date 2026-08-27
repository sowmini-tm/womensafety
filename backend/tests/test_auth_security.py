"""Phase 5 tests: JWT token-type semantics, password policy, production secret guard."""
import uuid

import pytest
from fastapi.testclient import TestClient
from jose import jwt
from pydantic import ValidationError

from app.config import Settings, settings
from app.main import app

client = TestClient(app)


def _register_and_login() -> dict:
    suffix = uuid.uuid4().hex[:10]
    payload = {
        "email": f"sec-{suffix}@example.com",
        "mobile_number": f"+1{int(suffix, 16) % 900000000 + 1000000000}",
        "password": "StrongPass123!",
    }
    resp = client.post("/api/auth/register", json=payload)
    assert resp.status_code == 201, resp.text
    login = client.post("/api/auth/login", json={"email": payload["email"], "password": payload["password"]})
    assert login.status_code == 200, login.text
    return login.json()


def _decode(token: str) -> dict:
    return jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])


# ---------------------------------------------------------------------------
# 1. Token semantics: /auth/refresh accepts ONLY refresh tokens
# ---------------------------------------------------------------------------

class TestTokenSemantics:
    def test_tokens_carry_distinct_type_claims(self):
        tokens = _register_and_login()
        access_claims = _decode(tokens["access_token"])
        refresh_claims = _decode(tokens["refresh_token"])
        assert access_claims["token_type"] == "access"
        assert refresh_claims["token_type"] == "refresh"
        assert access_claims["sub"] == refresh_claims["sub"]

    def test_refresh_endpoint_rejects_access_token(self):
        tokens = _register_and_login()
        resp = client.post("/api/auth/refresh", json={"refresh_token": tokens["access_token"]})
        assert resp.status_code == 401, resp.text
        assert "Invalid refresh token" in resp.json()["detail"]

    def test_refresh_endpoint_accepts_real_refresh_token_and_rotates_pair(self):
        tokens = _register_and_login()
        resp = client.post("/api/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
        assert resp.status_code == 200, resp.text
        body = resp.json()

        # The new access token must authenticate against a protected route.
        me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {body['access_token']}"})
        assert me.status_code == 200, me.text

        # Rotation issues a correctly typed pair.
        assert _decode(body["access_token"])["token_type"] == "access"
        assert _decode(body["refresh_token"])["token_type"] == "refresh"

    def test_refresh_endpoint_rejects_garbage_token(self):
        resp = client.post("/api/auth/refresh", json={"refresh_token": "not-a-jwt"})
        assert resp.status_code == 401

    def test_refresh_token_rejected_as_access_credential(self):
        tokens = _register_and_login()
        me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {tokens['refresh_token']}"})
        assert me.status_code == 401

    def test_register_login_me_flow_still_works(self):
        tokens = _register_and_login()
        claims = _decode(tokens["access_token"])
        me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {tokens['access_token']}"})
        assert me.status_code == 200
        assert me.json()["id"] == claims["sub"]


# ---------------------------------------------------------------------------
# 2. Password policy on registration only (legacy logins must keep working)
# ---------------------------------------------------------------------------

class TestPasswordPolicy:
    def _register(self, password: str):
        suffix = uuid.uuid4().hex[:10]
        return client.post(
            "/api/auth/register",
            json={
                "email": f"pw-{suffix}@example.com",
                "mobile_number": f"+1{int(suffix, 16) % 900000000 + 1000000000}",
                "password": password,
            },
        )

    def test_rejects_too_short_password(self):
        resp = self._register("Ab1")
        assert resp.status_code == 422

    def test_rejects_letters_only_password(self):
        resp = self._register("abcdefghij")
        assert resp.status_code == 422

    def test_rejects_digits_only_password(self):
        resp = self._register("1234567890")
        assert resp.status_code == 422

    def test_accepts_meeting_policy_password(self):
        resp = self._register("StrongPass123!")
        assert resp.status_code == 201, resp.text

    def test_login_unaffected_by_policy_for_legacy_accounts(self):
        """Accounts created before the policy (weak password) can still sign in."""
        from app.models.user import User
        from app.utils.security import hash_password
        from conftest import TestingSessionLocal

        legacy_email = f"legacy-{uuid.uuid4().hex[:10]}@example.com"
        with TestingSessionLocal() as db:
            db.add(
                User(
                    email=legacy_email,
                    mobile_number=f"+1{uuid.uuid4().int % 900000000 + 1000000000}",
                    password_hash=hash_password("weakpass1"),
                )
            )
            db.commit()

        resp = client.post("/api/auth/login", json={"email": legacy_email, "password": "weakpass1"})
        assert resp.status_code == 200, resp.text


# ---------------------------------------------------------------------------
# 3. Production configuration refuses insecure JWT secret
# ---------------------------------------------------------------------------

class TestProductionSecretGuard:
    @staticmethod
    def _build_settings(monkeypatch, **overrides) -> Settings:
        # Keep both real-env and .env-file values from leaking into this build.
        for key in ("JWT_SECRET_KEY", "ENVIRONMENT", "DATABASE_URL"):
            monkeypatch.delenv(key, raising=False)
        kwargs = {"DATABASE_URL": "sqlite:///./guard-test.db"}
        kwargs.update(overrides)
        return Settings(_env_file=None, **kwargs)

    def test_production_rejects_insecure_default_secret(self, monkeypatch):
        with pytest.raises(ValidationError, match="JWT_SECRET_KEY"):
            self._build_settings(monkeypatch, ENVIRONMENT="production", JWT_SECRET_KEY="change_this")

    def test_production_rejects_short_secret(self, monkeypatch):
        with pytest.raises(ValidationError, match="JWT_SECRET_KEY"):
            self._build_settings(monkeypatch, ENVIRONMENT="production", JWT_SECRET_KEY="too-short")

    def test_production_accepts_strong_secret(self, monkeypatch):
        strong = "a" * 48
        built = self._build_settings(
            monkeypatch, ENVIRONMENT="production", JWT_SECRET_KEY=strong, DEV_OTP_MODE=False
        )
        assert built.JWT_SECRET_KEY == strong
        assert built.ENVIRONMENT == "production"

    def test_production_rejects_dev_otp_mode(self, monkeypatch):
        with pytest.raises(ValidationError, match="DEV_OTP_MODE"):
            self._build_settings(
                monkeypatch, ENVIRONMENT="production", JWT_SECRET_KEY="a" * 48, DEV_OTP_MODE=True
            )

    def test_development_still_allows_default_secret(self, monkeypatch):
        built = self._build_settings(monkeypatch)
        assert built.ENVIRONMENT == "development"
        assert built.JWT_SECRET_KEY == "change_this"
