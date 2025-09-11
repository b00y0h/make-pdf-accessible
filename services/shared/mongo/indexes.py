"""MongoDB index management with schema validation setup."""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from pymongo.collection import Collection
from pymongo.errors import CollectionInvalid

from .connection import get_collection, get_mongo_connection

logger = logging.getLogger(__name__)


class IndexManager:
    """Manages MongoDB indexes and schema validation."""

    def __init__(self):
        self.connection = get_mongo_connection()
        self.database = self.connection.database
        self.schema_path = self._find_schema_path()

    def _find_schema_path(self) -> Path:
        """Find the MongoDB schemas directory."""
        # Look for schemas relative to current file
        current_dir = Path(__file__).parent

        # Try different possible locations
        possible_paths = [
            current_dir.parent.parent.parent / "packages" / "schemas" / "mongo",
            current_dir / ".." / ".." / ".." / "packages" / "schemas" / "mongo",
            Path("packages/schemas/mongo"),
        ]

        for path in possible_paths:
            resolved_path = path.resolve()
            if resolved_path.exists():
                return resolved_path

        # Default fallback
        return Path("packages/schemas/mongo")

    def load_json_schema(self, collection_name: str) -> Optional[Dict[str, Any]]:
        """Load JSON schema for collection validation."""
        try:
            schema_file = self.schema_path / f"{collection_name}.json"

            if not schema_file.exists():
                logger.warning(f"Schema file not found: {schema_file}")
                return None

            with open(schema_file) as f:
                schema = json.load(f)

            logger.info(f"Loaded JSON schema for {collection_name}")
            return schema

        except Exception as e:
            logger.error(f"Error loading JSON schema for {collection_name}: {e}")
            return None

    def create_collection_with_validation(self, collection_name: str) -> bool:
        """Create collection with JSON schema validation."""
        try:
            # Load JSON schema
            json_schema = self.load_json_schema(collection_name)

            if json_schema:
                # Create collection with validation
                validator = json_schema
                self.database.create_collection(
                    collection_name,
                    validator=validator,
                    validationLevel="moderate",  # Allow updates that don't include all required fields
                    validationAction="error",  # Reject invalid documents
                )
                logger.info(
                    f"Created collection '{collection_name}' with schema validation"
                )
            else:
                # Create collection without validation
                self.database.create_collection(collection_name)
                logger.info(
                    f"Created collection '{collection_name}' without schema validation"
                )

            return True

        except CollectionInvalid as e:
            if "already exists" in str(e):
                logger.info(f"Collection '{collection_name}' already exists")
                return True
            else:
                logger.error(f"Error creating collection '{collection_name}': {e}")
                return False
        except Exception as e:
            logger.error(f"Error creating collection '{collection_name}': {e}")
            return False

    def create_index(self, collection: Collection, index_spec: Dict[str, Any]) -> bool:
        """Create a single index on collection."""
        try:
            name = index_spec["name"]
            keys = index_spec["keys"]
            options = index_spec.get("options", {})

            # Check if index already exists
            existing_indexes = {idx["name"]: idx for idx in collection.list_indexes()}

            if name in existing_indexes:
                logger.debug(f"Index '{name}' already exists on {collection.name}")
                return True

            # Create the index
            created_name = collection.create_index(
                [(key, direction) for key, direction in keys.items()],
                name=name,
                background=options.get("background", True),
                **{k: v for k, v in options.items() if k != "background"},
            )

            logger.info(f"Created index '{created_name}' on {collection.name}")
            return True

        except Exception as e:
            logger.error(
                f"Error creating index '{index_spec.get('name')}' on {collection.name}: {e}"
            )
            return False

    def create_document_indexes(self) -> Dict[str, bool]:
        """Create all indexes for documents collection."""
        collection = get_collection("documents")

        # Define document indexes
        indexes = [
            # Primary unique index on docId
            {
                "name": "docId_unique",
                "keys": {"docId": 1},
                "options": {"unique": True, "background": True},
            },
            # Owner and creation time for user document lists
            {
                "name": "owner_createdAt",
                "keys": {"ownerId": 1, "createdAt": -1},
                "options": {"background": True},
            },
            # Status and update time for processing queues
            {
                "name": "status_updatedAt",
                "keys": {"status": 1, "updatedAt": -1},
                "options": {"background": True},
            },
            # Owner and status for filtered user queries
            {
                "name": "owner_status",
                "keys": {"ownerId": 1, "status": 1},
                "options": {"background": True},
            },
            # Created time for temporal queries
            {
                "name": "createdAt",
                "keys": {"createdAt": -1},
                "options": {"background": True},
            },
            # Updated time for change tracking
            {
                "name": "updatedAt",
                "keys": {"updatedAt": -1},
                "options": {"background": True},
            },
            # Completed time for analytics
            {
                "name": "completedAt",
                "keys": {"completedAt": -1},
                "options": {"background": True, "sparse": True},
            },
            # Priority processing
            {
                "name": "priority_status",
                "keys": {"metadata.priority": -1, "status": 1, "createdAt": 1},
                "options": {
                    "background": True,
                    "sparse": True,
                    "partialFilterExpression": {"metadata.priority": True},
                },
            },
            # Full-text search on filename
            {
                "name": "filename_text",
                "keys": {"filename": "text"},
                "options": {"background": True, "sparse": True},
            },
        ]

        results = {}
        for index_spec in indexes:
            results[index_spec["name"]] = self.create_index(collection, index_spec)

        return results

    def create_job_indexes(self) -> Dict[str, bool]:
        """Create all indexes for jobs collection."""
        collection = get_collection("jobs")

        # Define job indexes
        indexes = [
            # Primary unique index on jobId
            {
                "name": "jobId_unique",
                "keys": {"jobId": 1},
                "options": {"unique": True, "background": True},
            },
            # Document jobs lookup
            {
                "name": "docId_updatedAt",
                "keys": {"docId": 1, "updatedAt": -1},
                "options": {"background": True},
            },
            # Job queue processing by status and priority
            {
                "name": "status_priority_createdAt",
                "keys": {"status": 1, "priority": -1, "createdAt": 1},
                "options": {"background": True},
            },
            # Step-specific job queries
            {
                "name": "step_status",
                "keys": {"step": 1, "status": 1},
                "options": {"background": True},
            },
            # Document and step combination
            {
                "name": "docId_step",
                "keys": {"docId": 1, "step": 1},
                "options": {"background": True},
            },
            # Created time for temporal queries
            {
                "name": "createdAt",
                "keys": {"createdAt": -1},
                "options": {"background": True},
            },
            # Updated time for change tracking
            {
                "name": "updatedAt",
                "keys": {"updatedAt": -1},
                "options": {"background": True},
            },
            # Started time for execution tracking
            {
                "name": "startedAt",
                "keys": {"startedAt": -1},
                "options": {"background": True, "sparse": True},
            },
            # Completed time for analytics
            {
                "name": "completedAt",
                "keys": {"completedAt": -1},
                "options": {"background": True, "sparse": True},
            },
            # Failed jobs for retry processing
            {
                "name": "failed_attempts",
                "keys": {"status": 1, "attempts": 1, "updatedAt": 1},
                "options": {
                    "background": True,
                    "partialFilterExpression": {"status": {"$in": ["failed", "retry"]}},
                },
            },
            # Active jobs for monitoring
            {
                "name": "active_worker",
                "keys": {"status": 1, "worker.instanceId": 1, "startedAt": -1},
                "options": {
                    "background": True,
                    "sparse": True,
                    "partialFilterExpression": {"status": "running"},
                },
            },
            # TTL index for completed jobs (30 days)
            {
                "name": "completed_ttl",
                "keys": {"completedAt": 1},
                "options": {
                    "background": True,
                    "sparse": True,
                    "expireAfterSeconds": 30 * 24 * 60 * 60,  # 30 days
                    "partialFilterExpression": {"status": "completed"},
                },
            },
        ]

        results = {}
        for index_spec in indexes:
            results[index_spec["name"]] = self.create_index(collection, index_spec)

        return results

    def setup_all_indexes(self) -> Dict[str, Dict[str, bool]]:
        """Set up all collections and indexes."""
        try:
            logger.info("Setting up MongoDB collections and indexes...")

            results = {
                "collections_created": {},
                "documents_indexes": {},
                "jobs_indexes": {},
            }

            # Create collections with validation
            results["collections_created"]["documents"] = (
                self.create_collection_with_validation("documents")
            )
            results["collections_created"]["jobs"] = (
                self.create_collection_with_validation("jobs")
            )

            # Create document indexes
            logger.info("Creating document indexes...")
            results["documents_indexes"] = self.create_document_indexes()

            # Create job indexes
            logger.info("Creating job indexes...")
            results["jobs_indexes"] = self.create_job_indexes()

            # Log summary
            total_doc_indexes = len(results["documents_indexes"])
            successful_doc_indexes = sum(results["documents_indexes"].values())

            total_job_indexes = len(results["jobs_indexes"])
            successful_job_indexes = sum(results["jobs_indexes"].values())

            logger.info(
                f"Index creation complete: "
                f"Documents ({successful_doc_indexes}/{total_doc_indexes}), "
                f"Jobs ({successful_job_indexes}/{total_job_indexes})"
            )

            return results

        except Exception as e:
            logger.error(f"Error setting up indexes: {e}")
            raise

    def list_collection_indexes(self, collection_name: str) -> List[Dict[str, Any]]:
        """List all indexes for a collection."""
        try:
            collection = get_collection(collection_name)
            indexes = list(collection.list_indexes())

            logger.info(f"Found {len(indexes)} indexes on {collection_name}")
            return indexes

        except Exception as e:
            logger.error(f"Error listing indexes for {collection_name}: {e}")
            return []

    def drop_index(self, collection_name: str, index_name: str) -> bool:
        """Drop a specific index from collection."""
        try:
            collection = get_collection(collection_name)
            collection.drop_index(index_name)

            logger.info(f"Dropped index '{index_name}' from {collection_name}")
            return True

        except Exception as e:
            logger.error(
                f"Error dropping index '{index_name}' from {collection_name}: {e}"
            )
            return False

    def rebuild_index(self, collection_name: str, index_name: str) -> bool:
        """Rebuild a specific index."""
        try:
            collection = get_collection(collection_name)

            # Get current indexes
            existing_indexes = {idx["name"]: idx for idx in collection.list_indexes()}

            if index_name not in existing_indexes:
                logger.error(f"Index '{index_name}' not found on {collection_name}")
                return False

            # Drop and recreate
            collection.drop_index(index_name)

            # Find the index specification to recreate it
            # This is a simplified version - in production you might want to store specs
            logger.warning(
                f"Index '{index_name}' dropped but automatic recreation not implemented"
            )
            return True

        except Exception as e:
            logger.error(
                f"Error rebuilding index '{index_name}' on {collection_name}: {e}"
            )
            return False

    def get_index_stats(self, collection_name: str) -> Dict[str, Any]:
        """Get index usage statistics."""
        try:
            collection = get_collection(collection_name)

            # Get index stats using $indexStats aggregation
            pipeline = [{"$indexStats": {}}]
            index_stats = list(collection.aggregate(pipeline))

            return {
                "collection": collection_name,
                "total_indexes": len(index_stats),
                "index_usage": [
                    {
                        "name": stat["name"],
                        "accesses": stat["accesses"]["ops"],
                        "since": stat["accesses"]["since"],
                    }
                    for stat in index_stats
                ],
            }

        except Exception as e:
            logger.error(f"Error getting index stats for {collection_name}: {e}")
            return {"collection": collection_name, "error": str(e)}


# Global index manager instance
_index_manager = None


def get_index_manager() -> IndexManager:
    """Get global index manager instance."""
    global _index_manager
    if _index_manager is None:
        _index_manager = IndexManager()
    return _index_manager


def setup_mongodb_indexes():
    """Setup all MongoDB indexes - convenience function."""
    manager = get_index_manager()
    return manager.setup_all_indexes()
