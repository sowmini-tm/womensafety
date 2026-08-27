"""Phase 13 tests: production security & reliability hardening."""
import uuid

from fastapi.testclient import TestClient

from app.main import app
from app.middleware import _rate_buckets
from conftest import TestingSessionLocal

client = TestClient(app)


def _register_token(prefix: str = "hard") -> str:
    suffix = uuid.uuid4()
    email = f"{prefix}-{suffix}@example.com"
    mobile = f"+1{uuid.uuid4().int % 900000000 + 1000000000}"
    r = client.post(
        "/api/auth/register",
        json={"email": email, "mobile_number": mobile, "password": "StrongPass123!"},
    )
    assert r.status_code == 201, r.text
    login = client.post("/api/auth/login", json={"email": email, "password": "StrongPass123!"})
    assert login.status_code == 200, login.text
    return login.json()["access_token"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# --- security headers ---------------------------------------------------------

def test_security_headers_present():
    token = _register_token()
    resp = client.get("/api/auth/me", headers=_auth(token))
    assert resp.status_code == 200
    assert resp.headers.get("x-content-type-options") == "nosniff"
    assert resp.headers.get("x-frame-options") == "DENY"
    assert resp.headers.get("referrer-policy") == "no-referrer"
    assert resp.headers.get("cache-control") == "no-store"


# --- request body size cap ----------------------------------------------------

def test_oversized_request_body_rejected():
    # Only the Content-Length matters here; a GET with a huge header value is enough.
    resp = client.get("/api/safety/helplines", headers={"Content-Length": "99999999"})
    assert resp.status_code == 413


# --- input validation ----------------------------------------------------------

def test_location_rejects_impossible_coordinates():
    token = _register_token()
    for bad in ({"latitude": 999.0, "longitude": 0.0}, {"latitude": 0.0, "longitude": -181.0}):
        resp = client.post("/api/safety/location", headers=_auth(token), json=bad)
        assert resp.status_code == 422, resp.text


def test_location_accepts_valid_extreme_coordinates():
    token = _register_token()
    # Antarctica + dateline — genuine GPS values must still be accepted.
    resp = client.post(
        "/api/safety/location",
        headers=_auth(token),
        json={"latitude": -89.9999, "longitude": 179.9999, "accuracy": 5.0, "speed": 0.0},
    )
    assert resp.status_code == 201, resp.text


def test_geofence_rejects_negative_or_huge_radius():
    token = _register_token()
    for radius in (-5, 0, 10_000_000):
        resp = client.post(
            "/api/safety/geofences",
            headers=_auth(token),
            json={"name": "X", "latitude": 12.0, "longitude": 77.0, "radius": radius},
        )
        assert resp.status_code == 422, resp.text


def test_geofence_rejects_out_of_range_coordinates():
    token = _register_token()
    resp = client.post(
        "/api/safety/geofences",
        headers=_auth(token),
        json={"name": "X", "latitude": 91.0, "longitude": 77.0, "radius": 250},
    )
    assert resp.status_code == 422


# --- location history limit ----------------------------------------------------

def _post_locations(token: str, count: int):
    for i in range(count):
        r = client.post(
            "/api/safety/location",
            headers=_auth(token),
            json={"latitude": 12.0 + i / 1000.0, "longitude": 77.0 + i / 1000.0},
        )
        assert r.status_code == 201, r.text


def test_location_history_default_limit_and_custom_limit():
    token = _register_token()
    _post_locations(token, 250)

    # Default returns at most 200.
    default = client.get("/api/safety/location", headers=_auth(token))
    assert default.status_code == 200
    assert len(default.json()) == 200

    # Explicit limit up to 1000.
    custom = client.get("/api/safety/location", headers=_auth(token), params={"limit": 300})
    assert len(custom.json()) == 250  # only 250 exist

    # limit is clamped to 1000 and must be >= 1.
    too_many = client.get("/api/safety/location", headers=_auth(token), params={"limit": 5000})
    assert too_many.status_code == 422
    negative = client.get("/api/safety/location", headers=_auth(token), params={"limit": 0})
    assert negative.status_code == 422


def test_location_history_is_owner_scoped():
    token_a = _register_token("owna")
    token_b = _register_token("ownb")
    _post_locations(token_a, 5)

    # B sees none of A's history.
    resp = client.get("/api/safety/location", headers=_auth(token_b))
    assert resp.status_code == 200
    assert resp.json() == []


# --- rate limiting (opt-in, production-gated) -----------------------------------

def test_rate_limiting_returns_429_when_enabled(monkeypatch):
    from app import config

    monkeypatch.setattr(config.settings, "ENABLE_RATE_LIMITING", True)
    _rate_buckets.clear()
    try:
        # max auth limit is 10 per 60s window; the 11th login request is rejected.
        responses = []
        for _ in range(11):
            r = client.post(
                "/api/auth/login",
                json={"email": f"nobody-{uuid.uuid4()}@example.com", "password": "wrong"},
            )
            responses.append(r.status_code)
        assert 429 in responses
        assert responses[-1] == 429
    finally:
        monkeypatch.undo()
        _rate_buckets.clear()
        monkeypatch.setattr(config.settings, "ENABLE_RATE_LIMITING", False)


def test_non_sensitive_endpoint_not_rate_limited(monkeypatch):
    from app import config

    monkeypatch.setattr(config.settings, "ENABLE_RATE_LIMITING", True)
    _rate_buckets.clear()
    try:
        for _ in range(30):
            r = client.get("/api/safety/helplines")
            assert r.status_code == 200
    finally:
        monkeypatch.undo()
        _rate_buckets.clear()
        monkeypatch.setattr(config.settings, "ENABLE_RATE_LIMITING", False)
