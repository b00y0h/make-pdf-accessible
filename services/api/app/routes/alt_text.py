from typing import Optional
from uuid import UUID

from aws_lambda_powertools import Logger, Metrics, Tracer
from fastapi import APIRouter, Depends, HTTPException, Query, status

from ..auth import User, get_current_user, require_roles
from ..models import (
    AltTextBulkStatusRequest,
    AltTextDocumentResponse,
    AltTextEditRequest,
    AltTextEditResponse,
    AltTextHistoryResponse,
    AltTextStatus,
    UserRole,
)
from ..services import AWSServiceError, alt_text_service

logger = Logger()
tracer = Tracer()
metrics = Metrics()

router = APIRouter(prefix="/documents", tags=["alt-text"])


@router.get(
    "/{document_id}/alt-text",
    response_model=AltTextDocumentResponse,
    summary="Get document alt text data",
    description="Get all figures with AI text, current approved text, and version history for review.",
)
@tracer.capture_method
async def get_document_alt_text(
    document_id: UUID,
    status_filter: Optional[AltTextStatus] = Query(
        None, description="Filter by figure status"
    ),
    current_user: User = Depends(get_current_user),
) -> AltTextDocumentResponse:
    """Get alt text data for document review"""

    try:
        alt_text_data = await alt_text_service.get_document_alt_text(
            doc_id=str(document_id),
            user_id=current_user.sub if not current_user.is_admin() else None,
            status_filter=status_filter,
        )

        if not alt_text_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Alt text data not found or access denied",
            )

        metrics.add_metric(name="AltTextRetrievals", unit="Count", value=1)

        logger.info(
            "Alt text data retrieved",
            extra={
                "doc_id": str(document_id),
                "user_id": current_user.sub,
                "figures_count": alt_text_data.total_figures,
                "status_filter": status_filter.value if status_filter else None,
            },
        )

        return alt_text_data

    except AWSServiceError as e:
        logger.error(f"Failed to get alt text for document {document_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve alt text data",
        )


@router.patch(
    "/{document_id}/alt-text",
    response_model=AltTextEditResponse,
    summary="Edit figure alt text",
    description="Edit alt text for a specific figure, creating a new version with editor and timestamp.",
)
@tracer.capture_method
async def edit_figure_alt_text(
    document_id: UUID,
    edit_request: AltTextEditRequest,
    current_user: User = Depends(get_current_user),
) -> AltTextEditResponse:
    """Edit alt text for a figure"""

    try:
        # Verify user has access to the document
        if not current_user.is_admin():
            has_access = await alt_text_service.verify_document_access(
                doc_id=str(document_id), user_id=current_user.sub
            )
            if not has_access:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied to this document",
                )

        edit_response = await alt_text_service.edit_figure_alt_text(
            doc_id=str(document_id),
            figure_id=edit_request.figure_id,
            new_text=edit_request.text,
            editor_id=current_user.sub,
            editor_name=getattr(current_user, "name", current_user.sub),
            comment=edit_request.comment,
        )

        if not edit_response:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Figure not found or could not be updated",
            )

        metrics.add_metric(name="AltTextEdits", unit="Count", value=1)

        logger.info(
            "Alt text edited",
            extra={
                "doc_id": str(document_id),
                "figure_id": edit_request.figure_id,
                "user_id": current_user.sub,
                "new_version": edit_response.version,
            },
        )

        return edit_response

    except AWSServiceError as e:
        logger.error(
            f"Failed to edit alt text for figure {edit_request.figure_id}: {e}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update alt text",
        )


@router.patch(
    "/{document_id}/alt-text/status",
    summary="Update figure status",
    description="Update status for one or more figures (approve, reject, etc.)",
)
@tracer.capture_method
async def update_figure_status(
    document_id: UUID,
    status_request: AltTextBulkStatusRequest,
    current_user: User = Depends(get_current_user),
) -> dict:
    """Update status for multiple figures"""

    try:
        # Verify user has access to the document
        if not current_user.is_admin():
            has_access = await alt_text_service.verify_document_access(
                doc_id=str(document_id), user_id=current_user.sub
            )
            if not has_access:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied to this document",
                )

        updated_count = await alt_text_service.bulk_update_status(
            doc_id=str(document_id),
            figure_ids=status_request.figure_ids,
            status=status_request.status,
            editor_id=current_user.sub,
            editor_name=getattr(current_user, "name", current_user.sub),
            comment=status_request.comment,
        )

        metrics.add_metric(
            name="AltTextStatusUpdates", unit="Count", value=updated_count
        )

        logger.info(
            "Alt text status updated",
            extra={
                "doc_id": str(document_id),
                "figure_ids": status_request.figure_ids,
                "new_status": status_request.status.value,
                "user_id": current_user.sub,
                "updated_count": updated_count,
            },
        )

        return {
            "updated_count": updated_count,
            "figure_ids": status_request.figure_ids[:updated_count],
            "status": status_request.status,
            "comment": status_request.comment,
        }

    except AWSServiceError as e:
        logger.error(f"Failed to update status for figures: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update figure status",
        )


@router.get(
    "/{document_id}/alt-text/{figure_id}/history",
    response_model=AltTextHistoryResponse,
    summary="Get figure history",
    description="Get complete version history for a specific figure.",
)
@tracer.capture_method
async def get_figure_history(
    document_id: UUID, figure_id: str, current_user: User = Depends(get_current_user)
) -> AltTextHistoryResponse:
    """Get version history for a specific figure"""

    try:
        # Verify user has access to the document
        if not current_user.is_admin():
            has_access = await alt_text_service.verify_document_access(
                doc_id=str(document_id), user_id=current_user.sub
            )
            if not has_access:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied to this document",
                )

        history = await alt_text_service.get_figure_history(
            doc_id=str(document_id), figure_id=figure_id
        )

        if not history:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Figure not found"
            )

        metrics.add_metric(name="AltTextHistoryRequests", unit="Count", value=1)

        return history

    except AWSServiceError as e:
        logger.error(f"Failed to get history for figure {figure_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve figure history",
        )


@router.post(
    "/{document_id}/alt-text/{figure_id}/revert/{version}",
    response_model=AltTextEditResponse,
    summary="Revert to previous version",
    description="Revert a figure's alt text to a specific previous version.",
)
@tracer.capture_method
async def revert_to_version(
    document_id: UUID,
    figure_id: str,
    version: int,
    current_user: User = Depends(get_current_user),
) -> AltTextEditResponse:
    """Revert figure to a previous version"""

    try:
        # Verify user has access to the document
        if not current_user.is_admin():
            has_access = await alt_text_service.verify_document_access(
                doc_id=str(document_id), user_id=current_user.sub
            )
            if not has_access:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied to this document",
                )

        revert_response = await alt_text_service.revert_to_version(
            doc_id=str(document_id),
            figure_id=figure_id,
            version=version,
            editor_id=current_user.sub,
            editor_name=getattr(current_user, "name", current_user.sub),
        )

        if not revert_response:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Figure or version not found",
            )

        metrics.add_metric(name="AltTextReverts", unit="Count", value=1)

        logger.info(
            "Alt text reverted",
            extra={
                "doc_id": str(document_id),
                "figure_id": figure_id,
                "target_version": version,
                "new_version": revert_response.version,
                "user_id": current_user.sub,
            },
        )

        return revert_response

    except AWSServiceError as e:
        logger.error(f"Failed to revert figure {figure_id} to version {version}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to revert to previous version",
        )


@router.get(
    "/alt-text/dashboard",
    summary="Alt text review dashboard",
    description="Get summary statistics for alt text review across all documents.",
)
@tracer.capture_method
async def get_alt_text_dashboard(
    current_user: User = Depends(require_roles([UserRole.ADMIN])),
) -> dict:
    """Get alt text review dashboard statistics"""

    try:
        dashboard_data = await alt_text_service.get_dashboard_stats()

        metrics.add_metric(name="AltTextDashboard", unit="Count", value=1)

        return dashboard_data

    except AWSServiceError as e:
        logger.error(f"Failed to get dashboard data: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve dashboard data",
        )
