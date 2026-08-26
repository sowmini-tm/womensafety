from __future__ import annotations

import os
import re
from typing import Any

_SECRET_PATTERN = re.compile(
    r"(?i)(sk[a-z0-9_\-]{10,}|AC[a-f0-9]{32}|[a-f0-9]{32}|Bearer\s+\S+|eyJ[\w\-\.]+)"
)


def _redact(text: str) -> str:
    """Strip anything that looks like a credential out of provider error strings."""
    if not text:
        return text
    return _SECRET_PATTERN.sub("[REDACTED]", text)


def _redact_result(result: dict[str, Any]) -> dict[str, Any]:
    if result.get("error"):
        result["error"] = _redact(str(result["error"]))
    return result


def redact_message(text: str) -> str:
    """Public helper so callers can scrub credentials from unexpected errors."""
    return _redact(text)


class NotificationService:
    """Outbound notification facade.

    Delivery is truthful: when provider credentials are not configured the
    attempt is reported as ``failed`` with a configuration reason instead of
    being silently "simulated". Callers must never report SENT unless a
    provider actually accepted the message.
    """

    @staticmethod
    def send_sms(to_number: str, message: str) -> dict[str, Any]:
        account_sid = os.getenv("TWILIO_ACCOUNT_SID")
        auth_token = os.getenv("TWILIO_AUTH_TOKEN")
        from_number = os.getenv("TWILIO_FROM_NUMBER")

        if not account_sid or not auth_token or not from_number:
            return _redact_result({
                "status": "failed",
                "provider": "twilio",
                "error": "SMS provider not configured (missing Twilio credentials)",
                "to": to_number,
                "message": message,
            })

        try:
            from twilio.rest import Client

            client = Client(account_sid, auth_token)
            sms = client.messages.create(body=message, from_=from_number, to=to_number)
            return {
                "status": "sent",
                "sid": sms.sid,
                "provider": "twilio",
            }
        except Exception as exc:  # pragma: no cover - exercised via mocks in tests
            return _redact_result({
                "status": "failed",
                "provider": "twilio",
                "error": str(exc),
            })

    @staticmethod
    def send_email(to_email: str, subject: str, body: str) -> dict[str, Any]:
        api_key = os.getenv("SENDGRID_API_KEY")
        if not api_key:
            return _redact_result({
                "status": "failed",
                "provider": "sendgrid",
                "error": "Email provider not configured (missing SendGrid credentials)",
                "to": to_email,
                "subject": subject,
            })

        try:
            import sendgrid
            from sendgrid.helpers.mail import Mail

            sg = sendgrid.SendGridAPIClient(api_key)
            message = Mail(
                from_email=os.getenv("SENDGRID_FROM_EMAIL", "noreply@example.com"),
                to_emails=to_email,
                subject=subject,
                html_content=f"<p>{body}</p>",
            )
            response = sg.send(message)
            return {
                "status": "sent" if response.status_code < 400 else "failed",
                "provider": "sendgrid",
                "status_code": response.status_code,
            }
        except Exception as exc:  # pragma: no cover - exercised via mocks in tests
            return _redact_result({
                "status": "failed",
                "provider": "sendgrid",
                "error": str(exc),
            })
