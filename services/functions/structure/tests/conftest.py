import os
import pytest
from unittest.mock import patch, Mock

@pytest.fixture(autouse=True)
def setup_test_environment():
    """Setup test environment variables"""
    test_env = {
        "AWS_DEFAULT_REGION": "us-east-1",
        "AWS_ACCESS_KEY_ID": "testing",
        "AWS_SECRET_ACCESS_KEY": "testing",
        "ENVIRONMENT": "test",
        # Structure-specific environment variables
        "TEXTRACT_REGION": "us-east-1",
        "SOURCE_BUCKET": "test-source-bucket",
        "RESULTS_BUCKET": "test-results-bucket",
        "STRUCTURE_QUEUE_URL": "https://sqs.us-east-1.amazonaws.com/123456789/test-structure"
    }

    with patch.dict(os.environ, test_env):
        yield

@pytest.fixture
def sample_document_structure():
    """Sample document structure for testing"""
    return {
        "pages": [
            {
                "page_number": 1,
                "headings": [
                    {"text": "Chapter 1: Introduction", "level": 1, "confidence": 98.5},
                    {"text": "1.1 Overview", "level": 2, "confidence": 97.2}
                ],
                "paragraphs": [
                    {"text": "This is the introduction paragraph.", "confidence": 95.0}
                ],
                "tables": [
                    {
                        "rows": 3,
                        "columns": 2,
                        "cells": [
                            {"row": 0, "col": 0, "text": "Header 1"},
                            {"row": 0, "col": 1, "text": "Header 2"}
                        ]
                    }
                ],
                "images": [
                    {"description": "Figure 1: Sample chart", "confidence": 90.0}
                ]
            }
        ]
    }
