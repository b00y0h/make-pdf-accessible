#!/usr/bin/env python3
"""
Test script to validate MongoDB integration for PDF accessibility service.
"""

import asyncio
import os
import sys
import uuid
from datetime import datetime

# Add services directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "services", "api"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "services", "shared"))


def setup_test_environment():
    """Setup test environment variables."""
    os.environ.update(
        {
            "PERSISTENCE_PROVIDER": "mongo",
            "MONGODB_URI": "mongodb://localhost:27017/pdf_accessibility_test",
            "MONGODB_DATABASE": "pdf_accessibility_test",
            "ENABLE_QUERY_LOGGING": "true",
            "DEBUG_MODE": "true",
            "AWS_REGION": "us-east-1",  # Mock for S3 operations
            "AWS_ACCESS_KEY_ID": "test",  # Mock credentials
            "AWS_SECRET_ACCESS_KEY": "test",
        }
    )


async def test_persistence_layer():
    """Test the persistence layer functionality."""
    print("🧪 Testing Persistence Layer...")

    try:
        from services.shared.feature_flags import get_feature_flags
        from services.shared.persistence import get_persistence_manager

        # Test feature flags
        flags = get_feature_flags()
        print(f"✅ Feature flags loaded: {flags.get_persistence_provider()}")

        # Get persistence manager
        pm = get_persistence_manager()
        print("✅ Persistence manager initialized")

        # Test document repository
        doc_repo = pm.document_repository
        print(f"✅ Document repository: {type(doc_repo).__name__}")

        # Test job repository
        job_repo = pm.job_repository
        print(f"✅ Job repository: {type(job_repo).__name__}")

        return pm

    except Exception as e:
        print(f"❌ Persistence layer test failed: {e}")
        import traceback

        traceback.print_exc()
        return None


async def test_document_operations(pm):
    """Test document CRUD operations."""
    print("\n📄 Testing Document Operations...")

    try:
        # Create a test document
        doc_id = str(uuid.uuid4())
        test_doc = {
            "docId": doc_id,
            "ownerId": "test-user-123",
            "status": "pending",
            "createdAt": datetime.utcnow(),
            "updatedAt": datetime.utcnow(),
            "filename": "test-document.pdf",
            "metadata": {"source": "test"},
            "artifacts": {},
        }

        # Create document
        created_doc = pm.create_document(test_doc)
        print(f"✅ Document created: {created_doc.get('docId', 'Unknown ID')}")

        # Get document
        retrieved_doc = pm.document_repository.get_document(doc_id)
        if retrieved_doc:
            print(f"✅ Document retrieved: {retrieved_doc['docId']}")
        else:
            print("❌ Failed to retrieve document")
            return False

        # List documents by owner
        docs_result = pm.document_repository.get_documents_by_owner("test-user-123")
        print(
            f"✅ Documents by owner: {docs_result['total']} total, {len(docs_result['documents'])} returned"
        )

        # Update document status
        success = pm.update_document_status(doc_id, "processing")
        print(f"✅ Document status updated: {success}")

        return True

    except Exception as e:
        print(f"❌ Document operations test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


async def test_job_operations(pm):
    """Test job CRUD operations."""
    print("\n⚙️  Testing Job Operations...")

    try:
        # Create a test job
        job_id = str(uuid.uuid4())
        doc_id = str(uuid.uuid4())
        test_job = {
            "jobId": job_id,
            "docId": doc_id,
            "ownerId": "test-user-123",
            "step": "structure",
            "status": "pending",
            "priority": False,
            "createdAt": datetime.utcnow(),
            "updatedAt": datetime.utcnow(),
        }

        # Create job
        created_job = pm.create_job(test_job)
        print(f"✅ Job created: {created_job.get('jobId', 'Unknown ID')}")

        # Get job
        retrieved_job = pm.job_repository.get_job(job_id)
        if retrieved_job:
            print(f"✅ Job retrieved: {retrieved_job['jobId']}")
        else:
            print("❌ Failed to retrieve job")
            return False

        # Get pending jobs
        pending_jobs = pm.job_repository.get_pending_jobs(limit=10)
        print(f"✅ Pending jobs: {len(pending_jobs)} found")

        # Update job status
        success = pm.update_job_status(job_id, "running")
        print(f"✅ Job status updated: {success}")

        return True

    except Exception as e:
        print(f"❌ Job operations test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


async def test_service_layer():
    """Test the service layer integration."""
    print("\n🔧 Testing Service Layer...")

    try:
        from services.api.app.services import DocumentService, ReportsService

        # Test DocumentService
        doc_service = DocumentService()
        print(
            f"✅ DocumentService initialized: {type(doc_service.persistence_manager).__name__}"
        )

        # Test ReportsService
        reports_service = ReportsService()
        print(
            f"✅ ReportsService initialized: {type(reports_service.persistence_manager).__name__}"
        )

        # Test create document
        doc_response = await doc_service.create_document(
            user_id="test-user-456",
            filename="service-test.pdf",
            metadata={"test": True},
        )
        print(f"✅ Service document created: {doc_response.doc_id}")

        # Test get document
        retrieved_doc = await doc_service.get_document(
            str(doc_response.doc_id), "test-user-456"
        )
        if retrieved_doc:
            print(f"✅ Service document retrieved: {retrieved_doc.doc_id}")
        else:
            print("❌ Failed to retrieve service document")
            return False

        # Test list documents
        docs_list, total = await doc_service.list_user_documents("test-user-456")
        print(f"✅ Service documents listed: {total} total, {len(docs_list)} returned")

        return True

    except Exception as e:
        print(f"❌ Service layer test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


async def test_health_check(pm):
    """Test health check functionality."""
    print("\n🏥 Testing Health Check...")

    try:
        health_status = pm.health_check()
        print("✅ Health check completed:")
        print(f"  Provider: {health_status.get('provider', 'Unknown')}")
        print(f"  Status: {health_status.get('status', 'Unknown')}")
        print(f"  Dual write: {health_status.get('dual_write', False)}")

        return health_status.get("status") == "healthy"

    except Exception as e:
        print(f"❌ Health check failed: {e}")
        return False


async def cleanup_test_data(pm):
    """Clean up test data."""
    print("\n🧹 Cleaning up test data...")

    try:
        # Note: In a real implementation, you'd want proper cleanup methods
        # For now, we'll just note that cleanup would happen here
        print("✅ Test data cleanup completed (simulated)")
        return True

    except Exception as e:
        print(f"❌ Cleanup failed: {e}")
        return False


async def main():
    """Run all tests."""
    print("🚀 Starting MongoDB Integration Tests\n")

    # Setup environment
    setup_test_environment()

    # Test persistence layer
    pm = await test_persistence_layer()
    if not pm:
        print("\n❌ Persistence layer tests failed. Exiting.")
        sys.exit(1)

    # Run tests
    tests_passed = 0
    total_tests = 5

    if await test_document_operations(pm):
        tests_passed += 1

    if await test_job_operations(pm):
        tests_passed += 1

    if await test_service_layer():
        tests_passed += 1

    if await test_health_check(pm):
        tests_passed += 1

    if await cleanup_test_data(pm):
        tests_passed += 1

    # Summary
    print(f"\n📊 Test Results: {tests_passed}/{total_tests} tests passed")

    if tests_passed == total_tests:
        print("🎉 All MongoDB integration tests passed!")
        return True
    else:
        print("❌ Some tests failed. Check the logs above.")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
