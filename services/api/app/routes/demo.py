"""
Demo Session Management Routes

Endpoints for managing demo sessions and claiming anonymous uploads after authentication.
"""

from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from pydantic import BaseModel, Field

from services.shared.mongo.demo_sessions import get_demo_session_repository
from services.shared.mongo.documents import get_document_repository

from ..auth import User, get_current_user

router = APIRouter(prefix="/demo", tags=["demo"])


class ClaimSessionRequest(BaseModel):
    """Request to claim a demo session"""
    session_id: str = Field(..., description="Session ID to claim")
    auto_claim_ip: bool = Field(
        False,
        description="Also claim other sessions from same IP"
    )


class ClaimSessionResponse(BaseModel):
    """Response after claiming a session"""
    claimed: bool = Field(..., description="Whether claim was successful")
    documents_claimed: int = Field(..., description="Number of documents claimed")
    sessions_claimed: int = Field(..., description="Number of sessions claimed")
    document_ids: list[str] = Field(..., description="List of claimed document IDs")


@router.post(
    "/claim-session",
    response_model=ClaimSessionResponse,
    summary="Claim demo uploads after authentication",
    description="Transfer ownership of demo uploads to authenticated user",
)
async def claim_demo_session(
    request_obj: ClaimSessionRequest,
    current_user: User = Depends(get_current_user),
    request: Request = None,
) -> ClaimSessionResponse:
    """
    Claim a demo session and transfer all its documents to the authenticated user.

    This is called after a user signs up or logs in to claim their anonymous uploads.
    """

    demo_repo = get_demo_session_repository()
    doc_repo = get_document_repository()

    claimed_sessions = []
    all_document_ids = []

    # Claim the specific session
    if demo_repo.claim_session(request_obj.session_id, current_user.id):
        claimed_sessions.append(request_obj.session_id)

        # Get documents from this session
        doc_ids = demo_repo.get_session_documents(request_obj.session_id)
        all_document_ids.extend(doc_ids)

    # Optionally claim other sessions from same IP
    if request_obj.auto_claim_ip and request and request.client:
        client_ip = request.client.host

        # Find other unclaimed sessions from same IP
        ip_sessions = demo_repo.get_unclaimed_sessions_by_ip(client_ip, limit=10)

        for session in ip_sessions:
            if session.session_id != request_obj.session_id:
                if demo_repo.claim_session(session.session_id, current_user.id):
                    claimed_sessions.append(session.session_id)
                    all_document_ids.extend(session.document_ids)

    # Update document ownership in the documents collection
    documents_updated = 0
    for doc_id in all_document_ids:
        # Update the document to be owned by the actual user
        result = doc_repo.update_document_owner(
            doc_id=doc_id,
            old_owner=f"demo-{request_obj.session_id}",
            new_owner=current_user.id
        )
        if result:
            documents_updated += 1

    return ClaimSessionResponse(
        claimed=len(claimed_sessions) > 0,
        documents_claimed=documents_updated,
        sessions_claimed=len(claimed_sessions),
        document_ids=all_document_ids
    )


@router.get(
    "/session/{session_id}/documents",
    summary="Get documents for a demo session",
    description="List all documents uploaded in a demo session",
)
async def get_session_documents(
    session_id: str,
    x_session_id: Optional[str] = Header(None, alias="X-Session-ID"),
) -> list[str]:
    """
    Get list of document IDs for a demo session.

    Only the session owner can view their documents.
    """

    # Verify session ownership
    if x_session_id != session_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Can only view your own session documents"
        )

    demo_repo = get_demo_session_repository()
    document_ids = demo_repo.get_session_documents(session_id)

    if not document_ids:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No documents found for this session"
        )

    return document_ids


@router.get(
    "/session/{session_id}/status",
    summary="Check demo session status",
    description="Get information about a demo session including rate limits",
)
async def get_session_status(
    session_id: str,
    x_session_id: Optional[str] = Header(None, alias="X-Session-ID"),
):
    """Get demo session status and rate limit info"""

    # Verify session ownership
    if x_session_id != session_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Can only view your own session status"
        )

    demo_repo = get_demo_session_repository()

    # Get session
    session = demo_repo.collection.find_one({"session_id": session_id})

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )

    return {
        "session_id": session_id,
        "created_at": session.get("created_at"),
        "upload_count": session.get("upload_count", 0),
        "hourly_uploads": session.get("hourly_uploads", 0),
        "hourly_reset_at": session.get("hourly_reset_at"),
        "claimed": session.get("claimed_by_user") is not None,
        "documents": session.get("document_ids", []),
        "remaining_uploads": max(0, 5 - session.get("hourly_uploads", 0))
    }
