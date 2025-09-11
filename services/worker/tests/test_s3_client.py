"""Tests for S3 client utilities."""

from unittest.mock import MagicMock, patch

import boto3
import pytest
from botocore.exceptions import ClientError
from moto import mock_s3

from pdf_worker.aws.s3 import S3Client
from pdf_worker.core.exceptions import S3Error


class TestS3Client:
    """Test cases for S3Client."""

    @pytest.fixture
    def s3_client(self):
        """Create S3Client instance for testing."""
        with mock_s3():
            return S3Client()

    @pytest.fixture
    def mock_s3_setup(self):
        """Set up mock S3 environment."""
        with mock_s3():
            s3 = boto3.client("s3", region_name="us-east-1")
            s3.create_bucket(Bucket="test-bucket")
            yield s3

    def test_upload_bytes_success(self, s3_client, mock_s3_setup):
        """Test successful bytes upload."""
        test_data = b"test content"
        bucket = "test-bucket"
        key = "test-file.txt"

        result = s3_client.upload_bytes(
            data=test_data, bucket=bucket, key=key, content_type="text/plain"
        )

        assert result == f"s3://{bucket}/{key}"

        # Verify content was uploaded
        downloaded = s3_client.download_bytes(bucket, key)
        assert downloaded == test_data

    def test_upload_json_success(self, s3_client, mock_s3_setup):
        """Test successful JSON upload."""
        test_data = {"key": "value", "number": 123}
        bucket = "test-bucket"
        key = "test-data.json"

        result = s3_client.upload_json(data=test_data, bucket=bucket, key=key)

        assert result == f"s3://{bucket}/{key}"

        # Verify JSON content
        downloaded = s3_client.download_json(bucket, key)
        assert downloaded == test_data

    def test_download_json_parsing_error(self, s3_client, mock_s3_setup):
        """Test JSON download with parsing error."""
        bucket = "test-bucket"
        key = "invalid.json"

        # Upload invalid JSON
        s3_client.upload_bytes(data=b"invalid json content", bucket=bucket, key=key)

        with pytest.raises(S3Error, match="Failed to parse JSON"):
            s3_client.download_json(bucket, key)

    def test_object_exists_true(self, s3_client, mock_s3_setup):
        """Test object exists check returns True."""
        bucket = "test-bucket"
        key = "existing-file.txt"

        s3_client.upload_bytes(b"content", bucket, key)

        assert s3_client.object_exists(bucket, key) is True

    def test_object_exists_false(self, s3_client, mock_s3_setup):
        """Test object exists check returns False."""
        bucket = "test-bucket"
        key = "non-existent-file.txt"

        assert s3_client.object_exists(bucket, key) is False

    def test_get_object_metadata(self, s3_client, mock_s3_setup):
        """Test getting object metadata."""
        bucket = "test-bucket"
        key = "metadata-test.txt"
        content = b"test content"

        s3_client.upload_bytes(
            data=content,
            bucket=bucket,
            key=key,
            content_type="text/plain",
            metadata={"test-key": "test-value"},
        )

        metadata = s3_client.get_object_metadata(bucket, key)

        assert metadata["size"] == len(content)
        assert metadata["content_type"] == "text/plain"
        assert metadata["metadata"]["test-key"] == "test-value"

    def test_copy_object(self, s3_client, mock_s3_setup):
        """Test copying S3 object."""
        source_bucket = "test-bucket"
        source_key = "source.txt"
        dest_bucket = "test-bucket"
        dest_key = "destination.txt"
        content = b"copy test content"

        # Upload source file
        s3_client.upload_bytes(content, source_bucket, source_key)

        # Copy file
        result = s3_client.copy_object(
            source_bucket=source_bucket,
            source_key=source_key,
            dest_bucket=dest_bucket,
            dest_key=dest_key,
        )

        assert result == f"s3://{dest_bucket}/{dest_key}"

        # Verify copied content
        copied_content = s3_client.download_bytes(dest_bucket, dest_key)
        assert copied_content == content

    def test_list_objects(self, s3_client, mock_s3_setup):
        """Test listing objects with prefix."""
        bucket = "test-bucket"

        # Upload multiple files
        files = ["prefix/file1.txt", "prefix/file2.txt", "other/file3.txt"]
        for file_key in files:
            s3_client.upload_bytes(b"content", bucket, file_key)

        # List with prefix
        objects = s3_client.list_objects(bucket, prefix="prefix/")

        assert len(objects) == 2
        object_keys = [obj["key"] for obj in objects]
        assert "prefix/file1.txt" in object_keys
        assert "prefix/file2.txt" in object_keys
        assert "other/file3.txt" not in object_keys

    def test_delete_object(self, s3_client, mock_s3_setup):
        """Test deleting S3 object."""
        bucket = "test-bucket"
        key = "delete-me.txt"

        # Upload file
        s3_client.upload_bytes(b"content", bucket, key)
        assert s3_client.object_exists(bucket, key) is True

        # Delete file
        s3_client.delete_object(bucket, key)
        assert s3_client.object_exists(bucket, key) is False

    def test_generate_presigned_url(self, s3_client, mock_s3_setup):
        """Test generating presigned URL."""
        bucket = "test-bucket"
        key = "presigned-test.txt"

        # Upload file
        s3_client.upload_bytes(b"content", bucket, key)

        # Generate presigned URL
        url = s3_client.generate_presigned_url(bucket, key, expiration=3600)

        assert url is not None
        assert bucket in url
        assert key in url

    @patch("boto3.client")
    def test_client_error_handling(self, mock_boto_client):
        """Test handling of AWS client errors."""
        # Mock client that raises errors
        mock_client = MagicMock()
        mock_client.get_object.side_effect = ClientError(
            error_response={"Error": {"Code": "NoSuchKey"}}, operation_name="GetObject"
        )
        mock_boto_client.return_value = mock_client

        s3_client = S3Client()

        with pytest.raises(S3Error, match="Object not found"):
            s3_client.download_bytes("bucket", "key")

    def test_upload_with_tags(self, s3_client, mock_s3_setup):
        """Test uploading with object tags."""
        bucket = "test-bucket"
        key = "tagged-file.txt"
        content = b"tagged content"
        tags = {"environment": "test", "type": "document"}

        # Note: moto might not fully support tagging, so we just test that it doesn't error
        result = s3_client.upload_bytes(data=content, bucket=bucket, key=key, tags=tags)

        assert result == f"s3://{bucket}/{key}"

    def test_upload_bytes_with_metadata(self, s3_client, mock_s3_setup):
        """Test upload with custom metadata."""
        bucket = "test-bucket"
        key = "metadata-file.txt"
        content = b"content with metadata"
        metadata = {"custom-field": "custom-value", "version": "1.0"}

        s3_client.upload_bytes(data=content, bucket=bucket, key=key, metadata=metadata)

        object_metadata = s3_client.get_object_metadata(bucket, key)

        # Check that our metadata is present along with default metadata
        assert "custom-field" in object_metadata["metadata"]
        assert object_metadata["metadata"]["custom-field"] == "custom-value"
        assert "uploaded_by" in object_metadata["metadata"]
        assert object_metadata["metadata"]["uploaded_by"] == "pdf-accessibility-worker"


@pytest.mark.integration
class TestS3ClientIntegration:
    """Integration tests for S3Client (requires AWS credentials)."""

    @pytest.mark.skip(reason="Requires AWS credentials and actual S3 bucket")
    def test_real_s3_operations(self):
        """Test with real S3 service."""
        # This would test against real S3 - skip by default
        # to avoid requiring AWS credentials in CI/CD
        s3_client = S3Client()

        # Real integration test code would go here
        pass
