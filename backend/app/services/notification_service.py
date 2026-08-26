from __future__ import annotations

import os
from typing import Any


class NotificationService:
    """Lightweight outbound notification facade used for demo and production-ready integration."""

    @staticmethod
    def send_sms(to_number: str, message: str) -> dict[str, Any]:
        account_sid = os.getenv("TWILIO_ACCOUNT_SID")
        auth_token = os.getenv("TWILIO_AUTH_TOKEN")
        from_number = os.getenv("TWILIO_FROM_NUMBER")

        if not account_sid or not auth_token or not from_number:
            return {
                "status": "simulated",
                "to": to_number,
                "message": message,
                "provider": "simulated",
            }

        try:
            from twilio.rest import Client

            client = Client(account_sid, auth_token)
            sms = client.messages.create(body=message, from_=from_number, to=to_number)
            return {
                "status": "sent",
                "sid": sms.sid,
                "provider": "twilio",
            }
        except Exception as exc:  # pragma: no cover
            return {
                "status": "failed",
                "provider": "twilio",
                "error": str(exc),
            }

    @staticmethod
    def send_email(to_email: str, subject: str, body: str) -> dict[str, Any]:
        api_key = os.getenv("SENDGRID_API_KEY")
        if not api_key:
            return {
                "status": "simulated",
                "to": to_email,
                "subject": subject,
                "provider": "simulated",
            }

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
        except Exception as exc:  # pragma: no cover
            return {
                "status": "failed",
                "provider": "sendgrid",
                "error": str(exc),
            }
