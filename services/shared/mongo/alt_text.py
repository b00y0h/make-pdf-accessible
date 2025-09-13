"""Alt-text repository for MongoDB with versioning and audit history."""

import logging
from datetime import datetime
from typing import Optional

from pymongo import DESCENDING

from .repository import BaseRepository

logger = logging.getLogger(__name__)


class AltTextRepository(BaseRepository):
    """Repository for alt-text operations with MongoDB."""

    def __init__(self):
        super().__init__("alt_text")

    def get_document_alt_text(self, doc_id: str) -> Optional[dict]:
        """Get alt text data for a document."""
        try:
            return self.find_one({"docId": doc_id}, hint={"docId": 1})
        except Exception as e:
            logger.error(f"Error getting alt text for document {doc_id}: {e}")
            return None

    def create_document_alt_text(self, doc_id: str, figures_data: list[dict]) -> dict:
        """Create initial alt text document with AI-generated content."""
        try:
            now = datetime.utcnow()

            # Process figures and create initial versions
            figures = []
            for figure_data in figures_data:
                figure_id = figure_data.get("figure_id")
                ai_text = figure_data.get("alt_text", "")
                confidence = figure_data.get("confidence")

                # Create initial AI version
                initial_version = {
                    "version": 1,
                    "text": ai_text,
                    "editor_id": "system",
                    "editor_name": "AI System",
                    "timestamp": now,
                    "comment": f'AI generated ({figure_data.get("generation_method", "unknown")})',
                    "is_ai_generated": True,
                    "confidence": confidence,
                }

                figure = {
                    "figure_id": figure_id,
                    "status": "needs_review" if ai_text else "pending",
                    "current_version": 1,
                    "ai_text": ai_text,
                    "approved_text": None,
                    "confidence": confidence,
                    "generation_method": figure_data.get("generation_method"),
                    "versions": [initial_version],
                    "context": figure_data.get("context", {}),
                    "bounding_box": figure_data.get("bounding_box"),
                    "page_number": figure_data.get("page_number"),
                }
                figures.append(figure)

            # Create document record
            doc_data = {
                "docId": doc_id,
                "figures": figures,
                "total_figures": len(figures),
                "pending_review": len(
                    [f for f in figures if f["status"] == "needs_review"]
                ),
                "approved": 0,
                "edited": 0,
                "created_at": now,
                "updated_at": now,
            }

            return self.create(doc_data)

        except Exception as e:
            logger.error(f"Error creating alt text for document {doc_id}: {e}")
            raise

    def edit_figure_alt_text(
        self,
        doc_id: str,
        figure_id: str,
        new_text: str,
        editor_id: str,
        editor_name: Optional[str] = None,
        comment: Optional[str] = None,
    ) -> bool:
        """Edit alt text for a specific figure, creating a new version."""
        try:
            now = datetime.utcnow()

            # First, get the current document to find the figure
            doc = self.find_one({"docId": doc_id})
            if not doc:
                logger.error(f"Document {doc_id} not found")
                return False

            # Find the figure and get the next version number
            figure_index = None
            next_version = 1

            for i, figure in enumerate(doc.get("figures", [])):
                if figure["figure_id"] == figure_id:
                    figure_index = i
                    next_version = (
                        max([v.get("version", 0) for v in figure.get("versions", [])])
                        + 1
                    )
                    break

            if figure_index is None:
                logger.error(f"Figure {figure_id} not found in document {doc_id}")
                return False

            # Create new version
            new_version = {
                "version": next_version,
                "text": new_text,
                "editor_id": editor_id,
                "editor_name": editor_name or editor_id,
                "timestamp": now,
                "comment": comment,
                "is_ai_generated": False,
                "confidence": None,
            }

            # Determine new status
            current_figure = doc["figures"][figure_index]
            new_status = "edited"
            if current_figure.get("status") == "approved":
                new_status = "edited"  # Approved -> Edited when modified

            # Update the figure
            update_doc = {
                "$push": {f"figures.{figure_index}.versions": new_version},
                "$set": {
                    f"figures.{figure_index}.current_version": next_version,
                    f"figures.{figure_index}.status": new_status,
                    f"figures.{figure_index}.approved_text": (
                        new_text
                        if new_status == "approved"
                        else current_figure.get("approved_text")
                    ),
                    "updated_at": now,
                },
            }

            # Update counters
            self._update_status_counters(doc_id)

            result = self.update_one({"docId": doc_id}, update_doc)

            return result.modified_count > 0

        except Exception as e:
            logger.error(
                f"Error editing alt text for figure {figure_id} in document {doc_id}: {e}"
            )
            return False

    def update_figure_status(
        self,
        doc_id: str,
        figure_id: str,
        status: str,
        editor_id: str,
        editor_name: Optional[str] = None,
        comment: Optional[str] = None,
    ) -> bool:
        """Update the status of a figure (approve, reject, etc.)."""
        try:
            now = datetime.utcnow()

            # Get current document
            doc = self.find_one({"docId": doc_id})
            if not doc:
                return False

            # Find the figure
            figure_index = None
            for i, figure in enumerate(doc.get("figures", [])):
                if figure["figure_id"] == figure_id:
                    figure_index = i
                    break

            if figure_index is None:
                return False

            current_figure = doc["figures"][figure_index]
            update_fields = {
                f"figures.{figure_index}.status": status,
                "updated_at": now,
            }

            # If approving, set approved_text to current version's text
            if status == "approved":
                current_version_num = current_figure.get("current_version", 1)
                current_text = None

                for version in current_figure.get("versions", []):
                    if version.get("version") == current_version_num:
                        current_text = version.get("text")
                        break

                if current_text:
                    update_fields[f"figures.{figure_index}.approved_text"] = (
                        current_text
                    )

                # Add approval version if there was a comment
                if comment:
                    next_version = (
                        max(
                            [
                                v.get("version", 0)
                                for v in current_figure.get("versions", [])
                            ]
                        )
                        + 1
                    )
                    approval_version = {
                        "version": next_version,
                        "text": current_text,
                        "editor_id": editor_id,
                        "editor_name": editor_name or editor_id,
                        "timestamp": now,
                        "comment": f"Approved: {comment}",
                        "is_ai_generated": False,
                        "confidence": None,
                    }

                    self.update_one(
                        {"docId": doc_id},
                        {
                            "$push": {
                                f"figures.{figure_index}.versions": approval_version
                            },
                            "$set": {
                                f"figures.{figure_index}.current_version": next_version
                            },
                        },
                    )

            # Update the status
            result = self.update_one({"docId": doc_id}, {"$set": update_fields})

            # Update counters
            self._update_status_counters(doc_id)

            return result.modified_count > 0

        except Exception as e:
            logger.error(f"Error updating status for figure {figure_id}: {e}")
            return False

    def bulk_update_status(
        self,
        doc_id: str,
        figure_ids: list[str],
        status: str,
        editor_id: str,
        editor_name: Optional[str] = None,
        comment: Optional[str] = None,
    ) -> int:
        """Update status for multiple figures."""
        try:
            updated_count = 0
            for figure_id in figure_ids:
                if self.update_figure_status(
                    doc_id, figure_id, status, editor_id, editor_name, comment
                ):
                    updated_count += 1
            return updated_count

        except Exception as e:
            logger.error(f"Error bulk updating status: {e}")
            return 0

    def get_figure_history(self, doc_id: str, figure_id: str) -> Optional[dict]:
        """Get the complete history for a specific figure."""
        try:
            doc = self.find_one(
                {"docId": doc_id, "figures.figure_id": figure_id}, {"figures.$": 1}
            )

            if doc and "figures" in doc and doc["figures"]:
                figure = doc["figures"][0]
                return {
                    "figure_id": figure_id,
                    "versions": sorted(
                        figure.get("versions", []), key=lambda x: x.get("version", 0)
                    ),
                    "current_version": figure.get("current_version", 1),
                    "status": figure.get("status", "pending"),
                }

            return None

        except Exception as e:
            logger.error(f"Error getting history for figure {figure_id}: {e}")
            return None

    def revert_to_version(
        self,
        doc_id: str,
        figure_id: str,
        version: int,
        editor_id: str,
        editor_name: Optional[str] = None,
    ) -> bool:
        """Revert a figure to a specific version."""
        try:
            now = datetime.utcnow()

            # Get the document and find the figure
            doc = self.find_one({"docId": doc_id})
            if not doc:
                return False

            figure_index = None
            target_text = None

            for i, figure in enumerate(doc.get("figures", [])):
                if figure["figure_id"] == figure_id:
                    figure_index = i
                    # Find the target version text
                    for ver in figure.get("versions", []):
                        if ver.get("version") == version:
                            target_text = ver.get("text")
                            break
                    break

            if figure_index is None or target_text is None:
                return False

            # Create a new version that reverts to the old text
            current_figure = doc["figures"][figure_index]
            next_version = (
                max([v.get("version", 0) for v in current_figure.get("versions", [])])
                + 1
            )

            revert_version = {
                "version": next_version,
                "text": target_text,
                "editor_id": editor_id,
                "editor_name": editor_name or editor_id,
                "timestamp": now,
                "comment": f"Reverted to version {version}",
                "is_ai_generated": False,
                "confidence": None,
            }

            # Update the figure
            result = self.update_one(
                {"docId": doc_id},
                {
                    "$push": {f"figures.{figure_index}.versions": revert_version},
                    "$set": {
                        f"figures.{figure_index}.current_version": next_version,
                        f"figures.{figure_index}.status": "edited",
                        "updated_at": now,
                    },
                },
            )

            self._update_status_counters(doc_id)
            return result.modified_count > 0

        except Exception as e:
            logger.error(
                f"Error reverting figure {figure_id} to version {version}: {e}"
            )
            return False

    def _update_status_counters(self, doc_id: str) -> bool:
        """Update the status counters for a document."""
        try:
            pipeline = [
                {"$match": {"docId": doc_id}},
                {"$unwind": "$figures"},
                {"$group": {"_id": "$figures.status", "count": {"$sum": 1}}},
            ]

            results = list(self.collection.aggregate(pipeline))
            status_counts = {result["_id"]: result["count"] for result in results}

            update_doc = {
                "pending_review": status_counts.get("needs_review", 0),
                "approved": status_counts.get("approved", 0),
                "edited": status_counts.get("edited", 0),
                "updated_at": datetime.utcnow(),
            }

            self.update_one({"docId": doc_id}, {"$set": update_doc})
            return True

        except Exception as e:
            logger.error(f"Error updating status counters for document {doc_id}: {e}")
            return False

    def delete_document_alt_text(self, doc_id: str) -> bool:
        """Delete all alt text data for a document."""
        try:
            result = self.delete_one({"docId": doc_id})
            return result.deleted_count > 0
        except Exception as e:
            logger.error(f"Error deleting alt text for document {doc_id}: {e}")
            return False

    def get_documents_needing_review(self, limit: int = 50) -> list[dict]:
        """Get documents that have figures needing review."""
        try:
            return self.find(
                {"pending_review": {"$gt": 0}},
                sort=[("updated_at", DESCENDING)],
                limit=limit,
            )
        except Exception as e:
            logger.error(f"Error getting documents needing review: {e}")
            return []


# Global repository instance
_alt_text_repository = None


def get_alt_text_repository() -> AltTextRepository:
    """Get global alt text repository instance."""
    global _alt_text_repository
    if _alt_text_repository is None:
        _alt_text_repository = AltTextRepository()
    return _alt_text_repository
