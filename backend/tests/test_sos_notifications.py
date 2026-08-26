"""Phase 1 tests: real SOS emergency-contact notification delivery.

All Twilio/SendGrid calls are mocked - no real SMS or email is ever sent.
"""
import os
from unittest import mock

import pytest

from app.services import notification_service as ns_module
from app.services.notification_service import NotificationService

# tests/ is not a package; conftest sits on sys.path during collection.
from conftest import TestingSessionLocal  # noqa: E402

SOS_PAYLOAD = {"latitude": 12.9716, "longitude": 77.5946, "description": "Need help"}


def register_and_login(client) -> dict:
    import uuid

    suffix = uuid.uuid4().hex[:10]
    email = f"sos-{suffix}@example.com"
    mobile = f"+1{int(suffix, 16) % 900000000 + 1000000000}"
    password = "StrongPass123!"
    resp = client.post(
        "/api/auth/register",
        json={"email": email, "mobile_number": mobile, "password": password},
    )
    assert resp.status_code == 201, resp.text
    login = client.post("/api/auth/login", json={"email": email, "password": password})
    assert login.status_code == 200, login.text
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def add_contact(client, headers: dict, name: str = "Mom", phone: str = "+15550001111", email: str | None = None) -> dict:
    resp = client.post(
        "/api/safety/emergency-contacts",
        headers=headers,
        json={"name": name, "phone": phone, "email": email, "is_primary": True},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


@pytest.fixture(autouse=True)
def no_provider_credentials(monkeypatch):
    """Guarantee a clean credential slate for every test."""
    for var in (
        "TWILIO_ACCOUNT_SID",
        "TWILIO_AUTH_TOKEN",
        "TWILIO_FROM_NUMBER",
        "SENDGRID_API_KEY",
        "SENDGRID_FROM_EMAIL",
    ):
        monkeypatch.delenv(var, raising=False)


# ---------------------------------------------------------------------------
# NotificationService unit behaviour
# ---------------------------------------------------------------------------

class TestNotificationService:
    def test_missing_twilio_credentials_fail_safely(self):
        result = NotificationService.send_sms("+15550001111", "test message")
        assert result["status"] == "failed"
        assert "not configured" in result["error"]
        assert result["provider"] == "twilio"

    def test_missing_sendgrid_credentials_fail_safely(self):
        result = NotificationService.send_email("mom@example.com", "SOS Alert", "body")
        assert result["status"] == "failed"
        assert "not configured" in result["error"]
        assert result["provider"] == "sendgrid"

    def test_successful_sms_delivery(self, monkeypatch):
        """Fake credentials + fake twilio module; no real SDK/network is used."""
        monkeypatch.setenv("TWILIO_ACCOUNT_SID", "ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx")
        monkeypatch.setenv("TWILIO_AUTH_TOKEN", "fake-token")
        monkeypatch.setenv("TWILIO_FROM_NUMBER", "+15551110000")
        fake_twilio_rest = mock.MagicMock()
        fake_twilio_rest.Client.return_value.messages.create.return_value = mock.Mock(sid="SM123")
        with mock.patch.dict(
            os.sys.modules,
            {"twilio": mock.MagicMock(rest=fake_twilio_rest), "twilio.rest": fake_twilio_rest},
        ):
            result = NotificationService.send_sms("+15550001111", "test message")
        assert result["status"] == "sent"
        assert result["sid"] == "SM123"

    def test_failed_sms_delivery_reports_failure_without_secrets(self, monkeypatch):
        monkeypatch.setenv("TWILIO_ACCOUNT_SID", "ACaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa")
        monkeypatch.setenv("TWILIO_AUTH_TOKEN", "fake-token")
        monkeypatch.setenv("TWILIO_FROM_NUMBER", "+15551110000")
        fake_twilio_rest = mock.MagicMock()
        # Error strings often echo credentials; this one embeds a 32-hex token.
        leaked_secret = "ff11aa22bb33cc44dd55ee66ff77aa88"
        fake_twilio_rest.Client.return_value.messages.create.side_effect = Exception(
            f"auth failed with token {leaked_secret}"
        )
        with mock.patch.dict(
            os.sys.modules,
            {"twilio": mock.MagicMock(rest=fake_twilio_rest), "twilio.rest": fake_twilio_rest},
        ):
            result = NotificationService.send_sms("+15550001111", "test message")
        assert result["status"] == "failed"
        # The credential-looking string must be redacted.
        assert leaked_secret not in result["error"]
        assert "[REDACTED]" in result["error"]

    def _install_fake_sendgrid(self):
        """Register fake sendgrid + submodules so `from sendgrid.helpers.mail import Mail` resolves."""
        fake_mail = mock.MagicMock()
        fake_helpers = mock.MagicMock(mail=fake_mail)
        fake_sendgrid = mock.MagicMock(helpers=fake_helpers)
        return fake_sendgrid, {
            "sendgrid": fake_sendgrid,
            "sendgrid.helpers": fake_helpers,
            "sendgrid.helpers.mail": fake_mail,
        }

    def test_successful_email_delivery(self, monkeypatch):
        monkeypatch.setenv("SENDGRID_API_KEY", "SG.fakekeyforunit-test")
        fake_sendgrid, modules = self._install_fake_sendgrid()
        fake_sendgrid.SendGridAPIClient.return_value.send.return_value = mock.Mock(status_code=202)
        with mock.patch.dict(os.sys.modules, modules):
            result = NotificationService.send_email("mom@example.com", "SOS Alert", "body")
        assert result["status"] == "sent"

    def test_failed_email_delivery_reports_failure(self, monkeypatch):
        monkeypatch.setenv("SENDGRID_API_KEY", "SG.fakekeyforunit-test")
        fake_sendgrid, modules = self._install_fake_sendgrid()
        fake_sendgrid.SendGridAPIClient.return_value.send.side_effect = Exception("sendgrid down")
        with mock.patch.dict(os.sys.modules, modules):
            result = NotificationService.send_email("mom@example.com", "SOS Alert", "body")
        assert result["status"] == "failed"


# ---------------------------------------------------------------------------
# POST /api/safety/sos end-to-end (providers mocked)
# ---------------------------------------------------------------------------

class TestSOSEndpoint:
    def test_sos_creates_incident_and_delivers_to_contacts(self, client):
        headers = register_and_login(client)
        contact = add_contact(client, headers, name="Mom", phone="+15550001111")

        with mock.patch.object(NotificationService, "send_sms", return_value={"status": "sent", "sid": "SM1"}) as sms:
            resp = client.post("/api/safety/sos", headers=headers, json=SOS_PAYLOAD)

        assert resp.status_code == 201, resp.text
        body = resp.json()
        assert body["id"]
        assert body["status"] == "ACTIVE"
        assert body["no_contacts_configured"] is False
        assert len(body["notifications"]) == 1
        delivery = body["notifications"][0]
        assert delivery["emergency_contact_id"] == contact["id"]
        assert delivery["channel"] == "SMS"
        assert delivery["recipient"] == "+15550001111"
        assert delivery["status"] == "SENT"
        assert delivery["sent_at"] is not None
        sms.assert_called_once()

        # Delivery must be persisted truthfully.
        from app.models.notification import Notification, NotificationStatus

        with TestingSessionLocal() as db:
            row = db.query(Notification).filter(Notification.id == delivery["id"]).first()
            assert row is not None
            assert row.status == NotificationStatus.SENT
            assert row.emergency_contact_id == contact["id"]

    def test_email_channel_used_when_contact_has_email(self, client):
        headers = register_and_login(client)
        add_contact(
            client,
            headers,
            name="Dad",
            phone="+15550002222",
            email="dad@example.com",
        )

        with mock.patch.object(
            NotificationService, "send_sms", return_value={"status": "sent", "sid": "SM2"}
        ), mock.patch.object(
            NotificationService, "send_email", return_value={"status": "sent"}
        ) as email:
            resp = client.post("/api/safety/sos", headers=headers, json=SOS_PAYLOAD)

        assert resp.status_code == 201, resp.text
        deliveries = resp.json()["notifications"]
        channels = {d["channel"] for d in deliveries}
        assert channels == {"SMS", "EMAIL"}
        email.assert_called_once()

    def test_user_own_email_not_notified_unless_contact(self, client):
        headers = register_and_login(client)
        add_contact(client, headers, name="Mom", phone="+15550003333")

        with mock.patch.object(
            NotificationService, "send_sms", return_value={"status": "sent", "sid": "SM3"}
        ):
            resp = client.post("/api/safety/sos", headers=headers, json=SOS_PAYLOAD)

        recipients = [d["recipient"] for d in resp.json()["notifications"]]
        assert all(r.startswith("+15") for r in recipients), recipients

    def test_no_contacts_returns_clear_response(self, client):
        headers = register_and_login(client)

        with mock.patch.object(NotificationService, "send_sms") as sms, mock.patch.object(
            NotificationService, "send_email"
        ) as email:
            resp = client.post("/api/safety/sos", headers=headers, json=SOS_PAYLOAD)

        assert resp.status_code == 201, resp.text
        body = resp.json()
        assert body["no_contacts_configured"] is True
        assert body["notifications"] == []
        sms.assert_not_called()
        email.assert_not_called()

    def test_one_failed_contact_does_not_block_others(self, client):
        headers = register_and_login(client)
        add_contact(client, headers, name="First", phone="+15550004444")
        add_contact(client, headers, name="Second", phone="+15550005555")

        responses = {
            "+15550004444": {"status": "failed", "error": "provider outage"},
            "+15550005555": {"status": "sent", "sid": "SM4"},
        }

        def fake_send_sms(to_number, message):
            return responses[to_number]

        with mock.patch.object(NotificationService, "send_sms", side_effect=fake_send_sms):
            resp = client.post("/api/safety/sos", headers=headers, json=SOS_PAYLOAD)

        assert resp.status_code == 201, resp.text
        deliveries = {d["recipient"]: d for d in resp.json()["notifications"]}
        assert len(deliveries) == 2
        assert deliveries["+15550004444"]["status"] == "FAILED"
        assert deliveries["+15550004444"]["failure_reason"] == "provider outage"
        assert deliveries["+15550005555"]["status"] == "SENT"

    def test_delivery_exception_is_contained_per_contact(self, client):
        headers = register_and_login(client)
        add_contact(client, headers, name="Boom", phone="+15550006666")
        add_contact(client, headers, name="Fine", phone="+15550007777")

        def flaky_send_sms(to_number, message):
            if to_number == "+15550006666":
                raise RuntimeError("network exploded")
            return {"status": "sent", "sid": "SM5"}

        with mock.patch.object(NotificationService, "send_sms", side_effect=flaky_send_sms):
            resp = client.post("/api/safety/sos", headers=headers, json=SOS_PAYLOAD)

        assert resp.status_code == 201, resp.text
        deliveries = {d["recipient"]: d for d in resp.json()["notifications"]}
        assert deliveries["+15550006666"]["status"] == "FAILED"
        assert "network exploded" in deliveries["+15550006666"]["failure_reason"]
        assert deliveries["+15550007777"]["status"] == "SENT"

    def test_missing_credentials_store_failed_not_sent(self, client):
        """No env credentials -> provider reports failure -> DB stores FAILED."""
        headers = register_and_login(client)
        add_contact(client, headers, name="Mom", phone="+15550008888")

        # No mocking: NotificationService hits the missing-credential branch.
        resp = client.post("/api/safety/sos", headers=headers, json=SOS_PAYLOAD)

        assert resp.status_code == 201, resp.text
        deliveries = resp.json()["notifications"]
        assert len(deliveries) == 1
        assert deliveries[0]["status"] == "FAILED"
        assert "not configured" in deliveries[0]["failure_reason"]

        from app.models.notification import Notification, NotificationStatus

        with TestingSessionLocal() as db:
            row = db.query(Notification).filter(Notification.id == deliveries[0]["id"]).first()
            assert row.status == NotificationStatus.FAILED
            assert row.failure_reason

    def test_inactive_contacts_are_skipped(self, client):
        headers = register_and_login(client)
        add_contact(client, headers, name="Active", phone="+15550009999")

        # Deactivate the only contact directly in the isolated test DB.
        from app.models.emergency_contact import EmergencyContact

        with TestingSessionLocal() as db:
            contact = db.query(EmergencyContact).filter(EmergencyContact.name == "Active").first()
            contact.is_active = False
            db.commit()

        with mock.patch.object(NotificationService, "send_sms") as sms:
            resp = client.post("/api/safety/sos", headers=headers, json=SOS_PAYLOAD)

        assert resp.status_code == 201, resp.text
        assert resp.json()["no_contacts_configured"] is True
        sms.assert_not_called()


# ---------------------------------------------------------------------------
# GET /api/safety/notifications exposes new truthful fields
# ---------------------------------------------------------------------------

class TestNotificationsEndpoint:
    def test_notifications_list_includes_delivery_metadata(self, client):
        headers = register_and_login(client)
        add_contact(client, headers, name="Mom", phone="+15550010000", email="mom@example.com")

        with mock.patch.object(
            NotificationService, "send_sms", return_value={"status": "failed", "error": "outage"}
        ), mock.patch.object(
            NotificationService, "send_email", return_value={"status": "sent"}
        ):
            sos_resp = client.post("/api/safety/sos", headers=headers, json=SOS_PAYLOAD)
        assert sos_resp.status_code == 201

        resp = client.get("/api/safety/notifications", headers=headers)
        assert resp.status_code == 200
        items = resp.json()
        assert len(items) >= 2
        by_channel = {item["channel"]: item for item in items}
        assert by_channel["SMS"]["status"] == "FAILED"
        assert by_channel["SMS"]["failure_reason"] == "outage"
        assert by_channel["EMAIL"]["status"] == "SENT"
        assert by_channel["EMAIL"]["emergency_contact_id"]
        assert by_channel["EMAIL"]["sos_incident_id"]


# ---------------------------------------------------------------------------
# Redaction helper
# ---------------------------------------------------------------------------

def test_redact_message_scrubs_secret_like_strings():
    dirty = "auth failed for skLive1234567890abcdef and eyJhbGciOi.token.part"
    clean = ns_module.redact_message(dirty)
    assert "skLive1234567890abcdef" not in clean
    assert "eyJhbGciOi" not in clean