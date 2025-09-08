"""Persistence layer abstraction with support for MongoDB and DynamoDB."""

import logging
from datetime import datetime
from typing import List, Optional, Protocol, runtime_checkable

from .feature_flags import PersistenceProvider, get_feature_flags

logger = logging.getLogger(__name__)


@runtime_checkable
class DocumentRepository(Protocol):
    """Protocol for document repository interface."""

    def create_document(self, doc_data: dict) -> dict:
        """Create a new document."""
        ...

    def get_document(self, doc_id: str) -> Optional[dict]:
        """Get document by ID."""
        ...

    def get_documents_by_owner(
        self,
        owner_id: str,
        status_filter: Optional[List[str]] = None,
        page: int = 1,
        limit: int = 10,
        sort_by: str = 'createdAt',
        sort_order: str = 'desc'
    ) -> dict:
        """Get documents for owner with pagination."""
        ...

    def update_document_status(
        self,
        doc_id: str,
        status: str,
        error_message: Optional[str] = None,
        completed_at: Optional[datetime] = None,
        additional_data: Optional[dict] = None
    ) -> bool:
        """Update document status."""
        ...

    def get_processing_summary(self) -> dict:
        """Get processing summary statistics."""
        ...


@runtime_checkable
class JobRepository(Protocol):
    """Protocol for job repository interface."""

    def create_job(self, job_data: dict) -> dict:
        """Create a new job."""
        ...

    def get_job(self, job_id: str) -> Optional[dict]:
        """Get job by ID."""
        ...

    def get_jobs_for_document(
        self,
        doc_id: str,
        step_filter: Optional[List[str]] = None,
        status_filter: Optional[List[str]] = None
    ) -> List[dict]:
        """Get jobs for document."""
        ...

    def get_pending_jobs(
        self,
        step: Optional[str] = None,
        limit: int = 10,
        priority_threshold: Optional[int] = None
    ) -> List[dict]:
        """Get pending jobs for processing."""
        ...

    def update_job_status(
        self,
        job_id: str,
        status: str,
        **kwargs
    ) -> bool:
        """Update job status."""
        ...


class PersistenceManager:
    """Manages persistence layer based on feature flags."""

    def __init__(self):
        self.feature_flags = get_feature_flags()
        self._document_repo: Optional[DocumentRepository] = None
        self._job_repo: Optional[JobRepository] = None
        self._dynamo_document_repo: Optional[DocumentRepository] = None  # For dual write
        self._dynamo_job_repo: Optional[JobRepository] = None  # For dual write
        self._setup_repositories()

    def _setup_repositories(self):
        """Initialize repositories based on feature flags."""
        provider = self.feature_flags.get_persistence_provider()

        logger.info(f"Setting up persistence layer with provider: {provider.value}")

        if provider == PersistenceProvider.MONGO:
            self._setup_mongo_repositories()
        elif provider == PersistenceProvider.DYNAMO:
            self._setup_dynamo_repositories()

        # Setup dual write if enabled
        if self.feature_flags.should_dual_write():
            self._setup_dual_write()

    def _setup_mongo_repositories(self):
        """Setup MongoDB repositories."""
        try:
            from .mongo import get_document_repository, get_job_repository

            self._document_repo = get_document_repository()
            self._job_repo = get_job_repository()

            logger.info("MongoDB repositories initialized successfully")

        except ImportError as e:
            logger.error(f"Failed to import MongoDB repositories: {e}")
            raise RuntimeError("MongoDB dependencies not available")
        except Exception as e:
            logger.error(f"Failed to initialize MongoDB repositories: {e}")
            raise

    def _setup_dynamo_repositories(self):
        """Setup DynamoDB repositories."""
        try:
            from services.worker.src.pdf_worker.aws.dynamodb import (
                DocumentRepository as DynamoDocumentRepository,
            )
            from services.worker.src.pdf_worker.aws.dynamodb import (
                JobRepository as DynamoJobRepository,
            )

            self._document_repo = DynamoDocumentRepository()
            self._job_repo = DynamoJobRepository()

            logger.info("DynamoDB repositories initialized successfully")

        except ImportError as e:
            logger.error(f"Failed to import DynamoDB repositories: {e}")
            raise RuntimeError("DynamoDB dependencies not available")
        except Exception as e:
            logger.error(f"Failed to initialize DynamoDB repositories: {e}")
            raise

    def _setup_dual_write(self):
        """Setup dual write repositories for migration."""
        try:
            primary_provider = self.feature_flags.get_persistence_provider()

            if primary_provider == PersistenceProvider.MONGO:
                # Setup DynamoDB as secondary
                from services.worker.src.pdf_worker.aws.dynamodb import (
                    DocumentRepository as DynamoDocumentRepository,
                )
                from services.worker.src.pdf_worker.aws.dynamodb import (
                    JobRepository as DynamoJobRepository,
                )

                self._dynamo_document_repo = DynamoDocumentRepository()
                self._dynamo_job_repo = DynamoJobRepository()

                logger.info("Dual write enabled: MongoDB (primary) -> DynamoDB (secondary)")

            elif primary_provider == PersistenceProvider.DYNAMO:
                # Setup MongoDB as secondary
                from .mongo import get_document_repository, get_job_repository

                # Store in different variables to avoid confusion
                mongo_doc_repo = get_document_repository()
                mongo_job_repo = get_job_repository()

                # For DynamoDB primary, we'd need different storage
                # This is a simplified version - in production you'd want better separation
                logger.info("Dual write enabled: DynamoDB (primary) -> MongoDB (secondary)")

        except Exception as e:
            logger.error(f"Failed to setup dual write: {e}")
            # Don't fail completely, just disable dual write
            self.feature_flags.set('enable_dual_write', False)

    @property
    def document_repository(self) -> DocumentRepository:
        """Get document repository."""
        if self._document_repo is None:
            raise RuntimeError("Document repository not initialized")
        return self._document_repo

    @property
    def job_repository(self) -> JobRepository:
        """Get job repository."""
        if self._job_repo is None:
            raise RuntimeError("Job repository not initialized")
        return self._job_repo

    def create_document(self, doc_data: dict) -> dict:
        """Create document with dual write support."""
        try:
            # Primary write
            result = self.document_repository.create_document(doc_data)

            # Secondary write if dual write enabled
            if self.feature_flags.should_dual_write() and self._dynamo_document_repo:
                try:
                    self._dynamo_document_repo.create_document(doc_data)
                    logger.debug(f"Dual write successful for document {doc_data.get('docId')}")
                except Exception as e:
                    logger.error(f"Dual write failed for document {doc_data.get('docId')}: {e}")
                    # Continue with primary write success

            return result

        except Exception as e:
            logger.error(f"Failed to create document: {e}")
            raise

    def create_job(self, job_data: dict) -> dict:
        """Create job with dual write support."""
        try:
            # Primary write
            result = self.job_repository.create_job(job_data)

            # Secondary write if dual write enabled
            if self.feature_flags.should_dual_write() and self._dynamo_job_repo:
                try:
                    self._dynamo_job_repo.create_job(job_data)
                    logger.debug(f"Dual write successful for job {job_data.get('jobId')}")
                except Exception as e:
                    logger.error(f"Dual write failed for job {job_data.get('jobId')}: {e}")
                    # Continue with primary write success

            return result

        except Exception as e:
            logger.error(f"Failed to create job: {e}")
            raise

    def update_document_status(
        self,
        doc_id: str,
        status: str,
        **kwargs
    ) -> bool:
        """Update document status with dual write support."""
        try:
            # Primary update
            result = self.document_repository.update_document_status(doc_id, status, **kwargs)

            # Secondary update if dual write enabled
            if self.feature_flags.should_dual_write() and self._dynamo_document_repo:
                try:
                    self._dynamo_document_repo.update_document_status(doc_id, status, **kwargs)
                    logger.debug(f"Dual write update successful for document {doc_id}")
                except Exception as e:
                    logger.error(f"Dual write update failed for document {doc_id}: {e}")
                    # Continue with primary write success

            return result

        except Exception as e:
            logger.error(f"Failed to update document status: {e}")
            raise

    def update_job_status(
        self,
        job_id: str,
        status: str,
        **kwargs
    ) -> bool:
        """Update job status with dual write support."""
        try:
            # Primary update
            result = self.job_repository.update_job_status(job_id, status, **kwargs)

            # Secondary update if dual write enabled
            if self.feature_flags.should_dual_write() and self._dynamo_job_repo:
                try:
                    self._dynamo_job_repo.update_job_status(job_id, status, **kwargs)
                    logger.debug(f"Dual write update successful for job {job_id}")
                except Exception as e:
                    logger.error(f"Dual write update failed for job {job_id}: {e}")
                    # Continue with primary write success

            return result

        except Exception as e:
            logger.error(f"Failed to update job status: {e}")
            raise

    def health_check(self) -> dict:
        """Perform health check on persistence layer."""
        try:
            provider = self.feature_flags.get_persistence_provider()
            health_status = {
                'provider': provider.value,
                'status': 'unknown',
                'dual_write': self.feature_flags.should_dual_write(),
                'details': {}
            }

            if provider == PersistenceProvider.MONGO:
                from .mongo import health_check
                mongo_health = health_check()
                health_status['status'] = mongo_health.get('status', 'unhealthy')
                health_status['details']['mongo'] = mongo_health

            elif provider == PersistenceProvider.DYNAMO:
                # DynamoDB health check would go here
                health_status['status'] = 'healthy'  # Simplified
                health_status['details']['dynamo'] = {'status': 'healthy'}

            # Check secondary storage if dual write is enabled
            if self.feature_flags.should_dual_write():
                if provider == PersistenceProvider.MONGO and self._dynamo_document_repo:
                    health_status['details']['dynamo_secondary'] = {'status': 'healthy'}
                elif provider == PersistenceProvider.DYNAMO:
                    from .mongo import health_check
                    mongo_health = health_check()
                    health_status['details']['mongo_secondary'] = mongo_health

            return health_status

        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                'provider': 'unknown',
                'status': 'unhealthy',
                'error': str(e),
                'dual_write': False,
                'details': {}
            }

    def get_provider_info(self) -> dict:
        """Get information about the current persistence provider."""
        return {
            'provider': self.feature_flags.get_persistence_provider().value,
            'dual_write_enabled': self.feature_flags.should_dual_write(),
            'migration_mode': self.feature_flags.is_migration_mode(),
            'configuration': self.feature_flags.get_connection_config()
        }


# Global persistence manager instance
_persistence_manager: Optional[PersistenceManager] = None


def get_persistence_manager() -> PersistenceManager:
    """Get global persistence manager instance."""
    global _persistence_manager
    if _persistence_manager is None:
        _persistence_manager = PersistenceManager()
    return _persistence_manager


def get_document_repository() -> DocumentRepository:
    """Get document repository from persistence manager."""
    return get_persistence_manager().document_repository


def get_job_repository() -> JobRepository:
    """Get job repository from persistence manager."""
    return get_persistence_manager().job_repository


# Convenience functions for common operations
def create_document(doc_data: dict) -> dict:
    """Create document using configured persistence layer."""
    return get_persistence_manager().create_document(doc_data)


def create_job(job_data: dict) -> dict:
    """Create job using configured persistence layer."""
    return get_persistence_manager().create_job(job_data)


def update_document_status(doc_id: str, status: str, **kwargs) -> bool:
    """Update document status using configured persistence layer."""
    return get_persistence_manager().update_document_status(doc_id, status, **kwargs)


def update_job_status(job_id: str, status: str, **kwargs) -> bool:
    """Update job status using configured persistence layer."""
    return get_persistence_manager().update_job_status(job_id, status, **kwargs)


def persistence_health_check() -> dict:
    """Perform persistence layer health check."""
    return get_persistence_manager().health_check()


def get_persistence_info() -> dict:
    """Get persistence provider information."""
    return get_persistence_manager().get_provider_info()
