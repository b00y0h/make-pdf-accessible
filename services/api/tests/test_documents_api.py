import json
from unittest.mock import patch
from uuid import UUID

from app.main import app
from app.models import DocumentStatus
from fastapi import status
from fastapi.testclient import TestClient


class TestDocumentsAPI:
    """Test document API endpoints"""

    def setup_method(self):
        """Setup for each test method"""
        self.client = TestClient(app)
        self.mock_user_patcher = patch("app.routes.documents.get_current_user")
        self.mock_service_patcher = patch("app.routes.documents.document_service")

        self.mock_get_current_user = self.mock_user_patcher.start()
        self.mock_document_service = self.mock_service_patcher.start()

        # Setup default mock user
        from app.auth import User

        self.test_user = User(
            sub="test-user-123",
            username="testuser",
            email="test@example.com",
            roles=["viewer"],
        )
        self.mock_get_current_user.return_value = self.test_user

    def teardown_method(self):
        """Cleanup after each test method"""
        self.mock_user_patcher.stop()
        self.mock_service_patcher.stop()

    def test_upload_document_with_url_success(self):
        """Test successful document upload with URL"""
        from datetime import datetime

        from app.models import DocumentResponse

        # Mock service response
        mock_document = DocumentResponse(
            doc_id=UUID("12345678-1234-1234-1234-123456789012"),
            status=DocumentStatus.PENDING,
            filename="test.pdf",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            user_id="test-user-123",
            metadata={"source": "url"},
            artifacts={},
        )

        self.mock_document_service.create_document.return_value = mock_document

        # Test request
        response = self.client.post(
            "/documents",
            data={
                "source_url": "https://example.com/test.pdf",
                "filename": "test.pdf",
                "metadata": json.dumps({"source": "url"}),
            },
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["status"] == "pending"
        assert data["filename"] == "test.pdf"
        assert data["user_id"] == "test-user-123"

    def test_upload_document_validation_error(self):
        """Test document upload validation error"""
        # No file or source_url provided
        response = self.client.post("/documents", data={"filename": "test.pdf"})

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert (
            "Either file upload or source_url must be provided"
            in response.json()["message"]
        )

    def test_upload_document_both_file_and_url(self):
        """Test upload with both file and URL (should fail)"""
        response = self.client.post(
            "/documents",
            data={"source_url": "https://example.com/test.pdf"},
            files={"file": ("test.pdf", b"fake pdf content", "application/pdf")},
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert (
            "Cannot provide both file upload and source_url"
            in response.json()["message"]
        )

    def test_upload_document_invalid_metadata(self):
        """Test upload with invalid JSON metadata"""
        response = self.client.post(
            "/documents",
            data={
                "source_url": "https://example.com/test.pdf",
                "metadata": "invalid-json",
            },
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Invalid JSON in metadata field" in response.json()["message"]

    def test_list_documents_success(self):
        """Test successful document listing"""
        from datetime import datetime

        from app.models import DocumentResponse

        # Mock service response
        mock_documents = [
            DocumentResponse(
                doc_id=UUID("12345678-1234-1234-1234-123456789012"),
                status=DocumentStatus.COMPLETED,
                filename="test1.pdf",
                created_at=datetime.now(),
                updated_at=datetime.now(),
                user_id="test-user-123",
                metadata={},
                artifacts={},
            ),
            DocumentResponse(
                doc_id=UUID("12345678-1234-1234-1234-123456789013"),
                status=DocumentStatus.PENDING,
                filename="test2.pdf",
                created_at=datetime.now(),
                updated_at=datetime.now(),
                user_id="test-user-123",
                metadata={},
                artifacts={},
            ),
        ]

        self.mock_document_service.list_user_documents.return_value = (
            mock_documents,
            2,
        )

        # Test request
        response = self.client.get("/documents?page=1&per_page=10")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] == 2
        assert len(data["documents"]) == 2
        assert data["page"] == 1
        assert data["per_page"] == 10

    def test_list_documents_with_status_filter(self):
        """Test document listing with status filter"""
        from datetime import datetime

        from app.models import DocumentResponse

        mock_documents = [
            DocumentResponse(
                doc_id=UUID("12345678-1234-1234-1234-123456789012"),
                status=DocumentStatus.COMPLETED,
                filename="test.pdf",
                created_at=datetime.now(),
                updated_at=datetime.now(),
                user_id="test-user-123",
                metadata={},
                artifacts={},
            )
        ]

        self.mock_document_service.list_user_documents.return_value = (
            mock_documents,
            1,
        )

        response = self.client.get("/documents?status=completed")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] == 1
        assert data["documents"][0]["status"] == "completed"

    def test_get_document_success(self):
        """Test successful document retrieval"""
        from datetime import datetime

        from app.models import DocumentResponse

        doc_id = "12345678-1234-1234-1234-123456789012"

        mock_document = DocumentResponse(
            doc_id=UUID(doc_id),
            status=DocumentStatus.COMPLETED,
            filename="test.pdf",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            user_id="test-user-123",
            metadata={"source": "upload"},
            artifacts={"pdf": "s3://bucket/key"},
        )

        self.mock_document_service.get_document.return_value = mock_document

        response = self.client.get(f"/documents/{doc_id}")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["doc_id"] == doc_id
        assert data["status"] == "completed"
        assert data["artifacts"]["pdf"] == "s3://bucket/key"

    def test_get_document_not_found(self):
        """Test document not found"""
        doc_id = "12345678-1234-1234-1234-123456789012"

        self.mock_document_service.get_document.return_value = None

        response = self.client.get(f"/documents/{doc_id}")

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "Document not found" in response.json()["message"]

    def test_get_document_access_denied(self):
        """Test access denied to other user's document"""
        from datetime import datetime

        from app.models import DocumentResponse

        doc_id = "12345678-1234-1234-1234-123456789012"

        # Document belongs to different user
        mock_document = DocumentResponse(
            doc_id=UUID(doc_id),
            status=DocumentStatus.COMPLETED,
            filename="test.pdf",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            user_id="other-user-123",  # Different user
            metadata={},
            artifacts={},
        )

        self.mock_document_service.get_document.return_value = mock_document

        response = self.client.get(f"/documents/{doc_id}")

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert "Access denied to this document" in response.json()["message"]

    def test_get_download_url_success(self):
        """Test successful download URL generation"""
        from datetime import datetime

        doc_id = "12345678-1234-1234-1234-123456789012"

        # Mock document exists and is completed
        from app.models import DocumentResponse

        mock_document = DocumentResponse(
            doc_id=UUID(doc_id),
            status=DocumentStatus.COMPLETED,
            filename="test.pdf",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            user_id="test-user-123",
            metadata={},
            artifacts={},
        )

        self.mock_document_service.get_document.return_value = mock_document
        self.mock_document_service.generate_presigned_url.return_value = (
            "https://s3.amazonaws.com/bucket/key?signature=abc123",
            "application/pdf",
            "test.pdf",
        )

        response = self.client.get(f"/documents/{doc_id}/downloads?document_type=pdf")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["download_url"].startswith("https://s3.amazonaws.com")
        assert data["content_type"] == "application/pdf"
        assert data["filename"] == "test.pdf"
        assert "expires_at" in data

    def test_get_download_url_document_not_ready(self):
        """Test download URL for document not yet completed"""
        from datetime import datetime

        from app.models import DocumentResponse

        doc_id = "12345678-1234-1234-1234-123456789012"

        # Document is still processing
        mock_document = DocumentResponse(
            doc_id=UUID(doc_id),
            status=DocumentStatus.PROCESSING,  # Not completed
            filename="test.pdf",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            user_id="test-user-123",
            metadata={},
            artifacts={},
        )

        self.mock_document_service.get_document.return_value = mock_document

        response = self.client.get(f"/documents/{doc_id}/downloads?document_type=pdf")

        assert response.status_code == status.HTTP_409_CONFLICT
        assert "Document is not ready for download" in response.json()["message"]
        assert "processing" in response.json()["message"]

    def test_get_download_url_invalid_expiration(self):
        """Test download URL with invalid expiration time"""
        doc_id = "12345678-1234-1234-1234-123456789012"

        response = self.client.get(
            f"/documents/{doc_id}/downloads?document_type=pdf&expires_in=100"  # Too short
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_admin_can_access_any_document(self):
        """Test admin can access any user's document"""
        from datetime import datetime

        from app.auth import User
        from app.models import DocumentResponse

        # Setup admin user
        admin_user = User(sub="admin-user-123", username="admin", roles=["admin"])
        self.mock_get_current_user.return_value = admin_user

        doc_id = "12345678-1234-1234-1234-123456789012"

        # Document belongs to different user
        mock_document = DocumentResponse(
            doc_id=UUID(doc_id),
            status=DocumentStatus.COMPLETED,
            filename="test.pdf",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            user_id="other-user-123",
            metadata={},
            artifacts={},
        )

        self.mock_document_service.get_document.return_value = mock_document

        response = self.client.get(f"/documents/{doc_id}")

        # Admin should have access
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["doc_id"] == doc_id
