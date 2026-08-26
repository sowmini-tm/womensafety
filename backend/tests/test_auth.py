import uuid

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_register_and_login_flow():
    email = f"user-{uuid.uuid4()}@example.com"
    mobile = f"+{uuid.uuid4().int % 9000000000 + 1000000000}"
    payload = {
        "email": email,
        "mobile_number": mobile,
        "password": "StrongPass123!",
    }

    register_response = client.post("/api/auth/register", json=payload)
    assert register_response.status_code == 201, register_response.text

    login_response = client.post("/api/auth/login", json={
        "email": email,
        "password": "StrongPass123!",
    })
    assert login_response.status_code == 200, login_response.text
    body = login_response.json()
    assert "access_token" in body
    assert "refresh_token" in body

    me_response = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {body['access_token']}"},
    )
    assert me_response.status_code == 200, me_response.text
    assert me_response.json()["email"] == email


def test_refresh_token_flow():
    email = f"user-{uuid.uuid4()}@example.com"
    mobile = f"+{uuid.uuid4().int % 9000000000 + 1000000000}"
    register_response = client.post(
        "/api/auth/register",
        json={
            "email": email,
            "mobile_number": mobile,
            "password": "StrongPass123!",
        },
    )
    assert register_response.status_code == 201, register_response.text

    login_response = client.post(
        "/api/auth/login",
        json={
            "email": email,
            "password": "StrongPass123!",
        },
    )
    refresh_response = client.post(
        "/api/auth/refresh",
        json={"refresh_token": login_response.json()["refresh_token"]},
    )
    assert refresh_response.status_code == 200, refresh_response.text
    assert "access_token" in refresh_response.json()
