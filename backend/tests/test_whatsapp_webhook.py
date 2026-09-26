"""
Tests for the Twilio webhook signature check in routers/fields.py.

The webhook is reachable at BOTH /whatsapp/webhook and /api/whatsapp/webhook
(via the aliases in main.py). Signature verification lives inside
fields.whatsapp_webhook so both paths are protected by the same check; the
alias routes are exercised here to prove that.

These tests use the real Twilio RequestValidator rather than monkeypatching it,
so a regression in URL reconstruction is actually caught.
"""
import os

import pytest
from fastapi.testclient import TestClient
from twilio.request_validator import RequestValidator

from app.main import app

client = TestClient(app)

AUTH_TOKEN = "test-auth-token"
WEBHOOK_PATHS = ["/whatsapp/webhook", "/api/whatsapp/webhook"]


@pytest.fixture(autouse=True)
def twilio_token(monkeypatch):
    monkeypatch.setenv("TWILIO_AUTH_TOKEN", AUTH_TOKEN)


def _sign(url, params, token=AUTH_TOKEN):
    return RequestValidator(token).compute_signature(url, params)


def test_webhook_without_signature_header_is_rejected():
    """No X-Twilio-Signature at all must 403 and must not process the message."""
    for path in WEBHOOK_PATHS:
        response = client.post(path, data={"Body": "YES", "From": "whatsapp:+27820000000"})
        assert response.status_code == 403, path
        assert response.json()["detail"] == "Invalid Twilio signature", path
        # A rejected message must not produce a TwiML reply.
        assert "<Response>" not in response.text


def test_webhook_with_invalid_signature_is_rejected():
    for path in WEBHOOK_PATHS:
        response = client.post(
            path,
            headers={"x-twilio-signature": "invalid_signature123"},
            data={"Body": "YES", "From": "whatsapp:+27820000000"},
        )
        assert response.status_code == 403, path
        assert "<Response>" not in response.text


def test_webhook_signature_from_a_different_token_is_rejected():
    """A signature computed with the wrong auth token must not be accepted."""
    params = {"Body": "YES", "From": "whatsapp:+27820000000"}
    bad_sig = _sign("http://testserver/api/whatsapp/webhook", params, token="some-other-token")
    response = client.post(
        "/api/whatsapp/webhook",
        headers={"x-twilio-signature": bad_sig},
        data=params,
    )
    assert response.status_code == 403


def test_webhook_signature_for_a_different_url_is_rejected():
    """A signature valid for one path must not validate on another path."""
    params = {"Body": "YES", "From": "whatsapp:+27820000000"}
    sig = _sign("http://testserver/whatsapp/webhook", params)
    response = client.post(
        "/api/whatsapp/webhook",
        headers={"x-twilio-signature": sig},
        data=params,
    )
    assert response.status_code == 403


def test_webhook_accepts_a_correctly_signed_request():
    """Positive control: proves the URL the server rebuilds is the one signed."""
    params = {"Body": "YES", "From": "whatsapp:+27820000000"}
    sig = _sign("http://testserver/api/whatsapp/webhook", params)
    response = client.post(
        "/api/whatsapp/webhook",
        headers={"x-twilio-signature": sig},
        data=params,
    )
    assert response.status_code == 200
    assert "Siyabonga" in response.text or "Dankie" in response.text


def test_webhook_honours_x_forwarded_proto_when_rebuilding_url():
    """
    Behind a TLS-terminating proxy the app sees http:// but Twilio signed
    https://, so X-Forwarded-Proto must be used. A signature made over the
    https URL must therefore be accepted.
    """
    params = {"Body": "YES", "From": "whatsapp:+27820000000"}
    sig = _sign("https://testserver/api/whatsapp/webhook", params)
    response = client.post(
        "/api/whatsapp/webhook",
        headers={"x-twilio-signature": sig, "x-forwarded-proto": "https"},
        data=params,
    )
    assert response.status_code == 200


def test_webhook_json_body_cannot_bypass_signature_validation():
    """
    Regression guard: body parsing used to sit inside a try/except that fell
    back to JSON, so a payload that failed form parsing skipped validation
    entirely and still got a 200 TwiML reply. Validation must happen first.
    """
    response = client.post(
        "/api/whatsapp/webhook",
        headers={"Content-Type": "application/json"},
        json={"Body": "YES", "From": "whatsapp:+27820000000"},
    )
    assert response.status_code == 403
    assert "<Response>" not in response.text


def test_webhook_fails_closed_when_auth_token_is_not_configured(monkeypatch):
    """
    With no token configured we cannot verify anything, so the message must not
    be processed. Surfaced as a 500 to distinguish misconfiguration from a bad
    signature coming from Twilio.
    """
    monkeypatch.setenv("TWILIO_AUTH_TOKEN", "")
    response = client.post("/api/whatsapp/webhook", data={"Body": "YES"})
    assert response.status_code == 500
    assert "<Response>" not in response.text
