"""Unit tests for the webhook service."""

import hashlib
import hmac
from unittest.mock import patch

import pytest
from app.services.webhooks import webhook_service

SECRET = "test-secret-key"
PAYLOAD = '{"event_type": "document.completed"}'
DIGEST = hmac.new(SECRET.encode(), PAYLOAD.encode(), hashlib.sha256).hexdigest()


def test_verify_webhook_signature_accepts_correct_signature():
    """A sha256=<hexdigest> signature made with the secret is valid"""
    assert webhook_service.verify_webhook_signature(PAYLOAD, f"sha256={DIGEST}", SECRET)


def test_verify_webhook_signature_rejects_wrong_signature():
    """A signature made with another secret is invalid"""
    wrong_digest = hmac.new(b"other-secret", PAYLOAD.encode(), hashlib.sha256)

    assert not webhook_service.verify_webhook_signature(
        PAYLOAD, f"sha256={wrong_digest.hexdigest()}", SECRET
    )


def test_verify_webhook_signature_rejects_tampered_payload():
    """A valid signature for a different payload is invalid"""
    assert not webhook_service.verify_webhook_signature(
        PAYLOAD.replace("completed", "failed"), f"sha256={DIGEST}", SECRET
    )


def test_verify_webhook_signature_requires_prefix():
    """A bare hexdigest without the sha256= prefix is invalid"""
    assert not webhook_service.verify_webhook_signature(PAYLOAD, DIGEST, SECRET)


def test_verify_webhook_signature_rejects_non_ascii_signature():
    """A non-ASCII signature is invalid rather than an error"""
    assert not webhook_service.verify_webhook_signature(PAYLOAD, "sha256=é", SECRET)


@pytest.mark.asyncio
async def test_process_webhook_fails_without_callback_queue():
    """Without a callback queue the webhook is not accepted"""
    with patch("app.services.webhooks.settings.callback_queue_url", ""):
        assert not await webhook_service.process_webhook({"doc_id": "doc-123"})
