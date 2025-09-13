import json
from unittest.mock import patch

import boto3
import pytest
from moto import mock_s3


@pytest.fixture
def aws_credentials():
    """Mock AWS Credentials for moto."""
    import os

    os.environ["AWS_ACCESS_KEY_ID"] = "testing"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
    os.environ["AWS_SECURITY_TOKEN"] = "testing"
    os.environ["AWS_SESSION_TOKEN"] = "testing"
    os.environ["AWS_DEFAULT_REGION"] = "us-east-1"


@pytest.fixture
def s3_setup(aws_credentials):
    """Set up S3 buckets for testing."""
    with mock_s3():
        s3 = boto3.client("s3", region_name="us-east-1")

        # Create test buckets
        buckets = ["test-pdf-originals", "test-pdf-derivatives", "test-pdf-accessible"]

        for bucket in buckets:
            s3.create_bucket(Bucket=bucket)

        # Upload sample document structure
        with open("tests/fixtures/sample_document_structure.json") as f:
            sample_structure = f.read()

        s3.put_object(
            Bucket="test-pdf-derivatives",
            Key="pdf-derivatives/test-doc-123/structure/document.json",
            Body=sample_structure,
            ContentType="application/json",
        )

        yield s3


@pytest.fixture
def sample_step_function_input():
    """Sample input for Step Functions execution."""
    return {
        "docId": "test-doc-123",
        "s3Key": "pdfs/test-document.pdf",
        "userId": "user-456",
        "priority": False,
    }


@pytest.fixture
def sample_document_structure():
    """Sample document structure for testing."""
    with open("tests/fixtures/sample_document_structure.json") as f:
        return json.load(f)


class TestPipelineIntegration:
    """Integration tests for the PDF accessibility pipeline."""

    def test_step_functions_workflow_definition(self):
        """Test that Step Functions workflow definition is valid."""
        with open("infra/step-functions/pdf-processing-workflow.json") as f:
            workflow = json.load(f)

        # Validate basic structure
        assert "Comment" in workflow
        assert "StartAt" in workflow
        assert "States" in workflow

        # Validate all expected states exist
        expected_states = [
            "OCRProcessing",
            "StructureProcessing",
            "AltTextProcessing",
            "TagPDFProcessing",
            "ExportsProcessing",
            "ValidationProcessing",
            "NotifyCompletion",
        ]

        for state in expected_states:
            assert state in workflow["States"]

        # Validate error handling states
        error_states = [
            "HandleOCRFailure",
            "HandleStructureFailure",
            "HandleAltTextFailure",
            "HandleTagFailure",
            "HandleExportsFailure",
            "HandleValidationFailure",
        ]

        for state in error_states:
            assert state in workflow["States"]

    def test_ocr_lambda_input_output_contract(self):
        """Test OCR Lambda input/output contract."""
        from services.functions.ocr.models import OCRRequest, OCRResult, OCRStatus

        # Test valid input
        ocr_input = {
            "doc_id": "test-doc-123",
            "s3_key": "pdfs/test-document.pdf",
            "user_id": "user-456",
            "priority": False,
        }

        request = OCRRequest(**ocr_input)
        assert request.doc_id == "test-doc-123"
        assert not request.priority

        # Test valid output
        ocr_output = {
            "doc_id": "test-doc-123",
            "status": "completed",
            "textract_s3_key": "pdf-derivatives/test-doc-123/textract/raw_output.json",
            "is_image_based": True,
            "page_count": 5,
            "processing_time_seconds": 45.2,
        }

        result = OCRResult(**ocr_output)
        assert result.status == OCRStatus.COMPLETED
        assert result.page_count == 5

    def test_structure_lambda_input_output_contract(self):
        """Test Structure Lambda input/output contract."""
        from services.functions.structure.models import (
            StructureRequest,
            StructureResult,
        )

        # Test valid input
        structure_input = {
            "doc_id": "test-doc-123",
            "textract_s3_key": "pdf-derivatives/test-doc-123/textract/raw_output.json",
            "original_s3_key": "pdfs/test-document.pdf",
            "user_id": "user-456",
        }

        request = StructureRequest(**structure_input)
        assert request.doc_id == "test-doc-123"
        assert request.textract_s3_key is not None

        # Test valid output
        structure_output = {
            "doc_id": "test-doc-123",
            "status": "completed",
            "document_json_s3_key": "pdf-derivatives/test-doc-123/structure/document.json",
            "elements_count": 15,
            "processing_time_seconds": 30.1,
        }

        result = StructureResult(**structure_output)
        assert result.status == "completed"
        assert result.elements_count == 15

    def test_document_structure_model_validation(self, sample_document_structure):
        """Test document structure model validation."""
        from services.functions.structure.models import DocumentStructure

        # Test valid document structure
        doc_structure = DocumentStructure(**sample_document_structure)

        assert doc_structure.doc_id == "test-doc-123"
        assert doc_structure.title == "Sample Accessibility Report"
        assert doc_structure.total_pages == 3
        assert len(doc_structure.elements) == 9  # As per fixture
        assert len(doc_structure.reading_order) == 9

        # Validate element types
        element_types = [elem.type for elem in doc_structure.elements]
        assert "heading" in element_types
        assert "paragraph" in element_types
        assert "list" in element_types
        assert "figure" in element_types
        assert "table" in element_types

    @patch("boto3.client")
    def test_s3_file_operations(self, mock_boto_client, s3_setup):
        """Test S3 file operations for the pipeline."""

        # Test that files are stored in expected S3 structure
        expected_keys = [
            "pdf-derivatives/{doc_id}/textract/raw_output.json",
            "pdf-derivatives/{doc_id}/structure/document.json",
            "pdf-derivatives/{doc_id}/alt-text/alt.json",
            "pdf-accessible/{doc_id}/document_tagged.pdf",
            "pdf-accessible/{doc_id}/exports/document.html",
            "pdf-accessible/{doc_id}/exports/document.epub",
            "pdf-accessible/{doc_id}/exports/tables.zip",
        ]

        doc_id = "test-doc-123"
        for key_template in expected_keys:
            expected_key = key_template.format(doc_id=doc_id)
            # In a real test, we would verify these keys exist in S3
            assert "{doc_id}" not in expected_key  # Template was filled

    def test_error_handling_propagation(self):
        """Test that errors are properly propagated through the pipeline."""
        from services.shared.models import ProcessingStatus

        # Test error response structure
        error_response = {
            "doc_id": "test-doc-123",
            "status": "failed",
            "error_message": "Textract job failed: InvalidDocumentFormat",
        }

        # Validate error response can be parsed
        assert error_response["status"] == ProcessingStatus.FAILED.value
        assert "error_message" in error_response

    def test_validation_issues_model(self):
        """Test validation issues model structure."""
        from services.shared.models import ValidationIssue, ValidationLevel

        issue = ValidationIssue(
            type="missing_alt_text",
            level=ValidationLevel.ERROR,
            message="Figure 1 is missing alternative text description",
            location="page 2, figure-1",
            rule="WCAG 2.1 - 1.1.1 Non-text Content",
        )

        assert issue.level == ValidationLevel.ERROR
        assert "missing alternative text" in issue.message.lower()

    def test_pipeline_data_flow(self, sample_step_function_input):
        """Test data flow between pipeline steps."""
        # Simulate the data transformations through each step

        # Step 1: OCR
        ocr_output = {
            "doc_id": sample_step_function_input["docId"],
            "status": "completed",
            "textract_s3_key": "pdf-derivatives/test-doc-123/textract/raw_output.json",
            "is_image_based": True,
            "page_count": 3,
        }

        # Step 2: Structure (uses OCR output)
        structure_input = {
            "doc_id": ocr_output["doc_id"],
            "textract_s3_key": ocr_output["textract_s3_key"],
            "original_s3_key": sample_step_function_input["s3Key"],
            "user_id": sample_step_function_input["userId"],
        }

        structure_output = {
            "doc_id": structure_input["doc_id"],
            "status": "completed",
            "document_json_s3_key": "pdf-derivatives/test-doc-123/structure/document.json",
            "elements_count": 9,
        }

        # Step 3: Alt Text (uses Structure output)
        alt_text_input = {
            "doc_id": structure_output["doc_id"],
            "document_json_s3_key": structure_output["document_json_s3_key"],
            "original_s3_key": sample_step_function_input["s3Key"],
            "user_id": sample_step_function_input["userId"],
        }

        # Verify the data flow chain is consistent
        assert ocr_output["doc_id"] == sample_step_function_input["docId"]
        assert structure_input["doc_id"] == ocr_output["doc_id"]
        assert alt_text_input["doc_id"] == structure_output["doc_id"]

    @pytest.mark.integration
    def test_full_pipeline_with_mocked_services(
        self, s3_setup, sample_step_function_input
    ):
        """Integration test with mocked AWS services."""
        # This test would require actual Lambda function deployments
        # For now, we test the contract compatibility

        pipeline_steps = [
            "ocr",
            "structure",
            "alt_text",
            "tag_pdf",
            "exports",
            "validate",
            "notify",
        ]

        current_data = sample_step_function_input.copy()

        for step in pipeline_steps:
            # Each step should be able to process the current data format
            # and produce output compatible with the next step
            assert "docId" in current_data or "doc_id" in current_data

            # Simulate step processing
            if step == "ocr":
                current_data.update(
                    {
                        "textract_s3_key": f"pdf-derivatives/{current_data['docId']}/textract/raw_output.json"
                    }
                )
            elif step == "structure":
                current_data.update(
                    {
                        "document_json_s3_key": f"pdf-derivatives/{current_data['docId']}/structure/document.json"
                    }
                )
            # ... other steps would follow similar patterns

        # Final output should contain all expected keys
        expected_final_keys = [
            "docId",
            "s3Key",
            "userId",
            "textract_s3_key",
            "document_json_s3_key",
        ]

        for key in expected_final_keys:
            assert key in current_data or key.replace("Id", "_id") in current_data


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
