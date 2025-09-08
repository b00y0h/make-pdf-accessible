"""SQS client utilities with message handling and batch processing."""

import json
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import boto3
from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.utilities.data_classes import SQSEvent, SQSRecord
from botocore.exceptions import ClientError

from pdf_worker.core.config import config
from pdf_worker.core.exceptions import SQSError, WorkerConfigError

logger = Logger()
tracer = Tracer()


@dataclass
class SQSMessage:
    """Structured SQS message representation."""
    message_id: str
    receipt_handle: str
    body: dict[str, Any]
    attributes: dict[str, Any]
    message_attributes: dict[str, Any]
    md5_of_body: str

    @classmethod
    def from_sqs_record(cls, record: SQSRecord) -> 'SQSMessage':
        """Create SQSMessage from SQS event record."""
        try:
            # Parse JSON body
            body = json.loads(record.body) if isinstance(record.body, str) else record.body
        except json.JSONDecodeError:
            # Fallback to raw body if not JSON
            body = {"raw_body": record.body}

        return cls(
            message_id=record.message_id,
            receipt_handle=record.receipt_handle,
            body=body,
            attributes=record.attributes,
            message_attributes=record.message_attributes,
            md5_of_body=record.md5_of_body
        )


class SQSClient:
    """Enhanced SQS client with message handling utilities."""

    def __init__(self, region_name: str | None = None) -> None:
        """Initialize SQS client.
        
        Args:
            region_name: AWS region name. Defaults to config.aws_region.
        """
        try:
            self._client = boto3.client('sqs', region_name=region_name or config.aws_region)
        except Exception as e:
            raise WorkerConfigError(f"Failed to initialize SQS client: {e}")

        logger.info(f"Initialized SQS client for region: {region_name or config.aws_region}")

    @tracer.capture_method
    def send_message(
        self,
        queue_url: str,
        message_body: dict[str, Any],
        delay_seconds: int = 0,
        message_attributes: dict[str, Any] | None = None,
        message_group_id: str | None = None,
        message_deduplication_id: str | None = None
    ) -> dict[str, Any]:
        """Send message to SQS queue.
        
        Args:
            queue_url: SQS queue URL
            message_body: Message payload as dictionary
            delay_seconds: Delay before message becomes available
            message_attributes: SQS message attributes
            message_group_id: Message group ID for FIFO queues
            message_deduplication_id: Deduplication ID for FIFO queues
            
        Returns:
            SQS send message response
            
        Raises:
            SQSError: If send operation fails
        """
        try:
            # Add metadata to message body
            enhanced_body = {
                **message_body,
                '_metadata': {
                    'sent_at': datetime.utcnow().isoformat(),
                    'sent_by': 'pdf-accessibility-worker'
                }
            }

            send_kwargs = {
                'QueueUrl': queue_url,
                'MessageBody': json.dumps(enhanced_body, ensure_ascii=False)
            }

            if delay_seconds > 0:
                send_kwargs['DelaySeconds'] = delay_seconds

            if message_attributes:
                send_kwargs['MessageAttributes'] = self._format_message_attributes(
                    message_attributes
                )

            # FIFO queue specific parameters
            if message_group_id:
                send_kwargs['MessageGroupId'] = message_group_id

            if message_deduplication_id:
                send_kwargs['MessageDeduplicationId'] = message_deduplication_id

            response = self._client.send_message(**send_kwargs)

            logger.info(f"Successfully sent message to queue: {queue_url}")
            logger.debug(f"Message ID: {response.get('MessageId')}")

            return response

        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            raise SQSError(
                f"Failed to send message to SQS: {error_code}",
                queue_url=queue_url
            ) from e

    @tracer.capture_method
    def send_batch_messages(
        self,
        queue_url: str,
        messages: list[dict[str, Any]],
        message_group_id: str | None = None
    ) -> dict[str, Any]:
        """Send multiple messages to SQS queue in batch.
        
        Args:
            queue_url: SQS queue URL
            messages: List of message dictionaries
            message_group_id: Message group ID for FIFO queues
            
        Returns:
            SQS batch send response
            
        Raises:
            SQSError: If batch send operation fails
        """
        try:
            # Format messages for batch send
            entries = []
            for i, message in enumerate(messages):
                entry = {
                    'Id': str(i),
                    'MessageBody': json.dumps({
                        **message,
                        '_metadata': {
                            'sent_at': datetime.utcnow().isoformat(),
                            'sent_by': 'pdf-accessibility-worker',
                            'batch_index': i
                        }
                    }, ensure_ascii=False)
                }

                if message_group_id:
                    entry['MessageGroupId'] = message_group_id
                    # Use message index as dedup ID for batch
                    entry['MessageDeduplicationId'] = f"{message_group_id}-{i}-{int(datetime.utcnow().timestamp())}"

                entries.append(entry)

            response = self._client.send_message_batch(
                QueueUrl=queue_url,
                Entries=entries
            )

            successful_count = len(response.get('Successful', []))
            failed_count = len(response.get('Failed', []))

            logger.info(f"Batch send completed: {successful_count} successful, {failed_count} failed")

            if failed_count > 0:
                logger.warning(f"Failed messages: {response.get('Failed', [])}")

            return response

        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            raise SQSError(
                f"Failed to send batch messages to SQS: {error_code}",
                queue_url=queue_url
            ) from e

    @tracer.capture_method
    def delete_message(self, queue_url: str, receipt_handle: str) -> None:
        """Delete message from SQS queue.
        
        Args:
            queue_url: SQS queue URL
            receipt_handle: Message receipt handle
            
        Raises:
            SQSError: If delete operation fails
        """
        try:
            self._client.delete_message(
                QueueUrl=queue_url,
                ReceiptHandle=receipt_handle
            )

            logger.debug(f"Successfully deleted message from queue: {queue_url}")

        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')

            # Don't raise error for receipt handle not found (message already deleted)
            if error_code != 'ReceiptHandleIsInvalid':
                raise SQSError(
                    f"Failed to delete message from SQS: {error_code}",
                    queue_url=queue_url
                ) from e

    @tracer.capture_method
    def delete_batch_messages(
        self,
        queue_url: str,
        receipt_handles: list[str]
    ) -> dict[str, Any]:
        """Delete multiple messages from SQS queue in batch.
        
        Args:
            queue_url: SQS queue URL
            receipt_handles: List of message receipt handles
            
        Returns:
            SQS batch delete response
            
        Raises:
            SQSError: If batch delete operation fails
        """
        try:
            entries = [
                {'Id': str(i), 'ReceiptHandle': handle}
                for i, handle in enumerate(receipt_handles)
            ]

            response = self._client.delete_message_batch(
                QueueUrl=queue_url,
                Entries=entries
            )

            successful_count = len(response.get('Successful', []))
            failed_count = len(response.get('Failed', []))

            logger.info(f"Batch delete completed: {successful_count} successful, {failed_count} failed")

            return response

        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            raise SQSError(
                f"Failed to delete batch messages from SQS: {error_code}",
                queue_url=queue_url
            ) from e

    @tracer.capture_method
    def get_queue_attributes(self, queue_url: str) -> dict[str, Any]:
        """Get SQS queue attributes.
        
        Args:
            queue_url: SQS queue URL
            
        Returns:
            Queue attributes dictionary
            
        Raises:
            SQSError: If get attributes operation fails
        """
        try:
            response = self._client.get_queue_attributes(
                QueueUrl=queue_url,
                AttributeNames=['All']
            )

            attributes = response.get('Attributes', {})
            logger.debug(f"Retrieved attributes for queue: {queue_url}")

            return attributes

        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            raise SQSError(
                f"Failed to get queue attributes: {error_code}",
                queue_url=queue_url
            ) from e

    @tracer.capture_method
    def change_message_visibility(
        self,
        queue_url: str,
        receipt_handle: str,
        visibility_timeout: int
    ) -> None:
        """Change message visibility timeout.
        
        Args:
            queue_url: SQS queue URL
            receipt_handle: Message receipt handle
            visibility_timeout: New visibility timeout in seconds
            
        Raises:
            SQSError: If visibility change operation fails
        """
        try:
            self._client.change_message_visibility(
                QueueUrl=queue_url,
                ReceiptHandle=receipt_handle,
                VisibilityTimeout=visibility_timeout
            )

            logger.debug(f"Changed message visibility to {visibility_timeout}s")

        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            raise SQSError(
                f"Failed to change message visibility: {error_code}",
                queue_url=queue_url
            ) from e

    def _format_message_attributes(
        self,
        attributes: dict[str, Any]
    ) -> dict[str, dict[str, str]]:
        """Format message attributes for SQS API."""
        formatted = {}

        for key, value in attributes.items():
            if isinstance(value, str):
                formatted[key] = {'StringValue': value, 'DataType': 'String'}
            elif isinstance(value, (int, float)):
                formatted[key] = {'StringValue': str(value), 'DataType': 'Number'}
            elif isinstance(value, bytes):
                formatted[key] = {'BinaryValue': value, 'DataType': 'Binary'}
            else:
                # Convert other types to JSON string
                formatted[key] = {
                    'StringValue': json.dumps(value),
                    'DataType': 'String'
                }

        return formatted


class SQSMessageProcessor:
    """Utility class for processing SQS messages with error handling."""

    def __init__(self, sqs_client: SQSClient | None = None) -> None:
        """Initialize message processor.
        
        Args:
            sqs_client: SQS client instance. Creates new one if not provided.
        """
        self.sqs_client = sqs_client or SQSClient()

    @tracer.capture_method
    def process_sqs_event(
        self,
        event: SQSEvent,
        message_handler: Callable[[SQSMessage], dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Process SQS event with automatic error handling.
        
        Args:
            event: SQS Lambda event
            message_handler: Function to handle individual messages
            
        Returns:
            List of processing results
        """
        results = []

        for record in event.records:
            try:
                # Convert to structured message
                message = SQSMessage.from_sqs_record(record)

                logger.info(f"Processing message {message.message_id}")

                # Process message
                result = message_handler(message)

                # Mark as successful
                results.append({
                    'message_id': message.message_id,
                    'status': 'success',
                    'result': result
                })

                logger.info(f"Successfully processed message {message.message_id}")

            except Exception as e:
                logger.error(f"Failed to process message {record.message_id}: {e}")

                results.append({
                    'message_id': record.message_id,
                    'status': 'error',
                    'error': str(e)
                })

                # Don't delete failed messages - let them go to DLQ
                continue

        return results

    @tracer.capture_method
    def send_to_dlq(
        self,
        dlq_url: str,
        original_message: SQSMessage,
        error_info: dict[str, Any]
    ) -> None:
        """Send failed message to dead letter queue.
        
        Args:
            dlq_url: Dead letter queue URL
            original_message: Original SQS message that failed
            error_info: Error information
        """
        try:
            dlq_message = {
                **original_message.body,
                '_error_info': {
                    'error_time': datetime.utcnow().isoformat(),
                    'original_message_id': original_message.message_id,
                    'error_details': error_info
                }
            }

            self.sqs_client.send_message(
                queue_url=dlq_url,
                message_body=dlq_message,
                message_attributes={
                    'error_source': 'pdf-accessibility-worker',
                    'original_queue': original_message.attributes.get('source_queue', 'unknown')
                }
            )

            logger.info(f"Sent failed message {original_message.message_id} to DLQ")

        except Exception as e:
            logger.error(f"Failed to send message to DLQ: {e}")

    def create_process_message(
        self,
        doc_id: str,
        step: str,
        input_data: dict[str, Any],
        priority: bool = False
    ) -> dict[str, Any]:
        """Create a standardized process message.
        
        Args:
            doc_id: Document identifier
            step: Processing step name
            input_data: Step-specific input data
            priority: Whether this is high priority
            
        Returns:
            Formatted message dictionary
        """
        return {
            'docId': doc_id,
            'step': step,
            'priority': priority,
            'input': input_data,
            'timestamp': datetime.utcnow().isoformat(),
            'message_version': '1.0'
        }
