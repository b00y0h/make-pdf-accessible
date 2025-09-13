import os
import sys
from typing import Any

from fastapi import Depends, FastAPI

# Add shared services to path
sys.path.append(os.path.join(os.path.dirname(__file__), "../../shared"))

from auth import UserInfo, get_current_user, optional_auth, require_admin

app = FastAPI(
    title="PDF Tagger Service",
    description="Microservice for PDF tagging and accessibility enhancement",
    version="1.0.0",
)


@app.get("/")
def read_root():
    return {"message": "PDF tagger service is running"}


@app.get("/health")
def health_check():
    return {"status": "healthy"}


@app.post("/tag")
def tag_document(
    document_data: dict[str, Any], current_user: UserInfo = Depends(get_current_user)
) -> dict[str, Any]:
    """
    Apply accessibility tags to a PDF document
    Requires authentication
    """
    return {
        "message": "Document tagging initiated",
        "user_id": current_user.sub,
        "user_role": current_user.role,
        "document_id": document_data.get("doc_id"),
        "tagging_status": "in_progress",
        "estimated_completion": "2-5 minutes",
    }


@app.get("/tag/{doc_id}/status")
def get_tagging_status(
    doc_id: str, current_user: UserInfo = Depends(get_current_user)
) -> dict[str, Any]:
    """
    Get tagging status for a document
    Requires authentication
    """
    return {
        "doc_id": doc_id,
        "status": "completed",
        "tags_applied": 47,
        "accessibility_improvements": [
            "Added heading structure",
            "Applied reading order",
            "Tagged images with alt text",
        ],
        "user_id": current_user.sub,
    }


@app.get("/tag/{doc_id}/preview")
def preview_tags(
    doc_id: str, current_user: UserInfo = Depends(get_current_user)
) -> dict[str, Any]:
    """
    Preview tags that will be applied to a document
    Requires authentication
    """
    return {
        "doc_id": doc_id,
        "preview_tags": {
            "headings": ["H1: Main Title", "H2: Section 1", "H2: Section 2"],
            "images": ["Image 1: Chart showing data", "Image 2: Company logo"],
            "tables": ["Table 1: Financial summary"],
            "reading_order": "Sequential, left-to-right",
        },
        "preview_generated_by": current_user.sub,
    }


@app.delete("/tag/{doc_id}")
def remove_tags(
    doc_id: str, current_user: UserInfo = Depends(require_admin)
) -> dict[str, Any]:
    """
    Remove all accessibility tags from a document
    Requires admin role
    """
    return {
        "message": f"All tags removed from document {doc_id}",
        "removed_by": current_user.sub,
        "admin_action": True,
        "tags_removed": 47,
    }


@app.get("/templates")
def get_tagging_templates(
    current_user: UserInfo = Depends(optional_auth),
) -> dict[str, Any]:
    """
    Get available tagging templates
    Public endpoint with optional authentication for personalized results
    """
    base_templates = [
        {
            "id": "academic",
            "name": "Academic Paper",
            "description": "For research papers and academic documents",
        },
        {
            "id": "business",
            "name": "Business Report",
            "description": "For corporate reports and presentations",
        },
        {
            "id": "legal",
            "name": "Legal Document",
            "description": "For contracts and legal paperwork",
        },
    ]

    response = {"templates": base_templates, "public_access": True}

    if current_user:
        # Add personalized templates for authenticated users
        response["user_templates"] = [
            {
                "id": f"custom_{current_user.sub}",
                "name": "My Custom Template",
                "description": "User's saved template",
            }
        ]
        response["authenticated_user"] = current_user.sub

    return response
