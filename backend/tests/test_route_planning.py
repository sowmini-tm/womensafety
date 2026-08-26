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
    # Deterministic heuristic: base 20 + >5 km (+10) + >15 min (+5) = 35 -> MEDIUM.
    risk = result["route_data"]["risk"]
    assert result["risk_score"] == risk["score"] == 35
    assert risk["level"] == "MEDIUM"
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


def _mock_fixed_osrm(distance: float, duration: float):
    return lambda *args, **kwargs: {
        "coordinates": [
            {"latitude": 12.9716, "longitude": 77.5946},
            {"latitude": 12.9352, "longitude": 77.6245},
        ],
        "distance": distance,
        "duration": duration,
    }


def test_low_risk_short_route_inside_user_safe_zone(monkeypatch):
    monkeypatch.setattr(safety_router, "fetch_route_from_osrm", _mock_fixed_osrm(distance=600.0, duration=120.0))
    token = _create_token()

    created = client.post(
        "/api/safety/geofences",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "Home", "latitude": 12.9352, "longitude": 77.6245, "radius": 500, "is_active": True},
    )
    assert created.status_code == 201, created.text

    resp = _plan_route(token)

    assert resp.status_code == 201, resp.text
    result = resp.json()["results"][0]
    risk = result["route_data"]["risk"]
    assert risk["level"] == "LOW"
    assert risk["score"] < RISK_LEVEL_MEDIUM_CROSSCHECK  # below MEDIUM threshold (35)
    assert any("active safe zones" in factor for factor in risk["factors"])
    assert result["risk_score"] == risk["score"]
    # Real OSRM geometry/distance/duration preserved untouched by scoring.
    assert result["route_data"]["source"] == "osrm"
    assert result["distance"] == 600.0
    assert result["estimated_duration"] == 120.0


def test_high_risk_long_night_route_outside_safe_zones(monkeypatch):
    monkeypatch.setattr(safety_router, "fetch_route_from_osrm", _mock_fixed_osrm(distance=12_000.0, duration=2_400.0))
    token = _create_token()

    resp = client.post(
        "/api/safety/route-plan",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "start_latitude": 12.9716,
            "start_longitude": 77.5946,
            "destination_latitude": 12.9352,
            "destination_longitude": 77.6245,
            "route_type": "night",
        },
    )

    assert resp.status_code == 201, resp.text
    result = resp.json()["results"][0]
    risk = result["route_data"]["risk"]
    assert risk["level"] == "HIGH"
    assert risk["score"] >= RISK_LEVEL_HIGH_CROSSCHECK  # 20 base +25 night +15 long +10 duration = 70
    assert result["risk_score"] == risk["score"]
    joined = " ".join(risk["factors"]).lower()
    assert "night" in joined and "long route" in joined


def test_scoring_is_deterministic_and_repeatable(monkeypatch):
    monkeypatch.setattr(safety_router, "fetch_route_from_osrm", _mock_fixed_osrm(distance=3_000.0, duration=900.0))

    first = _plan_route(_create_token())
    second = _plan_route(_create_token())

    assert first.status_code == second.status_code == 201
    risk_first = first.json()["results"][0]["route_data"]["risk"]
    risk_second = second.json()["results"][0]["route_data"]["risk"]
    assert risk_first == risk_second
    assert first.json()["results"][0]["risk_score"] == risk_first["score"]


def test_scoring_survives_extreme_or_invalid_inputs():
    from app.routers.safety import calculate_route_safety

    absurd = calculate_route_safety(1e15, 5e9, "night", False)
    assert 0 <= absurd["score"] <= 100
    assert absurd["level"] in {"LOW", "MEDIUM", "HIGH"}
    assert absurd["factors"]

    negative_distance = calculate_route_safety(-100, -50, "unsafe", True)
    assert 0 <= negative_distance["score"] <= 100
    assert negative_distance["level"] in {"LOW", "MEDIUM", "HIGH"}

    zero_duration = calculate_route_safety(1200, 0, "safe", True)
    assert 0 <= zero_duration["score"] <= 100
    garbage = calculate_route_safety("not-a-number", None, "", False)
    assert 0 <= garbage["score"] <= 100


RISK_LEVEL_MEDIUM_CROSSCHECK = 35
RISK_LEVEL_HIGH_CROSSCHECK = 65