"""Phase 4 tests: contact & geofence PUT/DELETE with ownership enforcement."""
import uuid

from conftest import TestingSessionLocal  # noqa: E402


def _register_and_login(client) -> dict:
    suffix = uuid.uuid4().hex[:10]
    email = f"crud-{suffix}@example.com"
    mobile = f"+1{int(suffix, 16) % 900000000 + 1000000000}"
    resp = client.post(
        "/api/auth/register",
        json={"email": email, "mobile_number": mobile, "password": "StrongPass123!"},
    )
    assert resp.status_code == 201, resp.text
    login = client.post("/api/auth/login", json={"email": email, "password": "StrongPass123!"})
    assert login.status_code == 200, login.text
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


CONTACT_PAYLOAD = {
    "name": "Mom",
    "phone": "+15550001111",
    "relationship_type": "Family",
    "is_primary": True,
}

GEOFENCE_PAYLOAD = {"name": "Home Safe Zone", "latitude": 12.9716, "longitude": 77.5946, "radius": 250, "is_active": True}


# ---------------------------------------------------------------------------
# Emergency contacts
# ---------------------------------------------------------------------------

class TestContactUpdate:
    def test_partial_update_changes_only_sent_fields(self, client):
        headers = _register_and_login(client)
        created = client.post("/api/safety/emergency-contacts", headers=headers, json=CONTACT_PAYLOAD).json()

        resp = client.put(f"/api/safety/emergency-contacts/{created['id']}", headers=headers, json={"name": "Mum"})

        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["name"] == "Mum"
        assert body["phone"] == "+15550001111"
        assert body["relationship_type"] == "Family"
        assert body["is_primary"] is True

    def test_full_update_including_clearing_email(self, client):
        headers = _register_and_login(client)
        created = client.post(
            "/api/safety/emergency-contacts",
            headers=headers,
            json={**CONTACT_PAYLOAD, "email": "mom@example.com"},
        ).json()
        assert created["email"] == "mom@example.com"

        resp = client.put(
            f"/api/safety/emergency-contacts/{created['id']}",
            headers=headers,
            json={"phone": "+15550009999", "email": None, "is_primary": False},
        )

        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["phone"] == "+15550009999"
        assert body["email"] is None
        assert body["is_primary"] is False
        assert body["name"] == "Mom"

    def test_update_persists_to_database(self, client):
        from app.models.emergency_contact import EmergencyContact

        headers = _register_and_login(client)
        created = client.post("/api/safety/emergency-contacts", headers=headers, json=CONTACT_PAYLOAD).json()
        client.put(f"/api/safety/emergency-contacts/{created['id']}", headers=headers, json={"name": "Persisted"})

        with TestingSessionLocal() as db:
            row = db.query(EmergencyContact).filter(EmergencyContact.id == created["id"]).first()
            assert row.name == "Persisted"


class TestContactDelete:
    def test_delete_removes_contact(self, client):
        from app.models.emergency_contact import EmergencyContact

        headers = _register_and_login(client)
        created = client.post("/api/safety/emergency-contacts", headers=headers, json=CONTACT_PAYLOAD).json()

        resp = client.delete(f"/api/safety/emergency-contacts/{created['id']}", headers=headers)

        assert resp.status_code == 204, resp.text
        assert resp.content == b""
        remaining = client.get("/api/safety/emergency-contacts", headers=headers).json()
        assert remaining == []
        with TestingSessionLocal() as db:
            assert db.query(EmergencyContact).filter(EmergencyContact.id == created["id"]).first() is None


class TestContactNotFoundAndOwnership:
    def test_update_unknown_id_returns_404(self, client):
        headers = _register_and_login(client)
        resp = client.put(f"/api/safety/emergency-contacts/{uuid.uuid4()}", headers=headers, json={"name": "X"})
        assert resp.status_code == 404

    def test_delete_unknown_id_returns_404(self, client):
        headers = _register_and_login(client)
        resp = client.delete(f"/api/safety/emergency-contacts/{uuid.uuid4()}", headers=headers)
        assert resp.status_code == 404

    def test_cannot_update_another_users_contact(self, client):
        owner_headers = _register_and_login(client)
        attacker_headers = _register_and_login(client)
        owned = client.post("/api/safety/emergency-contacts", headers=owner_headers, json=CONTACT_PAYLOAD).json()

        resp = client.put(
            f"/api/safety/emergency-contacts/{owned['id']}",
            headers=attacker_headers,
            json={"phone": "+19999999999"},
        )

        assert resp.status_code == 404  # must not leak existence
        after = client.get("/api/safety/emergency-contacts", headers=owner_headers).json()[0]
        assert after["phone"] == "+15550001111"
        attacker_list = client.get("/api/safety/emergency-contacts", headers=attacker_headers).json()
        assert all(c["id"] != owned["id"] for c in attacker_list)

    def test_cannot_delete_another_users_contact(self, client):
        from app.models.emergency_contact import EmergencyContact

        owner_headers = _register_and_login(client)
        attacker_headers = _register_and_login(client)
        owned = client.post("/api/safety/emergency-contacts", headers=owner_headers, json=CONTACT_PAYLOAD).json()

        resp = client.delete(f"/api/safety/emergency-contacts/{owned['id']}", headers=attacker_headers)

        assert resp.status_code == 404
        with TestingSessionLocal() as db:
            row = db.query(EmergencyContact).filter(EmergencyContact.id == owned["id"]).first()
            assert row is not None
            assert row.phone == "+15550001111"


# ---------------------------------------------------------------------------
# Geofences
# ---------------------------------------------------------------------------

class TestGeofenceUpdate:
    def test_partial_update_changes_only_sent_fields(self, client):
        headers = _register_and_login(client)
        created = client.post("/api/safety/geofences", headers=headers, json=GEOFENCE_PAYLOAD).json()

        resp = client.put(
            f"/api/safety/geofences/{created['id']}",
            headers=headers,
            json={"radius": 500, "is_active": False},
        )

        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["radius"] == 500
        assert body["is_active"] is False
        assert body["name"] == "Home Safe Zone"
        assert body["latitude"] == 12.9716
        assert body["longitude"] == 77.5946

    def test_update_persists_to_database(self, client):
        from app.models.geofence import Geofence

        headers = _register_and_login(client)
        created = client.post("/api/safety/geofences", headers=headers, json=GEOFENCE_PAYLOAD).json()
        client.put(f"/api/safety/geofences/{created['id']}", headers=headers, json={"name": "Office Zone"})

        with TestingSessionLocal() as db:
            row = db.query(Geofence).filter(Geofence.id == created["id"]).first()
            assert row.name == "Office Zone"


class TestGeofenceDelete:
    def test_delete_removes_geofence(self, client):
        from app.models.geofence import Geofence

        headers = _register_and_login(client)
        created = client.post("/api/safety/geofences", headers=headers, json=GEOFENCE_PAYLOAD).json()

        resp = client.delete(f"/api/safety/geofences/{created['id']}", headers=headers)

        assert resp.status_code == 204, resp.text
        assert resp.content == b""
        remaining = client.get("/api/safety/geofences", headers=headers).json()
        assert remaining == []
        with TestingSessionLocal() as db:
            assert db.query(Geofence).filter(Geofence.id == created["id"]).first() is None


class TestGeofenceNotFoundAndOwnership:
    def test_update_unknown_id_returns_404(self, client):
        headers = _register_and_login(client)
        resp = client.put(f"/api/safety/geofences/{uuid.uuid4()}", headers=headers, json={"name": "X"})
        assert resp.status_code == 404

    def test_delete_unknown_id_returns_404(self, client):
        headers = _register_and_login(client)
        resp = client.delete(f"/api/safety/geofences/{uuid.uuid4()}", headers=headers)
        assert resp.status_code == 404

    def test_cannot_update_another_users_geofence(self, client):
        owner_headers = _register_and_login(client)
        attacker_headers = _register_and_login(client)
        owned = client.post("/api/safety/geofences", headers=owner_headers, json=GEOFENCE_PAYLOAD).json()

        resp = client.put(
            f"/api/safety/geofences/{owned['id']}",
            headers=attacker_headers,
            json={"radius": 9999},
        )

        assert resp.status_code == 404
        after = client.get("/api/safety/geofences", headers=owner_headers).json()[0]
        assert after["radius"] == 250

    def test_cannot_delete_another_users_geofence(self, client):
        from app.models.geofence import Geofence

        owner_headers = _register_and_login(client)
        attacker_headers = _register_and_login(client)
        owned = client.post("/api/safety/geofences", headers=owner_headers, json=GEOFENCE_PAYLOAD).json()

        resp = client.delete(f"/api/safety/geofences/{owned['id']}", headers=attacker_headers)

        assert resp.status_code == 404
        with TestingSessionLocal() as db:
            row = db.query(Geofence).filter(Geofence.id == owned["id"]).first()
            assert row is not None
            assert row.radius == 250


