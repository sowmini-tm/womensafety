import uuid

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def create_user():
    email = f"mvp-{uuid.uuid4()}@example.com"
    mobile = f"+{uuid.uuid4().int % 9000000000 + 1000000000}"
    password = "StrongPass123!"
    register = client.post(
        "/api/auth/register",
        json={"email": email, "mobile_number": mobile, "password": password},
    )
    assert register.status_code == 201, register.text
    login = client.post(
        "/api/auth/login",
        json={"email": email, "password": password},
    )
    assert login.status_code == 200, login.text
    token = login.json()["access_token"]
    return token


def test_profile_and_medical_details():
    token = create_user()
    profile = client.post(
        "/api/profile",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "full_name": "Test User",
            "gender": "female",
            "city": "Bangalore",
            "state": "Karnataka",
            "address": "Sample address",
        },
    )
    assert profile.status_code == 201, profile.text

    medical = client.post(
        "/api/profile/medical",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "blood_group": "O+",
            "allergies": "None",
            "medical_conditions": "None",
            "medications": "None",
        },
    )
    assert medical.status_code == 201, medical.text


def test_emergency_and_risk_features():
    token = create_user()
    contact = client.post(
        "/api/safety/emergency-contacts",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "name": "Mom",
            "phone": "+15550000000",
            "relationship_type": "Mother",
            "is_primary": True,
        },
    )
    assert contact.status_code == 201, contact.text

    location = client.post(
        "/api/safety/location",
        headers={"Authorization": f"Bearer {token}"},
        json={"latitude": 12.9716, "longitude": 77.5946, "accuracy": 10, "speed": 1.5},
    )
    assert location.status_code == 201, location.text

    risk = client.post(
        "/api/safety/risk-assessment",
        headers={"Authorization": f"Bearer {token}"},
        json={"latitude": 12.9716, "longitude": 77.5946, "speed": 15.0, "risk_factors": ["night_travel"]},
    )
    assert risk.status_code == 201, risk.text

    helplines = client.get("/api/safety/helplines")
    assert helplines.status_code == 200, helplines.text
    assert len(helplines.json()) > 0

    chatbot = client.post(
        "/api/safety/chatbot",
        json={"message": "What should I do if I feel unsafe?"},
    )
    assert chatbot.status_code == 200, chatbot.text

    geofence = client.post(
        "/api/safety/geofences",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "Home", "latitude": 12.9716, "longitude": 77.5946, "radius": 250, "is_active": True},
    )
    assert geofence.status_code == 201, geofence.text

    route = client.post(
        "/api/safety/route-plan",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "start_latitude": 12.9700,
            "start_longitude": 77.5900,
            "destination_latitude": 12.9750,
            "destination_longitude": 77.6000,
            "route_type": "safe",
        },
    )
    assert route.status_code == 201, route.text
    body = route.json()
    assert body["route_request"]["start_latitude"] == 12.97
    assert len(body["results"]) >= 1


def test_recent_activity_feed():
    token = create_user()
    client.post(
        "/api/safety/sos",
        headers={"Authorization": f"Bearer {token}"},
        json={"latitude": 12.9716, "longitude": 77.5946, "description": "Need help"},
    )
    client.post(
        "/api/safety/risk-assessment",
        headers={"Authorization": f"Bearer {token}"},
        json={"latitude": 12.9716, "longitude": 77.5946, "speed": 25.0, "risk_factors": ["night_travel"]},
    )
    response = client.get(
        "/api/safety/activity",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200, response.text
    items = response.json()
    assert len(items) >= 2
    assert any(item["type"] == "sos" for item in items)

    notifications = client.get(
        "/api/safety/notifications",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert notifications.status_code == 200, notifications.text
    assert len(notifications.json()) >= 1
