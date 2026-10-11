"""
Webhook service: HMAC signature verification and hand-off to the callback queue
"""

import hashlib
import hmac
import json
import logging
from typing import Any

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from ..config import settings

logger = logging.getLogger(__name__)


class WebhookService:
    """Service for webhook operations"""

    def verify_webhook_signature(
        self, payload: str, signature: str, secret: str
    ) -> bool:
        """Verify the "sha256=<hexdigest>" HMAC signature of a webhook payload"""
        expected_signature = hmac.new(
            secret.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256
        ).hexdigest()

        try:
            return hmac.compare_digest(f"sha256={expected_signature}", signature)
        except TypeError:
            # compare_digest rejects str arguments with non-ASCII characters
            logger.warning("Webhook signature contains non-ASCII characters")
            return False

    async def process_webhook(self, payload: dict[str, Any]) -> bool:
        """Send a verified webhook to the callback queue for processing"""
        if not settings.callback_queue_url:
            logger.error("CALLBACK_QUEUE_URL is not configured; webhook not queued")
            return False

        try:
            sqs_client = boto3.client(
                "sqs",
                region_name=settings.aws_region,
                endpoint_url=settings.aws_endpoint_url,
            )
            sqs_client.send_message(
                QueueUrl=settings.callback_queue_url,
                MessageBody=json.dumps(payload),
                MessageAttributes={
                    "eventType": {
                        "StringValue": str(payload.get("event_type") or "unknown"),
                        "DataType": "String",
                    }
                },
            )

        except (BotoCoreError, ClientError) as e:
            logger.error(f"Failed to queue webhook: {e}")
            return False

        logger.info(f"Queued webhook for doc_id: {payload.get('doc_id')}")
        return True


webhook_service = WebhookService()
