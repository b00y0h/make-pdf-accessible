import os
from unittest.mock import Mock, patch

import pytest


@pytest.fixture(autouse=True)
def setup_test_environment():
    """Setup test environment variables"""
    test_env = {
        "AWS_DEFAULT_REGION": "us-east-1",
        "AWS_ACCESS_KEY_ID": "testing",
        "AWS_SECRET_ACCESS_KEY": "testing",
        "AWS_SECURITY_TOKEN": "testing",
        "AWS_SESSION_TOKEN": "testing",
        "ENVIRONMENT": "test",
        "LOG_LEVEL": "DEBUG",
        # OCR-specific environment variables
        "TEXTRACT_REGION": "us-east-1",
        "SOURCE_BUCKET": "test-source-bucket",
        "DESTINATION_BUCKET": "test-destination-bucket",
        "RESULTS_QUEUE_URL": "https://sqs.us-east-1.amazonaws.com/123456789/test-results"
    }

    with patch.dict(os.environ, test_env):
        yield

@pytest.fixture
def mock_textract_client():
    """Mock Textract client"""
    with patch('boto3.client') as mock_boto:
        mock_client = Mock()
        mock_boto.return_value = mock_client

        # Mock successful text detection
        mock_client.detect_document_text.return_value = {
            'Blocks': [
                {
                    'BlockType': 'PAGE',
                    'Id': 'page-1',
                    'Confidence': 99.0
                },
                {
                    'BlockType': 'LINE',
                    'Id': 'line-1',
                    'Text': 'Sample extracted text line 1',
                    'Confidence': 95.5,
                    'Geometry': {
                        'BoundingBox': {
                            'Width': 0.5,
                            'Height': 0.02,
                            'Left': 0.1,
                            'Top': 0.1
                        }
                    }
                },
                {
                    'BlockType': 'LINE',
                    'Id': 'line-2',
                    'Text': 'Sample extracted text line 2',
                    'Confidence': 97.2,
                    'Geometry': {
                        'BoundingBox': {
                            'Width': 0.6,
                            'Height': 0.02,
                            'Left': 0.1,
                            'Top': 0.15
                        }
                    }
                },
                {
                    'BlockType': 'WORD',
                    'Id': 'word-1',
                    'Text': 'Sample',
                    'Confidence': 95.5
                }
            ]
        }

        # Mock async text detection
        mock_client.start_document_text_detection.return_value = {
            'JobId': 'test-job-123'
        }

        mock_client.get_document_text_detection.return_value = {
            'JobStatus': 'SUCCEEDED',
            'Blocks': mock_client.detect_document_text.return_value['Blocks']
        }

        yield mock_client

@pytest.fixture
def mock_s3_client():
    """Mock S3 client"""
    with patch('boto3.client') as mock_boto:
        mock_client = Mock()
        mock_boto.return_value = mock_client

        # Mock S3 operations
        mock_client.get_object.return_value = {
            'Body': Mock(),
            'ContentType': 'application/pdf',
            'ContentLength': 1024
        }

        mock_client.put_object.return_value = {
            'ETag': '"test-etag"'
        }

        mock_client.head_object.return_value = {
            'ContentType': 'application/pdf',
            'ContentLength': 1024,
            'LastModified': '2023-01-01T00:00:00Z'
        }

        yield mock_client

@pytest.fixture
def sample_s3_event():
    """Sample S3 event for Lambda testing"""
    return {
        "Records": [
            {
                "eventVersion": "2.1",
                "eventSource": "aws:s3",
                "awsRegion": "us-east-1",
                "eventTime": "2023-01-01T00:00:00.000Z",
                "eventName": "ObjectCreated:Put",
                "userIdentity": {
                    "principalId": "test-principal"
                },
                "requestParameters": {
                    "sourceIPAddress": "127.0.0.1"
                },
                "responseElements": {
                    "x-amz-request-id": "test-request-id"
                },
                "s3": {
                    "s3SchemaVersion": "1.0",
                    "configurationId": "test-config",
                    "bucket": {
                        "name": "test-source-bucket",
                        "ownerIdentity": {
                            "principalId": "test-owner"
                        },
                        "arn": "arn:aws:s3:::test-source-bucket"
                    },
                    "object": {
                        "key": "documents/test-document.pdf",
                        "size": 1024,
                        "eTag": "test-etag",
                        "sequencer": "test-sequencer"
                    }
                }
            }
        ]
    }

@pytest.fixture
def lambda_context():
    """Mock Lambda context"""
    context = Mock()
    context.aws_request_id = "test-request-id"
    context.log_group_name = "/aws/lambda/test-function"
    context.log_stream_name = "2023/01/01/test-stream"
    context.function_name = "test-ocr-function"
    context.function_version = "1"
    context.invoked_function_arn = "arn:aws:lambda:us-east-1:123456789:function:test-ocr-function"
    context.memory_limit_in_mb = 512
    context.get_remaining_time_in_millis = lambda: 30000
    return context

@pytest.fixture
def mock_logger():
    """Mock logger for testing"""
    with patch('logging.getLogger') as mock_get_logger:
        mock_logger_instance = Mock()
        mock_get_logger.return_value = mock_logger_instance
        yield mock_logger_instance
