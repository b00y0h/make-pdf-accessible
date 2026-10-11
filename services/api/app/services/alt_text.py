"""
Alt-text service: figure review, versioning and audit history in MongoDB
"""

import logging
import uuid
from datetime import datetime
from typing import Any, Optional

from services.shared.mongo.alt_text import get_alt_text_repository
from services.shared.mongo.documents import get_document_repository

from ..models import (
    AltTextDocumentResponse,
    AltTextEditResponse,
    AltTextFigure,
    AltTextHistoryResponse,
    AltTextStatus,
    AltTextVersion,
)
from .errors import AWSServiceError

logger = logging.getLogger(__name__)


def _to_version(version_data: dict) -> AltTextVersion:
    """Convert a stored version entry to its response model"""
    return AltTextVersion(
        version=version_data.get("version", 1),
        text=version_data.get("text", ""),
        editor_id=version_data.get("editor_id", ""),
        editor_name=version_data.get("editor_name"),
        timestamp=version_data.get("timestamp"),
        comment=version_data.get("comment"),
        is_ai_generated=version_data.get("is_ai_generated", False),
        confidence=version_data.get("confidence"),
    )


class AltTextService:
    """Service for alt-text operations with versioning and audit history"""

    async def get_document_alt_text(
        self,
        doc_id: str,
        user_id: Optional[str] = None,
        status_filter: Optional[AltTextStatus] = None,
    ) -> Optional[AltTextDocumentResponse]:
        """Get alt text data for a document with optional status filtering"""
        try:
            # Verify document access if not admin
            if user_id:
                has_access = await self.verify_document_access(doc_id, user_id)
                if not has_access:
                    return None

            alt_text_doc = get_alt_text_repository().get_document_alt_text(doc_id)

            if not alt_text_doc:
                return None

            figures = []
            for figure_data in alt_text_doc.get("figures", []):
                if status_filter and figure_data.get("status") != status_filter.value:
                    continue

                figures.append(
                    AltTextFigure(
                        figure_id=figure_data.get("figure_id", ""),
                        status=AltTextStatus(figure_data.get("status", "pending")),
                        current_version=figure_data.get("current_version", 1),
                        ai_text=figure_data.get("ai_text"),
                        approved_text=figure_data.get("approved_text"),
                        confidence=figure_data.get("confidence"),
                        generation_method=figure_data.get("generation_method"),
                        versions=[
                            _to_version(version_data)
                            for version_data in figure_data.get("versions", [])
                        ],
                        context=figure_data.get("context", {}),
                        bounding_box=figure_data.get("bounding_box"),
                        page_number=figure_data.get("page_number"),
                    )
                )

            return AltTextDocumentResponse(
                doc_id=uuid.UUID(doc_id),
                figures=figures,
                total_figures=alt_text_doc.get("total_figures", 0),
                pending_review=alt_text_doc.get("pending_review", 0),
                approved=alt_text_doc.get("approved", 0),
                edited=alt_text_doc.get("edited", 0),
                last_updated=alt_text_doc.get("updated_at", datetime.utcnow()),
            )

        except Exception as e:
            logger.error(f"Failed to get alt text for document {doc_id}: {e}")
            raise AWSServiceError(f"Failed to get alt text: {e}") from e

    async def edit_figure_alt_text(
        self,
        doc_id: str,
        figure_id: str,
        new_text: str,
        editor_id: str,
        editor_name: Optional[str] = None,
        comment: Optional[str] = None,
    ) -> Optional[AltTextEditResponse]:
        """Edit alt text for a figure, creating a new version"""
        try:
            alt_text_repo = get_alt_text_repository()
            success = alt_text_repo.edit_figure_alt_text(
                doc_id=doc_id,
                figure_id=figure_id,
                new_text=new_text,
                editor_id=editor_id,
                editor_name=editor_name,
                comment=comment,
            )

            if not success:
                return None

            # Read back the figure for its current version
            alt_text_doc = alt_text_repo.get_document_alt_text(doc_id)
            if not alt_text_doc:
                return None

            for figure_data in alt_text_doc.get("figures", []):
                if figure_data.get("figure_id") == figure_id:
                    return AltTextEditResponse(
                        figure_id=figure_id,
                        version=figure_data.get("current_version", 1),
                        text=new_text,
                        status=AltTextStatus(figure_data.get("status", "edited")),
                        timestamp=datetime.utcnow(),
                    )

            return None

        except Exception as e:
            logger.error(f"Failed to edit alt text for figure {figure_id}: {e}")
            raise AWSServiceError(f"Failed to edit alt text: {e}") from e

    async def bulk_update_status(
        self,
        doc_id: str,
        figure_ids: list[str],
        status: AltTextStatus,
        editor_id: str,
        editor_name: Optional[str] = None,
        comment: Optional[str] = None,
    ) -> int:
        """Update status for multiple figures"""
        try:
            return get_alt_text_repository().bulk_update_status(
                doc_id=doc_id,
                figure_ids=figure_ids,
                status=status.value,
                editor_id=editor_id,
                editor_name=editor_name,
                comment=comment,
            )

        except Exception as e:
            logger.error(f"Failed to bulk update status: {e}")
            raise AWSServiceError(f"Failed to bulk update status: {e}") from e

    async def get_figure_history(
        self, doc_id: str, figure_id: str
    ) -> Optional[AltTextHistoryResponse]:
        """Get complete history for a specific figure"""
        try:
            history_data = get_alt_text_repository().get_figure_history(
                doc_id, figure_id
            )

            if not history_data:
                return None

            return AltTextHistoryResponse(
                figure_id=figure_id,
                versions=[
                    _to_version(version_data)
                    for version_data in history_data.get("versions", [])
                ],
                current_version=history_data.get("current_version", 1),
                status=AltTextStatus(history_data.get("status", "pending")),
            )

        except Exception as e:
            logger.error(f"Failed to get history for figure {figure_id}: {e}")
            raise AWSServiceError(f"Failed to get figure history: {e}") from e

    async def revert_to_version(
        self,
        doc_id: str,
        figure_id: str,
        version: int,
        editor_id: str,
        editor_name: Optional[str] = None,
    ) -> Optional[AltTextEditResponse]:
        """Revert a figure to a specific version"""
        try:
            alt_text_repo = get_alt_text_repository()
            success = alt_text_repo.revert_to_version(
                doc_id=doc_id,
                figure_id=figure_id,
                version=version,
                editor_id=editor_id,
                editor_name=editor_name,
            )

            if not success:
                return None

            # Read back the figure for its current version
            alt_text_doc = alt_text_repo.get_document_alt_text(doc_id)
            if not alt_text_doc:
                return None

            for figure_data in alt_text_doc.get("figures", []):
                if figure_data.get("figure_id") == figure_id:
                    reverted_text = next(
                        (
                            version_data.get("text", "")
                            for version_data in figure_data.get("versions", [])
                            if version_data.get("version") == version
                        ),
                        "",
                    )

                    return AltTextEditResponse(
                        figure_id=figure_id,
                        version=figure_data.get("current_version", 1),
                        text=reverted_text,
                        status=AltTextStatus(figure_data.get("status", "edited")),
                        timestamp=datetime.utcnow(),
                    )

            return None

        except Exception as e:
            logger.error(
                f"Failed to revert figure {figure_id} to version {version}: {e}"
            )
            raise AWSServiceError(f"Failed to revert to version: {e}") from e

    async def verify_document_access(self, doc_id: str, user_id: str) -> bool:
        """Verify that a user owns a document"""
        try:
            document = get_document_repository().get_document(doc_id)
            if not document:
                return False

            return document.get("ownerId") == user_id

        except Exception as e:
            logger.error(f"Failed to verify document access for {doc_id}: {e}")
            return False

    async def get_dashboard_stats(self) -> dict[str, Any]:
        """Get alt text dashboard statistics"""
        try:
            documents_needing_review = (
                get_alt_text_repository().get_documents_needing_review(limit=100)
            )

            total_figures = sum(
                doc.get("total_figures", 0) for doc in documents_needing_review
            )
            approved = sum(doc.get("approved", 0) for doc in documents_needing_review)

            return {
                "summary": {
                    "total_documents": len(documents_needing_review),
                    "total_figures": total_figures,
                    "pending_review": sum(
                        doc.get("pending_review", 0) for doc in documents_needing_review
                    ),
                    "approved": approved,
                    "edited": sum(
                        doc.get("edited", 0) for doc in documents_needing_review
                    ),
                    "completion_rate": (
                        (approved / total_figures * 100) if total_figures > 0 else 0
                    ),
                },
                "recent_documents": documents_needing_review[:10],
            }

        except Exception as e:
            logger.error(f"Failed to get dashboard stats: {e}")
            raise AWSServiceError(f"Failed to get dashboard stats: {e}") from e


alt_text_service = AltTextService()
