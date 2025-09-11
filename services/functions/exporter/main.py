import os
import sys
from typing import Any, Dict

from fastapi import Depends, FastAPI

# Add shared services to path
sys.path.append(os.path.join(os.path.dirname(__file__), "../../shared"))

from auth import UserInfo, get_current_user, require_user_or_admin

app = FastAPI(
    title="PDF Exporter Service",
    description="Microservice for exporting accessible PDF documents",
    version="1.0.0",
)


@app.get("/")
def read_root():
    return {"message": "PDF exporter service is running"}


@app.get("/health")
def health_check():
    return {"status": "healthy"}


@app.post("/export")
def export_document(
    export_request: Dict[str, Any], current_user: UserInfo = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Export an accessible PDF document
    Requires authentication
    """
    return {
        "message": "Document export initiated",
        "user_id": current_user.sub,
        "user_role": current_user.role,
        "document_id": export_request.get("doc_id"),
        "export_format": export_request.get("format", "pdf"),
        "export_status": "in_progress",
        "estimated_completion": "1-3 minutes",
    }


@app.get("/export/{doc_id}/status")
def get_export_status(
    doc_id: str, current_user: UserInfo = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get export status for a document
    Requires authentication
    """
    return {
        "doc_id": doc_id,
        "status": "completed",
        "export_url": f"https://s3.example.com/exports/{doc_id}/accessible.pdf",
        "accessibility_features": [
            "Tagged PDF structure",
            "Alt text for images",
            "Proper heading hierarchy",
            "Accessible form fields",
        ],
        "user_id": current_user.sub,
        "expires_at": "2024-01-15T10:00:00Z",
    }


@app.get("/export/formats")
def get_supported_formats() -> Dict[str, Any]:
    """
    Get supported export formats
    Public endpoint - no authentication required
    """
    return {
        "supported_formats": [
            {
                "format": "pdf",
                "name": "Accessible PDF",
                "description": "Tagged PDF with accessibility features",
                "mime_type": "application/pdf",
            },
            {
                "format": "html",
                "name": "Accessible HTML",
                "description": "Semantic HTML with ARIA labels",
                "mime_type": "text/html",
            },
            {
                "format": "epub",
                "name": "EPUB",
                "description": "Accessible eBook format",
                "mime_type": "application/epub+zip",
            },
        ]
    }


@app.get("/export/{doc_id}/download")
def download_export(
    doc_id: str,
    format: str = "pdf",
    current_user: UserInfo = Depends(require_user_or_admin),
) -> Dict[str, Any]:
    """
    Get download link for exported document
    Requires user or admin role
    """
    # In a real implementation, you would:
    # 1. Check if user owns the document or is admin
    # 2. Generate a signed download URL
    # 3. Return the download link

    return {
        "doc_id": doc_id,
        "format": format,
        "download_url": f"https://s3.example.com/exports/{doc_id}/accessible.{format}",
        "content_type": "application/pdf" if format == "pdf" else "text/html",
        "file_size_bytes": 2845673,
        "requested_by": current_user.sub,
        "expires_in_minutes": 60,
    }
