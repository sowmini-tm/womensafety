"""Phase 10 tests: secure emergency-contact live-location sharing sessions."""
import uuid

from fastapi.testclient import TestClient

from app.main import app
from app.models.location_share_session import LocationShareSession
from conftest import TestingSessionLocal

client = TestClient(app)


def _create_token(prefix: str = "share") -> str:
    suffix = uuid.uuid4()
    email = f"{prefix}-{suffix}@example.com"
    register = client.post(
        "/api/auth/register",
        json={
            "email": email,
            "mobile_number": f"+{suffix.int % 9000000000 + 1000000000}",
            "password": "StrongPass123!",
        },
    )
    assert register.status_code == 201, register.text
    login = client.post("/api/auth/login", json={"email": email, "password": "StrongPass123!"})
    assert login.status_code == 200, login.text
    return login.json()["access_token"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _start_sharing(token: str):
    resp = client.post("/api/safety/location-sharing/start", json={}, headers=_auth(token))
    assert resp.status_code == 200, resp.text
    return resp.json()


def _post_location(token: str, latitude=12.9716, longitude=77.5946, accuracy=8.5, speed=1.2):
    return client.post(
        "/api/safety/location",
        headers=_auth(token),
        json={"latitude": latitude, "longitude": longitude, "accuracy": accuracy, "speed": speed},
    )


# --- start / persist / token security ---------------------------------------


def test_owner_can_start_sharing_and_get_secure_token():
    token = _create_token()
    body = _start_sharing(token)

    assert body["is_active"] is True
    assert body["share_token"], "starting a session must return a share token"
    # tokens never look like sequential IDs and are hex in this implementation
    assert len(body["share_token"]) == 64
    assert all(c in "0123456789abcdef" for c in body["share_token"])
    assert body["started_at"] is not None


def test_active_session_is_persisted_with_hashed_token():
    token = _create_token()
    body = _start_sharing(token)

    db = TestingSessionLocal()
    try:
        rows = db.query(LocationShareSession).filter(LocationShareSession.user_id == body["user_id"]).all()
        assert len(rows) == 1
        row = rows[0]
        assert row.is_active is True
        # raw token is NOT stored at rest; only its SHA-256 hash is
        assert row.share_token_hash != body["share_token"]
        assert len(row.share_token_hash) == 64
    finally:
        db.close()


def test_start_requires_authentication():
    resp = client.post("/api/safety/location-sharing/start", json={})
    assert resp.status_code in (401, 403)


def test_owner_can_see_sharing_status():
    token = _create_token()
    started = _start_sharing(token)

    status = client.get("/api/safety/location-sharing/status", headers=_auth(token))
    assert status.status_code == 200, status.text
    data = status.json()
    assert data["id"] == started["id"]
    assert data["is_active"] is True
    # status response must not leak the raw share token
    assert "share_token" not in data


def test_status_404_before_any_session():
    token = _create_token()
    resp = client.get("/api/safety/location-sharing/status", headers=_auth(token))
    assert resp.status_code == 404


# --- stop / inactive --------------------------------------------------------


def test_owner_can_stop_sharing_and_session_becomes_inactive():
    token = _create_token()
    started = _start_sharing(token)

    stopped = client.post("/api/safety/location-sharing/stop", headers=_auth(token))
    assert stopped.status_code == 200, stopped.text
    assert stopped.json()["is_active"] is False
    assert stopped.json()["stopped_at"] is not None

    db = TestingSessionLocal()
    try:
        row = db.query(LocationShareSession).filter(LocationShareSession.id == started["id"]).first()
        assert row is not None and row.is_active is False
    finally:
        db.close()


def test_stop_without_active_session_is_404():
    token = _create_token()
    resp = client.post("/api/safety/location-sharing/stop", headers=_auth(token))
    assert resp.status_code == 404


def test_stopped_share_link_is_rejected():
    token = _create_token()
    body = _start_sharing(token)
    client.post("/api/safety/location-sharing/stop", headers=_auth(token))

    shared = client.get(f"/api/safety/shared-location/{body['share_token']}")
    assert shared.status_code == 404
    assert shared.json()["detail"] == "Shared location not available"


# --- contact-facing shared endpoint -----------------------------------------


def test_valid_active_token_returns_latest_owner_location():
    token = _create_token()
    _post_location(token, latitude=12.9716, longitude=77.5946)
    _post_location(token, latitude=13.0827, longitude=80.2707)  # newest point
    body = _start_sharing(token)

    shared = client.get(f"/api/safety/shared-location/{body['share_token']}")
    assert shared.status_code == 200, shared.text
    data = shared.json()
    assert data["latitude"] == 13.0827
    assert data["longitude"] == 80.2707
    assert data["session_status"] == "active"
    assert data["timestamp"] is not None


# --- minimum data exposure ----------------------------------------------------


def test_shared_endpoint_returns_minimum_fields_only():
    token = _create_token()
    _post_location(token, latitude=12.9716, longitude=77.5946, accuracy=8.5, speed=1.2)
    body = _start_sharing(token)

    data = client.get(f"/api/safety/shared-location/{body['share_token']}").json()

    allowed_keys = {"latitude", "longitude", "accuracy", "speed", "timestamp", "session_status"}
    assert set(data.keys()) <= allowed_keys
    assert allowed_keys.issubset(set(data.keys()))
    forbidden_fragments = ("user_id", "history", "profile", "medical", "contacts", "email")
    for fragment in forbidden_fragments:
        assert fragment not in data


def test_location_submitted_after_start_becomes_available_via_token():
    token = _create_token()
    body = _start_sharing(token)

    before = client.get(f"/api/safety/shared-location/{body['share_token']}")
    assert before.status_code == 404  # nothing recorded yet

    saved = _post_location(token, latitude=17.3850, longitude=78.4867, accuracy=6.0, speed=3.4)
    assert saved.status_code == 201, saved.text

    after = client.get(f"/api/safety/shared-location/{body['share_token']}")
    assert after.status_code == 200, after.text
    assert after.json()["latitude"] == 17.3850
    assert after.json()["accuracy"] == 6.0
    assert after.json()["speed"] == 3.4


def test_shared_endpoint_never_exposes_full_history_or_user_data():
    token = _create_token()
    _post_location(token, latitude=12.9716, longitude=77.5946)
    _post_location(token, latitude=13.3532, longitude=74.7921)
    _post_location(token, latitude=9.9312, longitude=76.2673)
    body = _start_sharing(token)

    data = client.get(f"/api/safety/shared-location/{body['share_token']}").json()

    # A single object with exactly one coordinate pair — never an array of points.
    assert isinstance(data, dict)
    coords = [value for key, value in data.items() if key in ("latitude", "longitude")]
    assert len(coords) == 2
    assert (data["latitude"], data["longitude"]) in ((12.9716, 77.5946), (13.3532, 74.7921), (9.9312, 76.2673))


def test_invalid_token_is_rejected():
    for bad in ("not-a-real-token", "0" * 64, "../etc/passwd"):
        resp = client.get(f"/api/safety/shared-location/{bad}")
        assert resp.status_code == 404


# --- ownership / multi-user safety -------------------------------------------


def test_another_authenticated_user_cannot_control_owners_session():
    owner_token = _create_token("owner")
    attacker_token = _create_token("attacker")

    started = _start_sharing(owner_token)
    assert client.post("/api/safety/location-sharing/stop", headers=_auth(attacker_token)).status_code == 404

    status_attacker = client.get("/api/safety/location-sharing/status", headers=_auth(attacker_token))
    assert status_attacker.status_code == 404  # attacker has no session of their own

    # Owner's session is untouched by any other user's calls.
    status = client.get("/api/safety/location-sharing/status", headers=_auth(owner_token))
    assert status.status_code == 200
    assert status.json()["id"] == started["id"]
    assert status.json()["is_active"] is True


def test_sessions_are_scoped_per_owner():
    token_a = _create_token("alpha")
    token_b = _create_token("beta")

    start_a = _start_sharing(token_a)
    start_b = _start_sharing(token_b)

    status_a = client.get("/api/safety/location-sharing/status", headers=_auth(token_a)).json()
    status_b = client.get("/api/safety/location-sharing/status", headers=_auth(token_b)).json()

    assert status_a["id"] == start_a["id"]
    assert status_b["id"] == start_b["id"]
    assert status_a["id"] != status_b["id"]

    # Stopping B must not deactivate A's session.
    client.post("/api/safety/location-sharing/stop", headers=_auth(token_b))
    assert client.get("/api/safety/location-sharing/status", headers=_auth(token_a)).json()["is_active"] is True
    assert client.get("/api/safety/location-sharing/status", headers=_auth(token_b)).json()["is_active"] is False


def test_second_session_deactivates_previous_one_and_invalidates_old_token():
    token = _create_token()
    _post_location(token, latitude=12.9716, longitude=77.5946)
    first = _start_sharing(token)
    second = _start_sharing(token)

    assert first["id"] != second["id"]

    db = TestingSessionLocal()
    try:
        rows = (
            db.query(LocationShareSession)
            .filter(LocationShareSession.user_id == second["user_id"])
            .order_by(LocationShareSession.created_at.asc())
            .all()
        )
        assert len(rows) == 2
        assert rows[0].is_active is False
        assert rows[0].stopped_at is not None
        assert rows[1].is_active is True
    finally:
        db.close()

    # The old token no longer resolves to a live session.
    old = client.get(f"/api/safety/shared-location/{first['share_token']}")
    assert old.status_code == 404
    new = client.get(f"/api/safety/shared-location/{second['share_token']}")
    assert new.status_code == 200


def test_starting_new_session_deactivates_old_even_if_never_stopped_explicitly():
    token = _create_token()
    _post_location(token, latitude=12.9716, longitude=77.5946)
    first = _start_sharing(token)

    status = client.get("/api/safety/location-sharing/status", headers=_auth(token)).json()
    assert status["is_active"] is True

    second = _start_sharing(token)
    stale = client.get(f"/api/safety/shared-location/{first['share_token']}")
    assert stale.status_code == 404
    fresh = client.get(f"/api/safety/shared-location/{second['share_token']}")
    assert fresh.status_code == 200

