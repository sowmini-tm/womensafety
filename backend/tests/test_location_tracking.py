"""Phase 6 tests: real continuous location tracking endpoint behavior."""
import uuid

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _create_token() -> str:
    suffix = uuid.uuid4()
    register = client.post(
        "/api/auth/register",
        json={
            "email": f"track-{suffix}@example.com",
            "mobile_number": f"+{suffix.int % 9000000000 + 1000000000}",
            "password": "StrongPass123!",
        },
    )
    assert register.status_code == 201, register.text
    login = client.post("/api/auth/login", json={"email": f"track-{suffix}@example.com", "password": "StrongPass123!"})
    assert login.status_code == 200, login.text
    return login.json()["access_token"]


def _post_location(token: str, latitude=12.9716, longitude=77.5946, accuracy=8.5, speed=1.2):
    return client.post(
        "/api/safety/location",
        headers={"Authorization": f"Bearer {token}"},
        json={"latitude": latitude, "longitude": longitude, "accuracy": accuracy, "speed": speed},
    )


def test_authenticated_location_submission_and_readback():
    token = _create_token()
    resp = _post_location(token, latitude=13.0827, longitude=80.2707, accuracy=12.0, speed=2.5)
    assert resp.status_code == 201, resp.text

    body = resp.json()
    assert body["latitude"] == 13.0827
    assert body["longitude"] == 80.2707
    assert body["accuracy"] == 12.0
    assert body["speed"] == 2.5

    listed = client.get("/api/safety/location", headers={"Authorization": f"Bearer {token}"})
    assert listed.status_code == 200, listed.text
    records = listed.json()
    assert len(records) == 1
    assert records[0]["id"] == body["id"]

    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert records[0]["user_id"] == me.json()["id"]


def test_location_requires_authentication():
    resp = client.post("/api/safety/location", json={"latitude": 1.23, "longitude": 4.56})
    assert resp.status_code in (401, 403)

    bad_token = client.post(
        "/api/safety/location",
        headers={"Authorization": "Bearer not-a-real-token"},
        json={"latitude": 1.23, "longitude": 4.56},
    )
    assert bad_token.status_code == 401


def test_latest_endpoint_returns_most_recent_own_point():
    token = _create_token()
    first = _post_location(token, latitude=10.0, longitude=20.0)
    assert first.status_code == 201, first.text
    second = _post_location(token, latitude=11.5, longitude=21.5, accuracy=5.0, speed=0.0)
    assert second.status_code == 201, second.text

    latest = client.get("/api/safety/location/latest", headers={"Authorization": f"Bearer {token}"})
    assert latest.status_code == 200, latest.text
    assert latest.json()["id"] == second.json()["id"]
    assert latest.json()["latitude"] == 11.5


def test_latest_endpoint_404_when_no_locations():
    token = _create_token()
    latest = client.get("/api/safety/location/latest", headers={"Authorization": f"Bearer {token}"})
    assert latest.status_code == 404


def test_locations_are_not_shared_between_users():
    token_a = _create_token()
    token_b = _create_token()
    assert _post_location(token_a).status_code == 201, token_a

    list_b = client.get("/api/safety/location", headers={"Authorization": f"Bearer {token_b}"})
    assert list_b.status_code == 200
    assert list_b.json() == []

    latest_b = client.get("/api/safety/location/latest", headers={"Authorization": f"Bearer {token_b}"})
    assert latest_b.status_code == 404


def test_existing_minimum_payload_still_accepted():
    """Continuous feed only needs lat/lng; optional fields stay optional."""
    token = _create_token()
    resp = client.post(
        "/api/safety/location",
        headers={"Authorization": f"Bearer {token}"},
        json={"latitude": -33.8688, "longitude": 151.2093},
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["accuracy"] is None
    assert resp.json()["speed"] is None