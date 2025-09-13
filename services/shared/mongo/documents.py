"""Document repository for MongoDB with specialized document operations."""

import logging
from datetime import datetime, timedelta
from typing import Optional

from pymongo import ASCENDING, DESCENDING

from .repository import BaseRepository

logger = logging.getLogger(__name__)


class DocumentRepository(BaseRepository):
    """Repository for document operations with MongoDB."""

    def __init__(self):
        super().__init__("documents")

    def create_document(self, doc_data: dict) -> dict:
        """Create a new document with validation."""
        try:
            # Validate required fields
            required_fields = ["docId", "ownerId", "status"]
            for field in required_fields:
                if field not in doc_data:
                    raise ValueError(f"Missing required field: {field}")

            # Set default values
            now = datetime.utcnow()
            doc_data.setdefault("createdAt", now)
            doc_data.setdefault("updatedAt", now)
            doc_data.setdefault("metadata", {})
            doc_data.setdefault("artifacts", {})
            doc_data.setdefault("scores", {})
            doc_data.setdefault("issues", [])
            doc_data.setdefault("ai", {})

            return self.create(doc_data)

        except Exception as e:
            logger.error(f"Error creating document: {e}")
            raise

    def get_document(self, doc_id: str) -> Optional[dict]:
        """Get document by docId."""
        return self.find_one({"docId": doc_id}, hint={"docId": 1})

    def get_documents_by_owner(
        self,
        owner_id: str,
        status_filter: Optional[list[str]] = None,
        page: int = 1,
        limit: int = 10,
        sort_by: str = "createdAt",
        sort_order: str = "desc",
    ) -> dict:
        """Get documents for a specific owner with filtering and pagination."""
        try:
            # Build filter
            filter_doc = {"ownerId": owner_id}

            if status_filter:
                filter_doc["status"] = {"$in": status_filter}

            # Build sort
            sort_direction = DESCENDING if sort_order == "desc" else ASCENDING
            sort = [(sort_by, sort_direction)]

            # Use appropriate index hint
            hint = {"ownerId": 1, "createdAt": -1}

            return self.paginate(
                filter_doc=filter_doc, page=page, limit=limit, sort=sort, hint=hint
            )

        except Exception as e:
            logger.error(f"Error getting documents for owner {owner_id}: {e}")
            return {
                "documents": [],
                "total": 0,
                "page": page,
                "limit": limit,
                "total_pages": 0,
                "has_next": False,
                "has_prev": False,
            }

    def get_documents_by_status(
        self, status: str, limit: Optional[int] = None, sort_by_priority: bool = False
    ) -> list[dict]:
        """Get documents by status, optionally prioritizing high-priority documents."""
        try:
            filter_doc = {"status": status}

            # Build sort order
            if sort_by_priority:
                sort = [("metadata.priority", DESCENDING), ("createdAt", ASCENDING)]
                hint = {"metadata.priority": -1, "status": 1, "createdAt": 1}
            else:
                sort = [("updatedAt", DESCENDING)]
                hint = {"status": 1, "updatedAt": -1}

            return self.find(filter_doc=filter_doc, sort=sort, limit=limit, hint=hint)

        except Exception as e:
            logger.error(f"Error getting documents by status {status}: {e}")
            return []

    def update_document_status(
        self,
        doc_id: str,
        status: str,
        error_message: Optional[str] = None,
        completed_at: Optional[datetime] = None,
        additional_data: Optional[dict] = None,
    ) -> bool:
        """Update document status and related fields."""
        try:
            update_doc = {"$set": {"status": status, "updatedAt": datetime.utcnow()}}

            if error_message is not None:
                update_doc["$set"]["errorMessage"] = error_message

            if completed_at is not None:
                update_doc["$set"]["completedAt"] = completed_at
            elif status == "completed":
                update_doc["$set"]["completedAt"] = datetime.utcnow()

            if additional_data:
                update_doc["$set"].update(additional_data)

            return self.update_by_id(
                doc_id=doc_id, update=update_doc, hint={"docId": 1}
            )

        except Exception as e:
            logger.error(f"Error updating document status for {doc_id}: {e}")
            return False

    def update_artifacts(self, doc_id: str, artifacts: dict) -> bool:
        """Update document artifacts."""
        try:
            update_doc = {
                "$set": {"artifacts": artifacts, "updatedAt": datetime.utcnow()}
            }

            return self.update_by_id(
                doc_id=doc_id, update=update_doc, hint={"docId": 1}
            )

        except Exception as e:
            logger.error(f"Error updating artifacts for document {doc_id}: {e}")
            return False

    def update_scores(self, doc_id: str, scores: dict) -> bool:
        """Update document accessibility scores."""
        try:
            update_doc = {"$set": {"scores": scores, "updatedAt": datetime.utcnow()}}

            return self.update_by_id(
                doc_id=doc_id, update=update_doc, hint={"docId": 1}
            )

        except Exception as e:
            logger.error(f"Error updating scores for document {doc_id}: {e}")
            return False

    def update_issues(self, doc_id: str, issues: list[dict]) -> bool:
        """Update document accessibility issues."""
        try:
            update_doc = {"$set": {"issues": issues, "updatedAt": datetime.utcnow()}}

            return self.update_by_id(
                doc_id=doc_id, update=update_doc, hint={"docId": 1}
            )

        except Exception as e:
            logger.error(f"Error updating issues for document {doc_id}: {e}")
            return False

    def update_ai_manifest(self, doc_id: str, ai_data: dict) -> bool:
        """Update AI processing manifest."""
        try:
            update_doc = {"$set": {"ai": ai_data, "updatedAt": datetime.utcnow()}}

            return self.update_by_id(
                doc_id=doc_id, update=update_doc, hint={"docId": 1}
            )

        except Exception as e:
            logger.error(f"Error updating AI manifest for document {doc_id}: {e}")
            return False

    def search_documents(
        self, owner_id: str, search_term: str, page: int = 1, limit: int = 10
    ) -> dict:
        """Search documents by filename using text search."""
        try:
            filter_doc = {"ownerId": owner_id, "$text": {"$search": search_term}}

            # Sort by text score relevance
            sort = [("score", {"$meta": "textScore"})]
            projection = {"score": {"$meta": "textScore"}}

            return self.paginate(
                filter_doc=filter_doc,
                page=page,
                limit=limit,
                sort=sort,
                projection=projection,
            )

        except Exception as e:
            logger.error(f"Error searching documents for owner {owner_id}: {e}")
            return {
                "documents": [],
                "total": 0,
                "page": page,
                "limit": limit,
                "total_pages": 0,
                "has_next": False,
                "has_prev": False,
            }

    def get_processing_summary(self) -> dict:
        """Get processing summary statistics."""
        try:
            pipeline = [
                {
                    "$group": {
                        "_id": "$status",
                        "count": {"$sum": 1},
                        "avg_processing_time": {
                            "$avg": {
                                "$cond": [
                                    {"$ne": ["$ai.totalProcessingTimeSeconds", None]},
                                    "$ai.totalProcessingTimeSeconds",
                                    None,
                                ]
                            }
                        },
                    }
                },
                {
                    "$group": {
                        "_id": None,
                        "total_documents": {"$sum": "$count"},
                        "documents_by_status": {
                            "$push": {"status": "$_id", "count": "$count"}
                        },
                        "avg_processing_time": {"$avg": "$avg_processing_time"},
                    }
                },
            ]

            results = self.aggregate(pipeline)

            if not results:
                return {
                    "total_documents": 0,
                    "completed_documents": 0,
                    "failed_documents": 0,
                    "processing_documents": 0,
                    "pending_documents": 0,
                    "completion_rate": 0,
                    "avg_processing_time_hours": 0,
                }

            result = results[0]
            status_counts = {
                item["status"]: item["count"] for item in result["documents_by_status"]
            }

            total = result["total_documents"]
            completed = status_counts.get("completed", 0)
            completion_rate = completed / total if total > 0 else 0

            return {
                "total_documents": total,
                "completed_documents": completed,
                "failed_documents": status_counts.get("failed", 0),
                "processing_documents": status_counts.get("processing", 0),
                "pending_documents": status_counts.get("pending", 0),
                "completion_rate": completion_rate,
                "avg_processing_time_hours": (result["avg_processing_time"] or 0)
                / 3600,
            }

        except Exception as e:
            logger.error(f"Error getting processing summary: {e}")
            return {
                "total_documents": 0,
                "completed_documents": 0,
                "failed_documents": 0,
                "processing_documents": 0,
                "pending_documents": 0,
                "completion_rate": 0,
                "avg_processing_time_hours": 0,
            }

    def get_weekly_stats(self, weeks: int = 4) -> list[dict]:
        """Get weekly processing statistics."""
        try:
            start_date = datetime.utcnow() - timedelta(weeks=weeks)

            pipeline = [
                {"$match": {"createdAt": {"$gte": start_date}}},
                {
                    "$group": {
                        "_id": {
                            "year": {"$year": "$createdAt"},
                            "week": {"$week": "$createdAt"},
                        },
                        "documents": {"$sum": 1},
                        "completed": {
                            "$sum": {"$cond": [{"$eq": ["$status", "completed"]}, 1, 0]}
                        },
                        "failed": {
                            "$sum": {"$cond": [{"$eq": ["$status", "failed"]}, 1, 0]}
                        },
                    }
                },
                {"$sort": {"_id.year": 1, "_id.week": 1}},
            ]

            results = self.aggregate(pipeline)

            return [
                {
                    "week": f"{result['_id']['year']}-W{result['_id']['week']:02d}",
                    "documents": result["documents"],
                    "completed": result["completed"],
                    "failed": result["failed"],
                    "success_rate": (
                        result["completed"] / result["documents"]
                        if result["documents"] > 0
                        else 0
                    ),
                }
                for result in results
            ]

        except Exception as e:
            logger.error(f"Error getting weekly stats: {e}")
            return []

    def cleanup_old_documents(self, days: int = 90) -> int:
        """Clean up documents older than specified days (completed or failed only)."""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)

            filter_doc = {
                "createdAt": {"$lt": cutoff_date},
                "status": {"$in": ["completed", "failed"]},
            }

            # Count documents to be deleted
            count = self.count(filter_doc)

            if count > 0:
                # Delete old documents
                result = self.collection.delete_many(filter_doc)
                deleted_count = result.deleted_count

                logger.info(f"Cleaned up {deleted_count} old documents")
                return deleted_count

            return 0

        except Exception as e:
            logger.error(f"Error cleaning up old documents: {e}")
            return 0


# Global repository instance
_document_repository = None


def get_document_repository() -> DocumentRepository:
    """Get global document repository instance."""
    global _document_repository
    if _document_repository is None:
        _document_repository = DocumentRepository()
    return _document_repository
