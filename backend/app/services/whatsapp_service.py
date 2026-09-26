"""
app/services/whatsapp_service.py

WhatsApp Business API delivery service via Twilio Sandbox.
Handles sending both plain-language text alerts and spoken voice notes to farmers.
"""
from __future__ import annotations

import os
import logging

logger = logging.getLogger("ubuntu_terra.whatsapp")


def send_whatsapp_alert_and_voice(
    to_number: str | None = None,
    message_text: str = "",
    audio_url: str | None = None,
) -> dict:
    """
    Sends a WhatsApp text message and optional audio voice note via Twilio.
    Falls back gracefully to simulated sandbox delivery if credentials are not configured.
    """
    account_sid = os.environ.get("TWILIO_ACCOUNT_SID")
    auth_token = os.environ.get("TWILIO_AUTH_TOKEN")
    from_whatsapp = os.environ.get("TWILIO_WHATSAPP_NUMBER", "whatsapp:+14155238886")
    target_number = to_number or os.environ.get("RECIPIENT_WHATSAPP_NUMBER", "whatsapp:+27821234567")

    if not target_number.startswith("whatsapp:"):
        target_number = f"whatsapp:{target_number}"

    # If real Twilio credentials are configured, execute live WhatsApp API call
    if account_sid and auth_token:
        try:
            from twilio.rest import Client

            client = Client(account_sid, auth_token)

            # 1. Send text message
            msg = client.messages.create(
                from_=from_whatsapp,
                body=message_text,
                to=target_number,
            )

            # 2. Send voice note if audio URL is provided
            voice_sid = None
            if audio_url:
                voice_msg = client.messages.create(
                    from_=from_whatsapp,
                    body="🎙️ Spoken voice note:",
                    media_url=[audio_url],
                    to=target_number,
                )
                voice_sid = voice_msg.sid

            return {
                "status": "sent",
                "sid": msg.sid,
                "voice_sid": voice_sid,
                "to": target_number,
                "text": message_text,
                "audio_url": audio_url,
            }
        except Exception as e:
            logger.warning(f"Twilio WhatsApp dispatch error: {e}")

    # Fallback / Sandbox Simulated Delivery
    return {
        "status": "simulated",
        "to": target_number,
        "text": message_text,
        "audio_url": audio_url,
        "note": "WhatsApp sandbox delivery recorded (configure TWILIO_ACCOUNT_SID & TWILIO_AUTH_TOKEN for live SMS/WA)",
    }
