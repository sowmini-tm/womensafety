"""Phase 9 tests: real geofence entry/exit detection on /api/safety/location."""
import math
import uuid

from fastapi.testclient import TestClient

from app.main import app
from app.routers.safety import _haversine_meters as router_haversine_meters
from app.services.geofence_service import haversine_meters

# tests/ is not a package; conftest sits on sys.path during collection.
from conftest import TestingSessionLocal  # noqa: E402

client = TestClient(app)

CENTER_LAT = 12.9716
CENTER_LNG = 77.5946
EARTH_RADIUS_M = 6_371_000.0
METERS_PER_DEG_LAT = math.pi * EARTH_RADIUS_M / 180.0  # meridian arc length per degree


def _register_and_login() -> str:
    suffix = uuid.uuid4()
    register = client.post(
        "/api/auth/register",
        json={
            "email": f"geo-{suffix}@example.com",
            "mobile_number": f"+{suffix.int % 9000000000 + 1000000000}",
            "password": "StrongPass123!",
        },
    )
    assert register.status_code == 201, register.text
    login = client.post(
        "/api/auth/login",
        json={"email": f"geo-{suffix}@example.com", "password": "StrongPass123!"},
    )
    assert login.status_code == 200, login.text
    return login.json()["access_token"]


def _make_geofence(token: str, name="Home Zone", lat=CENTER_LAT, lng=CENTER_LNG, radius=500, is_active=True) -> dict:
    resp = client.post(
        "/api/safety/geofences",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "name": name,
            "latitude": lat,
            "longitude": lng,
            "radius": radius,
            "is_active": is_active,
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def _post_location(token: str, lat: float, lng: float) -> dict:
    resp = client.post(
        "/api/safety/location",
        headers={"Authorization": f"Bearer {token}"},
        json={"latitude": lat, "longitude": lng},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def _lat_offset(meters: float) -> float:
    """Northward latitude offset that maps to roughly `meters` on the ground."""
    return meters / METERS_PER_DEG_LAT


def _inside_point() -> tuple[float, float]:
    """A point comfortably inside a default 500 m geofence (~55 m from center)."""
    return CENTER_LAT + _lat_offset(55), CENTER_LNG


def _outside_point() -> tuple[float, float]:
    """A point clearly outside a default 500 m geofence (~1100 m from center)."""
    return CENTER_LAT + _lat_offset(1100), CENTER_LNG


def test_first_location_inside_does_not_create_transition():
    token = _register_and_login()
    created = _make_geofence(token)

    body = _post_location(token, *_inside_point())

    assert body["geofence_events"] == []
    with TestingSessionLocal() as db:
        from app.models.geofence_state import GeofenceState

        row = (
            db.query(GeofenceState)
            .filter(GeofenceState.geofence_id == created["id"])
            .first()
        )
        assert row is not None
        assert row.last_seen_inside is True

    feed = client.get("/api/safety/notifications", headers={"Authorization": f"Bearer {token}"})
    assert all("Geofence update" not in item["message"] for item in feed.json())


def test_first_location_outside_does_not_create_transition():
    token = _register_and_login()
    _make_geofence(token)

    body = _post_location(token, *_outside_point())

    assert body["geofence_events"] == []


def test_user_without_geofences_gets_empty_events_and_old_contract():
    token = _register_and_login()

    resp = client.post(
        "/api/safety/location",
        headers={"Authorization": f"Bearer {token}"},
        json={"latitude": 12.9716, "longitude": 77.5946, "accuracy": 9.0, "speed": 1.5},
    )

    assert resp.status_code == 201
    body = resp.json()
    assert body["geofence_events"] == []
    for key in ("id", "user_id", "latitude", "longitude", "accuracy", "speed"):
        assert key in body

# ---------------------------------------------------------------------------
# ENTERED transitions
# ---------------------------------------------------------------------------

def test_outside_to_inside_creates_exactly_one_entered_event():
    token = _register_and_login()
    created = _make_geofence(token)

    baseline = _post_location(token, *_outside_point())
    assert baseline["geofence_events"] == []

    entered = _post_location(token, *_inside_point())
    events = entered["geofence_events"]
    assert len(events) == 1
    assert events[0]["event_type"] == "ENTERED"
    assert events[0]["geofence_id"] == created["id"]
    assert events[0]["geofence_name"] == created["name"]
    assert 0 <= events[0]["distance_meters"] <= 500


def test_repeated_inside_locations_do_not_duplicate_entered():
    token = _register_and_login()
    _make_geofence(token)

    assert _post_location(token, *_outside_point())["geofence_events"] == []
    first = _post_location(token, *_inside_point())
    second = _post_location(token, *_inside_point())
    third = _post_location(token, *_inside_point())

    assert len(first["geofence_events"]) == 1
    assert second["geofence_events"] == []
    assert third["geofence_events"] == []


# ---------------------------------------------------------------------------
# EXITED transitions
# ---------------------------------------------------------------------------

def test_inside_to_outside_creates_exactly_one_exited_event():
    token = _register_and_login()
    created = _make_geofence(token)

    assert _post_location(token, *_inside_point())["geofence_events"] == []

    exited = _post_location(token, *_outside_point())
    events = exited["geofence_events"]
    assert len(events) == 1
    assert events[0]["event_type"] == "EXITED"
    assert events[0]["geofence_id"] == created["id"]
    assert events[0]["distance_meters"] > 500

    again = _post_location(token, *_outside_point())
    further = _post_location(token, CENTER_LAT + _lat_offset(2500), CENTER_LNG)
    assert again["geofence_events"] == []
    assert further["geofence_events"] == []


# ---------------------------------------------------------------------------
# Multiple geofences behave independently
# ---------------------------------------------------------------------------

def test_multiple_geofences_trigger_independently():
    token = _register_and_login()
    zone_a = _make_geofence(token, name="Zone A")
    far_lat, far_lng = -33.8688, 151.2093  # Sydney, nowhere near zone A
    zone_b = _make_geofence(token, name="Zone B", lat=far_lat, lng=far_lng, radius=400)

    # First fix inside A establishes A=inside and B=outside without any event.
    first = _post_location(token, *_inside_point())
    assert first["geofence_events"] == []

    # Leaving both zones fires only A's EXITED.
    left_a = _post_location(token, 13.5, 78.5)
    events = left_a["geofence_events"]
    assert len(events) == 1
    assert events[0]["event_type"] == "EXITED"
    assert events[0]["geofence_id"] == zone_a["id"]

    # Arriving inside B fires only B's ENTERED.
    entered_b = _post_location(token, far_lat + _lat_offset(50), far_lng)
    events = entered_b["geofence_events"]
    assert len(events) == 1
    assert events[0]["event_type"] == "ENTERED"
    assert events[0]["geofence_id"] == zone_b["id"]

# ---------------------------------------------------------------------------
# Inactive geofences are ignored
# ---------------------------------------------------------------------------

def test_inactive_geofence_is_ignored():
    token = _register_and_login()
    inactive = _make_geofence(token, name="Sleeping Zone", is_active=False)

    assert _post_location(token, *_outside_point())["geofence_events"] == []
    inside = _post_location(token, *_inside_point())
    outside = _post_location(token, *_outside_point())

    assert inside["geofence_events"] == []
    assert outside["geofence_events"] == []

    with TestingSessionLocal() as db:
        from app.models.geofence_state import GeofenceState

        assert db.query(GeofenceState).filter(GeofenceState.geofence_id == inactive["id"]).count() == 0


# ---------------------------------------------------------------------------
# Cross-user isolation
# ---------------------------------------------------------------------------

def test_geofence_events_are_isolated_per_user():
    owner = _register_and_login()
    stranger = _register_and_login()
    _make_geofence(owner, name="Owner Only Zone")

    # Stranger walks straight through the owner's zone center: nothing may fire.
    first_stranger_fix = _post_location(stranger, *_outside_point())
    inside_for_owner_but_not_stranger = _post_location(stranger, *_inside_point())
    back_out = _post_location(stranger, *_outside_point())

    assert first_stranger_fix["geofence_events"] == []
    assert inside_for_owner_but_not_stranger["geofence_events"] == []
    assert back_out["geofence_events"] == []

    # The owner's own state must not have been touched by the stranger's fixes.
    owner_baseline = _post_location(owner, *_inside_point())
    assert owner_baseline["geofence_events"] == []

    with TestingSessionLocal() as db:
        from app.models.geofence_state import GeofenceState

        states = db.query(GeofenceState).all()
        assert len(states) == 1  # only the owner has state for this geofence
        assert states[0].last_seen_inside is True


# ---------------------------------------------------------------------------
# Boundary behavior: distance <= radius counts as inside
# ---------------------------------------------------------------------------

def test_distance_exactly_equal_to_radius_counts_as_inside():
    token = _register_and_login()
    probe = (CENTER_LAT + _lat_offset(750), CENTER_LNG)
    exact_distance = haversine_meters(CENTER_LAT, CENTER_LNG, probe[0], probe[1])
    _make_geofence(token, radius=exact_distance)  # radius == distance -> inside

    assert _post_location(token, *_outside_point())["geofence_events"] == []
    on_boundary = _post_location(token, *probe)

    events = on_boundary["geofence_events"]
    assert len(events) == 1
    assert events[0]["event_type"] == "ENTERED"


def test_just_beyond_radius_counts_as_outside():
    token = _register_and_login()
    _make_geofence(token, radius=1000)

    just_outside = (CENTER_LAT + _lat_offset(1050), CENTER_LNG)
    distance = haversine_meters(CENTER_LAT, CENTER_LNG, just_outside[0], just_outside[1])
    assert distance > 1000

    baseline_inside = _post_location(token, *_inside_point())
    assert baseline_inside["geofence_events"] == []

    exited = _post_location(token, *just_outside)
    assert [e["event_type"] for e in exited["geofence_events"]] == ["EXITED"]

# ---------------------------------------------------------------------------
# Haversine correctness
# ---------------------------------------------------------------------------

def test_haversine_zero_distance_for_identical_points():
    assert haversine_meters(CENTER_LAT, CENTER_LNG, CENTER_LAT, CENTER_LNG) == 0.0


def test_haversine_one_degree_of_latitude():
    d = haversine_meters(0.0, 0.0, 1.0, 0.0)
    assert abs(d - METERS_PER_DEG_LAT) < 1.0  # ~111,195 m per degree of latitude


def test_haversine_quarter_circumference_on_equator():
    d = haversine_meters(0.0, 0.0, 0.0, 90.0)
    expected = math.pi * EARTH_RADIUS_M / 2.0
    assert abs(d - expected) < 2.0


def test_service_haversine_matches_existing_route_plan_haversine():
    pairs = [
        (CENTER_LAT, CENTER_LNG, 12.9876, 77.6103),
        (-33.8688, 151.2093, 48.8566, 2.3522),
        (51.5074, -0.1278, 40.7128, -74.0060),
    ]
    for lat1, lon1, lat2, lon2 in pairs:
        assert haversine_meters(lat1, lon1, lat2, lon2) == router_haversine_meters(lat1, lon1, lat2, lon2)


# ---------------------------------------------------------------------------
# Truthful activity records on real transitions
# ---------------------------------------------------------------------------

def test_transition_records_activity_once_and_never_marks_sent():
    token = _register_and_login()
    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"}).json()

    _make_geofence(token)
    assert _post_location(token, *_outside_point())["geofence_events"] == []
    assert _post_location(token, *_inside_point())["geofence_events"]
    assert _post_location(token, *_inside_point())["geofence_events"] == []

    feed = client.get("/api/safety/notifications", headers={"Authorization": f"Bearer {token}"})
    assert feed.status_code == 200
    items = [n for n in feed.json() if n["message"].startswith("Geofence update")]
    assert len(items) == 1

    record = items[0]
    assert record["type"] == "INFO"
    assert record["user_id"] == me["id"]
    assert record["channel"] is None          # no delivery channel was used
    assert record["status"] == "PENDING"      # nothing external was delivered
    assert record["sent_at"] is None
