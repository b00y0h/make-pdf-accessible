"""Base MongoDB repository with CRUD operations and query optimization."""

import logging
from abc import ABC
from dataclasses import dataclass
from datetime import datetime
from typing import Generic, List, Optional, Type, TypeVar, Union

from bson import ObjectId
from pymongo.collection import Collection
from pymongo.errors import BulkWriteError, DuplicateKeyError
from pymongo.results import DeleteResult, InsertOneResult, UpdateResult

from .connection import get_collection

logger = logging.getLogger(__name__)

T = TypeVar('T')

@dataclass
class QueryPlan:
    """Query execution plan for performance monitoring."""
    collection: str
    operation: str
    filter_doc: dict
    execution_stats: dict
    index_used: Optional[str] = None
    execution_time_ms: Optional[float] = None


class BaseRepository(Generic[T], ABC):
    """Base repository class with common MongoDB operations."""

    def __init__(self, collection_name: str, document_class: Optional[Type[T]] = None):
        self.collection_name = collection_name
        self.document_class = document_class
        self._collection: Optional[Collection] = None
        self.enable_query_logging = self._should_enable_query_logging()

    def _should_enable_query_logging(self) -> bool:
        """Check if query logging should be enabled."""
        import os
        return os.getenv('ENABLE_QUERY_LOGGING', 'false').lower() == 'true'

    @property
    def collection(self) -> Collection:
        """Get MongoDB collection instance."""
        if self._collection is None:
            self._collection = get_collection(self.collection_name)
        return self._collection

    def _log_query_plan(self, operation: str, filter_doc: dict, hint: Optional[dict] = None):
        """Log query execution plan for performance monitoring."""
        if not self.enable_query_logging:
            return

        try:
            # Get query plan
            explain_result = self.collection.find(filter_doc).hint(hint or {}).explain()
            execution_stats = explain_result.get('executionStats', {})

            query_plan = QueryPlan(
                collection=self.collection_name,
                operation=operation,
                filter_doc=filter_doc,
                execution_stats=execution_stats,
                index_used=execution_stats.get('indexName'),
                execution_time_ms=execution_stats.get('executionTimeMillis')
            )

            logger.info(f"Query Plan: {query_plan}")

        except Exception as e:
            logger.warning(f"Failed to get query plan: {e}")

    def _serialize_document(self, doc: dict) -> dict:
        """Serialize document for MongoDB storage."""
        serialized = {}
        for key, value in doc.items():
            if isinstance(value, datetime):
                serialized[key] = value
            elif isinstance(value, dict):
                serialized[key] = self._serialize_document(value)
            elif isinstance(value, list):
                serialized[key] = [
                    self._serialize_document(item) if isinstance(item, dict) else item
                    for item in value
                ]
            else:
                serialized[key] = value
        return serialized

    def _deserialize_document(self, doc: dict) -> dict:
        """Deserialize document from MongoDB storage."""
        if not doc:
            return doc

        # Convert ObjectId to string for API compatibility
        if '_id' in doc and isinstance(doc['_id'], ObjectId):
            doc['_id'] = str(doc['_id'])

        return doc

    def create(self, document: dict) -> dict:
        """Create a new document."""
        try:
            # Add timestamps
            now = datetime.utcnow()
            document['createdAt'] = document.get('createdAt', now)
            document['updatedAt'] = document.get('updatedAt', now)

            # Serialize document
            serialized_doc = self._serialize_document(document)

            # Insert document
            result: InsertOneResult = self.collection.insert_one(serialized_doc)

            # Return document with generated ID
            document['_id'] = str(result.inserted_id)

            logger.info(f"Created document in {self.collection_name}: {result.inserted_id}")
            return document

        except DuplicateKeyError as e:
            logger.error(f"Duplicate key error creating document: {e}")
            raise ValueError("Document with this identifier already exists")
        except Exception as e:
            logger.error(f"Error creating document in {self.collection_name}: {e}")
            raise

    def get_by_id(self, doc_id: str, hint: Optional[dict] = None) -> Optional[dict]:
        """Get document by ID."""
        try:
            filter_doc = {'_id': ObjectId(doc_id)} if ObjectId.is_valid(doc_id) else {'docId': doc_id}

            # Log query plan
            self._log_query_plan('find_by_id', filter_doc, hint)

            # Find document
            cursor = self.collection.find(filter_doc)
            if hint:
                cursor = cursor.hint(hint)

            doc = cursor.limit(1).next() if cursor.alive else None

            if doc:
                logger.debug(f"Found document in {self.collection_name}: {doc_id}")
                return self._deserialize_document(doc)

            return None

        except StopIteration:
            return None
        except Exception as e:
            logger.error(f"Error getting document by ID in {self.collection_name}: {e}")
            return None

    def update_by_id(
        self,
        doc_id: str,
        update: dict,
        upsert: bool = False,
        hint: Optional[dict] = None
    ) -> bool:
        """Update document by ID."""
        try:
            filter_doc = {'_id': ObjectId(doc_id)} if ObjectId.is_valid(doc_id) else {'docId': doc_id}

            # Add updated timestamp
            update.setdefault('$set', {})['updatedAt'] = datetime.utcnow()

            # Log query plan
            self._log_query_plan('update_by_id', filter_doc, hint)

            # Update document
            update_kwargs = {'upsert': upsert}
            if hint:
                update_kwargs['hint'] = hint

            result: UpdateResult = self.collection.update_one(
                filter_doc,
                update,
                **update_kwargs
            )

            success = result.modified_count > 0 or (upsert and result.upserted_id is not None)

            if success:
                logger.info(f"Updated document in {self.collection_name}: {doc_id}")

            return success

        except Exception as e:
            logger.error(f"Error updating document in {self.collection_name}: {e}")
            return False

    def delete_by_id(self, doc_id: str, hint: Optional[dict] = None) -> bool:
        """Delete document by ID."""
        try:
            filter_doc = {'_id': ObjectId(doc_id)} if ObjectId.is_valid(doc_id) else {'docId': doc_id}

            # Log query plan
            self._log_query_plan('delete_by_id', filter_doc, hint)

            # Delete document
            delete_kwargs = {}
            if hint:
                delete_kwargs['hint'] = hint

            result: DeleteResult = self.collection.delete_one(filter_doc, **delete_kwargs)

            success = result.deleted_count > 0

            if success:
                logger.info(f"Deleted document from {self.collection_name}: {doc_id}")

            return success

        except Exception as e:
            logger.error(f"Error deleting document from {self.collection_name}: {e}")
            return False

    def find(
        self,
        filter_doc: dict,
        sort: Optional[List[tuple]] = None,
        limit: Optional[int] = None,
        skip: Optional[int] = None,
        hint: Optional[dict] = None,
        projection: Optional[dict] = None
    ) -> List[dict]:
        """Find documents with filtering, sorting, and pagination."""
        try:
            # Log query plan
            self._log_query_plan('find', filter_doc, hint)

            # Build query
            cursor = self.collection.find(filter_doc, projection)

            if hint:
                cursor = cursor.hint(hint)

            if sort:
                cursor = cursor.sort(sort)

            if skip:
                cursor = cursor.skip(skip)

            if limit:
                cursor = cursor.limit(limit)

            # Execute query and deserialize results
            documents = [self._deserialize_document(doc) for doc in cursor]

            logger.debug(f"Found {len(documents)} documents in {self.collection_name}")
            return documents

        except Exception as e:
            logger.error(f"Error finding documents in {self.collection_name}: {e}")
            return []

    def find_one(
        self,
        filter_doc: dict,
        hint: Optional[dict] = None,
        projection: Optional[dict] = None
    ) -> Optional[dict]:
        """Find single document."""
        try:
            # Log query plan
            self._log_query_plan('find_one', filter_doc, hint)

            # Build query
            find_kwargs = {}
            if hint:
                find_kwargs['hint'] = hint

            doc = self.collection.find_one(filter_doc, projection, **find_kwargs)

            if doc:
                return self._deserialize_document(doc)

            return None

        except Exception as e:
            logger.error(f"Error finding document in {self.collection_name}: {e}")
            return None

    def count(self, filter_doc: dict, hint: Optional[dict] = None) -> int:
        """Count documents matching filter."""
        try:
            # Log query plan
            self._log_query_plan('count', filter_doc, hint)

            count_kwargs = {}
            if hint:
                count_kwargs['hint'] = hint

            count = self.collection.count_documents(filter_doc, **count_kwargs)

            logger.debug(f"Counted {count} documents in {self.collection_name}")
            return count

        except Exception as e:
            logger.error(f"Error counting documents in {self.collection_name}: {e}")
            return 0

    def paginate(
        self,
        filter_doc: dict,
        page: int = 1,
        limit: int = 10,
        sort: Optional[List[tuple]] = None,
        hint: Optional[dict] = None,
        projection: Optional[dict] = None
    ) -> dict:
        """Paginate query results."""
        try:
            # Calculate skip value
            skip = (page - 1) * limit

            # Get total count
            total = self.count(filter_doc, hint)

            # Get documents for current page
            documents = self.find(
                filter_doc=filter_doc,
                sort=sort,
                limit=limit,
                skip=skip,
                hint=hint,
                projection=projection
            )

            # Calculate pagination metadata
            total_pages = (total + limit - 1) // limit  # Ceiling division
            has_next = page < total_pages
            has_prev = page > 1

            return {
                'documents': documents,
                'total': total,
                'page': page,
                'limit': limit,
                'total_pages': total_pages,
                'has_next': has_next,
                'has_prev': has_prev
            }

        except Exception as e:
            logger.error(f"Error paginating documents in {self.collection_name}: {e}")
            return {
                'documents': [],
                'total': 0,
                'page': page,
                'limit': limit,
                'total_pages': 0,
                'has_next': False,
                'has_prev': False
            }

    def aggregate(self, pipeline: List[dict], hint: Optional[dict] = None) -> List[dict]:
        """Execute aggregation pipeline."""
        try:
            # Log pipeline
            if self.enable_query_logging:
                logger.info(f"Aggregation pipeline on {self.collection_name}: {pipeline}")

            # Execute aggregation
            agg_kwargs = {}
            if hint:
                agg_kwargs['hint'] = hint

            cursor = self.collection.aggregate(pipeline, **agg_kwargs)
            results = list(cursor)

            logger.debug(f"Aggregation returned {len(results)} results from {self.collection_name}")
            return results

        except Exception as e:
            logger.error(f"Error executing aggregation in {self.collection_name}: {e}")
            return []

    def bulk_write(self, operations: List[dict]) -> dict:
        """Execute bulk write operations."""
        try:
            if not operations:
                return {'inserted_count': 0, 'modified_count': 0, 'deleted_count': 0}

            result = self.collection.bulk_write(operations)

            logger.info(f"Bulk write completed in {self.collection_name}: "
                       f"inserted={result.inserted_count}, "
                       f"modified={result.modified_count}, "
                       f"deleted={result.deleted_count}")

            return {
                'inserted_count': result.inserted_count,
                'modified_count': result.modified_count,
                'deleted_count': result.deleted_count,
                'upserted_count': result.upserted_count
            }

        except BulkWriteError as e:
            logger.error(f"Bulk write error in {self.collection_name}: {e.details}")
            raise
        except Exception as e:
            logger.error(f"Error executing bulk write in {self.collection_name}: {e}")
            raise

    def create_index(self, keys: Union[str, List[tuple]], **kwargs) -> str:
        """Create index on collection."""
        try:
            index_name = self.collection.create_index(keys, **kwargs)
            logger.info(f"Created index '{index_name}' on {self.collection_name}")
            return index_name
        except Exception as e:
            logger.error(f"Error creating index on {self.collection_name}: {e}")
            raise

    def list_indexes(self) -> List[dict]:
        """List all indexes on collection."""
        try:
            indexes = list(self.collection.list_indexes())
            return indexes
        except Exception as e:
            logger.error(f"Error listing indexes on {self.collection_name}: {e}")
            return []

    def get_collection_stats(self) -> dict:
        """Get collection statistics."""
        try:
            stats = self.collection.database.command("collStats", self.collection_name)
            return {
                'count': stats.get('count', 0),
                'size': stats.get('size', 0),
                'storage_size': stats.get('storageSize', 0),
                'total_index_size': stats.get('totalIndexSize', 0),
                'index_count': stats.get('nindexes', 0)
            }
        except Exception as e:
            logger.error(f"Error getting collection stats for {self.collection_name}: {e}")
            return {}
