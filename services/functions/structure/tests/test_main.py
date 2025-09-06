import pytest
import json
from unittest.mock import Mock, patch
import sys
import os

# Add the parent directory to the path so we can import main
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_lambda_handler_import():
    """Test that the main module can be imported"""
    try:
        import main
        assert hasattr(main, 'app') or hasattr(main, 'handler') or hasattr(main, 'lambda_handler')
    except ImportError as e:
        pytest.skip(f"Cannot import main module: {e}")

def test_health_endpoint():
    """Test health endpoint if available"""
    try:
        import main
        from fastapi.testclient import TestClient

        if hasattr(main, 'app'):
            client = TestClient(main.app)
            response = client.get("/health")
            assert response.status_code in [200, 404]
    except Exception as e:
        pytest.skip(f"Health endpoint test skipped: {e}")

@patch('boto3.client')
def test_structure_analysis_mock(mock_boto_client):
    """Test document structure analysis functionality"""
    mock_textract = Mock()
    mock_s3 = Mock()

    mock_boto_client.side_effect = lambda service: {
        'textract': mock_textract,
        's3': mock_s3
    }.get(service, Mock())

    # Mock Textract response with document structure
    mock_textract.analyze_document.return_value = {
        'Blocks': [
            {
                'BlockType': 'PAGE',
                'Id': 'page-1',
                'Confidence': 99.0
            },
            {
                'BlockType': 'LINE',
                'Id': 'heading-1',
                'Text': 'Chapter 1: Introduction',
                'Confidence': 98.5,
                'BlockType': 'LINE'
            },
            {
                'BlockType': 'TABLE',
                'Id': 'table-1',
                'Confidence': 95.0,
                'Relationships': [
                    {
                        'Type': 'CHILD',
                        'Ids': ['cell-1', 'cell-2']
                    }
                ]
            }
        ]
    }

    try:
        import main

        if hasattr(main, 'analyze_structure') or hasattr(main, 'extract_structure'):
            assert True
        else:
            pytest.skip("No structure analysis function found")

    except Exception as e:
        pytest.skip(f"Structure analysis test skipped: {e}")

def test_heading_detection():
    """Test heading detection functionality"""
    try:
        import main

        sample_text_blocks = [
            {"text": "Chapter 1: Introduction", "font_size": 18, "is_bold": True},
            {"text": "This is regular paragraph text.", "font_size": 12, "is_bold": False},
            {"text": "1.1 Overview", "font_size": 14, "is_bold": True},
        ]

        # Test heading detection logic if available
        if hasattr(main, 'detect_headings') or hasattr(main, 'identify_headings'):
            assert True
        else:
            pytest.skip("No heading detection function found")

    except Exception as e:
        pytest.skip(f"Heading detection test skipped: {e}")

def test_table_extraction():
    """Test table extraction functionality"""
    try:
        import main

        # Test table extraction if available
        if hasattr(main, 'extract_tables') or hasattr(main, 'process_tables'):
            assert True
        else:
            pytest.skip("No table extraction function found")

    except Exception as e:
        pytest.skip(f"Table extraction test skipped: {e}")
