"""
Tests for shared schema definitions.
Validates Pydantic models and type definitions used across services.
"""

from datetime import datetime
from uuid import UUID, uuid4

import pytest

from ..api import APIResponse, ErrorResponse, PaginatedResponse, PaginationParams
from ..document import DocumentSchema, DocumentStatus, DocumentType, ProcessingStep
from ..user import UserRole, UserSchema


class TestDocumentSchemas:
    """Test document-related schemas."""

    def test_document_schema_validation(self):
        """Test DocumentSchema validation."""
        doc_data = {
            "id": str(uuid4()),
            "filename": "test.pdf",
            "status": DocumentStatus.PENDING,
            "type": DocumentType.PDF,
            "user_id": str(uuid4()),
            "tenant_id": str(uuid4()),
            "file_size": 1024,
            "created_at": datetime.now(),
            "metadata": {"source": "upload"},
        }

        doc = DocumentSchema(**doc_data)

        assert doc.filename == "test.pdf"
        assert doc.status == DocumentStatus.PENDING
        assert doc.type == DocumentType.PDF
        assert doc.file_size == 1024
        assert isinstance(doc.id, UUID)
        assert isinstance(doc.user_id, UUID)
        assert doc.metadata["source"] == "upload"

    def test_document_status_enum(self):
        """Test document status enumeration."""
        assert DocumentStatus.PENDING == "pending"
        assert DocumentStatus.PROCESSING == "processing"
        assert DocumentStatus.COMPLETED == "completed"
        assert DocumentStatus.FAILED == "failed"

        # Test valid status assignment
        doc_data = {
            "id": str(uuid4()),
            "filename": "test.pdf",
            "status": "processing",
            "type": "pdf",
            "user_id": str(uuid4()),
            "tenant_id": str(uuid4()),
            "created_at": datetime.now(),
        }

        doc = DocumentSchema(**doc_data)
        assert doc.status == DocumentStatus.PROCESSING

    def test_processing_step_schema(self):
        """Test ProcessingStep schema."""
        step_data = {
            "name": "ocr",
            "status": "completed",
            "started_at": datetime.now(),
            "completed_at": datetime.now(),
            "duration_ms": 1500,
            "metadata": {"pages_processed": 5},
        }

        step = ProcessingStep(**step_data)

        assert step.name == "ocr"
        assert step.status == "completed"
        assert step.duration_ms == 1500
        assert step.metadata["pages_processed"] == 5

    def test_invalid_document_data(self):
        """Test validation errors for invalid document data."""
        # Missing required fields
        with pytest.raises(ValueError):
            DocumentSchema(filename="test.pdf")

        # Invalid status
        with pytest.raises(ValueError):
            DocumentSchema(
                id=str(uuid4()),
                filename="test.pdf",
                status="invalid_status",
                type="pdf",
                user_id=str(uuid4()),
                tenant_id=str(uuid4()),
                created_at=datetime.now(),
            )

        # Invalid file size
        with pytest.raises(ValueError):
            DocumentSchema(
                id=str(uuid4()),
                filename="test.pdf",
                status="pending",
                type="pdf",
                user_id=str(uuid4()),
                tenant_id=str(uuid4()),
                file_size=-100,
                created_at=datetime.now(),
            )


class TestUserSchemas:
    """Test user-related schemas."""

    def test_user_schema_validation(self):
        """Test UserSchema validation."""
        user_data = {
            "id": str(uuid4()),
            "email": "test@example.com",
            "name": "Test User",
            "role": UserRole.VIEWER,
            "tenant_id": str(uuid4()),
            "created_at": datetime.now(),
            "is_active": True,
        }

        user = UserSchema(**user_data)

        assert user.email == "test@example.com"
        assert user.name == "Test User"
        assert user.role == UserRole.VIEWER
        assert user.is_active is True
        assert isinstance(user.id, UUID)

    def test_user_role_enum(self):
        """Test user role enumeration."""
        assert UserRole.VIEWER == "viewer"
        assert UserRole.ADMIN == "admin"

        # Test role assignment
        user_data = {
            "id": str(uuid4()),
            "email": "admin@example.com",
            "name": "Admin User",
            "role": "admin",
            "tenant_id": str(uuid4()),
            "created_at": datetime.now(),
        }

        user = UserSchema(**user_data)
        assert user.role == UserRole.ADMIN

    def test_email_validation(self):
        """Test email format validation."""
        # Valid emails should work
        valid_emails = [
            "test@example.com",
            "user+tag@domain.co.uk",
            "firstname.lastname@company.org",
        ]

        for email in valid_emails:
            user_data = {
                "id": str(uuid4()),
                "email": email,
                "name": "Test User",
                "role": "viewer",
                "tenant_id": str(uuid4()),
                "created_at": datetime.now(),
            }
            user = UserSchema(**user_data)
            assert user.email == email

        # Invalid emails should fail
        invalid_emails = [
            "invalid-email",
            "@example.com",
            "user@",
            "user space@example.com",
        ]

        for email in invalid_emails:
            with pytest.raises(ValueError):
                UserSchema(
                    id=str(uuid4()),
                    email=email,
                    name="Test User",
                    role="viewer",
                    tenant_id=str(uuid4()),
                    created_at=datetime.now(),
                )


class TestAPISchemas:
    """Test API response schemas."""

    def test_api_response_schema(self):
        """Test APIResponse schema."""
        response_data = {
            "success": True,
            "data": {"message": "Operation completed"},
            "message": "Success",
        }

        response = APIResponse(**response_data)

        assert response.success is True
        assert response.data["message"] == "Operation completed"
        assert response.message == "Success"

    def test_error_response_schema(self):
        """Test ErrorResponse schema."""
        error_data = {
            "error": "validation_error",
            "message": "Invalid input provided",
            "details": {"field": "email", "issue": "Invalid format"},
            "request_id": str(uuid4()),
        }

        error = ErrorResponse(**error_data)

        assert error.error == "validation_error"
        assert error.message == "Invalid input provided"
        assert error.details["field"] == "email"
        assert isinstance(error.request_id, UUID)

    def test_pagination_params(self):
        """Test PaginationParams schema."""
        pagination_data = {
            "page": 2,
            "page_size": 20,
            "sort_by": "created_at",
            "sort_order": "desc",
        }

        pagination = PaginationParams(**pagination_data)

        assert pagination.page == 2
        assert pagination.page_size == 20
        assert pagination.sort_by == "created_at"
        assert pagination.sort_order == "desc"

    def test_pagination_validation(self):
        """Test pagination parameter validation."""
        # Invalid page number
        with pytest.raises(ValueError):
            PaginationParams(page=0, page_size=10)

        # Invalid page size
        with pytest.raises(ValueError):
            PaginationParams(page=1, page_size=101)  # Assuming max is 100

        # Invalid sort order
        with pytest.raises(ValueError):
            PaginationParams(page=1, page_size=10, sort_order="invalid")

    def test_paginated_response(self):
        """Test PaginatedResponse schema."""
        response_data = {
            "success": True,
            "data": [
                {"id": str(uuid4()), "name": "Item 1"},
                {"id": str(uuid4()), "name": "Item 2"},
            ],
            "pagination": {
                "page": 1,
                "page_size": 10,
                "total_items": 25,
                "total_pages": 3,
                "has_next": True,
                "has_previous": False,
            },
        }

        response = PaginatedResponse(**response_data)

        assert len(response.data) == 2
        assert response.pagination.total_items == 25
        assert response.pagination.total_pages == 3
        assert response.pagination.has_next is True
        assert response.pagination.has_previous is False


class TestSchemaInteroperability:
    """Test schemas work together correctly."""

    def test_document_with_user_reference(self):
        """Test document schema with user references."""
        user_id = uuid4()
        tenant_id = uuid4()

        # Create user
        user_data = {
            "id": str(user_id),
            "email": "user@example.com",
            "name": "Test User",
            "role": "viewer",
            "tenant_id": str(tenant_id),
            "created_at": datetime.now(),
        }
        user = UserSchema(**user_data)

        # Create document referencing the user
        doc_data = {
            "id": str(uuid4()),
            "filename": "user-doc.pdf",
            "status": "pending",
            "type": "pdf",
            "user_id": str(user_id),
            "tenant_id": str(tenant_id),
            "created_at": datetime.now(),
        }
        doc = DocumentSchema(**doc_data)

        # Verify relationship
        assert doc.user_id == user.id
        assert doc.tenant_id == user.tenant_id

    def test_api_response_with_document_data(self):
        """Test API response containing document data."""
        doc_data = {
            "id": str(uuid4()),
            "filename": "api-doc.pdf",
            "status": "completed",
            "type": "pdf",
            "user_id": str(uuid4()),
            "tenant_id": str(uuid4()),
            "created_at": datetime.now(),
        }

        response_data = {
            "success": True,
            "data": doc_data,
            "message": "Document retrieved successfully",
        }

        response = APIResponse(**response_data)

        # Should be able to reconstruct document from response data
        document = DocumentSchema(**response.data)
        assert document.filename == "api-doc.pdf"
        assert document.status == DocumentStatus.COMPLETED
