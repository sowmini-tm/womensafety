"""Phase 7A tests: real OSRM-backed route planning with the service mocked.

No test here performs real network requests — ``fetch_route_from_osrm`` is
monkeypatched before every ``POST /api/safety/route-plan`` call.
"""
import uuid

from fastapi.testclient import TestClient

from app.main import app
from app.routers import safety as safety_router

client = TestClient(app)


def _create_token() -> str:
    suffix = uuid.uuid4()
    register = client.post(
        "/api/auth/register",
        json={
            "email": f"route-{suffix}@example.com",
            "mobile_number": f"+{suffix.int % 9000000000 + 1000000000}",
            "password": "StrongPass123!",
        },
    )
    assert register.status_code == 201, register.text
    login = client.post("/api/auth/login", json={"email": f"route-{suffix}@example.com", "password": "StrongPass123!"})
    assert login.status_code == 200, login.text
    return login.json()["access_token"]


def _plan_route(token: str | None):
    return client.post(
        "/api/safety/route-plan",
        headers={"Authorization": f"Bearer {token}"} if token else {},
        json={
            "start_latitude": 12.9716,
            "start_longitude": 77.5946,
            "destination_latitude": 12.9352,
            "destination_longitude": 77.6245,
            "route_type": "safe",
        },
    )


def test_successful_route_returns_real_geometry_distance_duration(monkeypatch):
    fake_coordinates = [
        {"latitude": 12.9716, "longitude": 77.5946},
        {"latitude": 12.9784, "longitude": 77.6068},
        {"latitude": 12.9352, "longitude": 77.6245},
    ]
    captured_args = []

    def fake_fetch(start_latitude, start_longitude, destination_latitude, destination_longitude, **_kwargs):
        captured_args.append((start_latitude, start_longitude, destination_latitude, destination_longitude))
        return {"coordinates": fake_coordinates, "distance": 8320.0, "duration": 975.0}

    monkeypatch.setattr(safety_router, "fetch_route_from_osrm", fake_fetch)
    token = _create_token()

    resp = _plan_route(token)

    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["results"], "expected at least one route result"

    result = body["results"][0]
    assert result["distance"] == 8320.0
    assert result["estimated_duration"] == 975.0
    assert result["risk_score"] == 15  # 'safe' route_type keeps the low score
    assert result["route_data"]["source"] == "osrm"
    assert result["route_data"]["coordinates"] == fake_coordinates

    # Coordinates must reach the routing service with correct start/dest pairing.
    assert captured_args[-1] == (12.9716, 77.5946, 12.9352, 77.6245)


def test_routing_service_failure_is_reported_not_invented(monkeypatch):
    """OSRM returning no usable route must yield 502 and zero fabricated data."""
    monkeypatch.setattr(safety_router, "fetch_route_from_osrm", lambda *args, **kwargs: None)
    token = _create_token()

    resp = _plan_route(token)

    assert resp.status_code == 502, resp.text
    body = resp.json()
    assert "routing" in body["detail"].lower()
    assert "results" not in body
    assert "route_data" not in body


def test_route_plan_requires_authentication():
    resp = _plan_route(None)
    assert resp.status_code in (401, 403)