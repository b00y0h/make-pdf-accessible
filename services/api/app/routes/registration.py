"""
Client Registration System - Domain-based authentication for integrations
"""

import uuid
from typing import Dict, List, Any, Optional
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends, status, Query
from pydantic import BaseModel, Field

from ..auth import User as UserInfo, get_current_user

router = APIRouter(prefix="/v1/registration", tags=["client_registration"])


class ClientRegistration(BaseModel):
    """Client registration for domain-based authentication."""
    
    organization_name: str = Field(..., description="Organization name")
    domain: str = Field(..., description="Primary domain (e.g., agency.gov)")
    additional_domains: List[str] = Field(default=[], description="Additional domains")
    contact_email: str = Field(..., description="Primary contact email")
    organization_type: str = Field(..., description="Type: government, education, nonprofit, business")
    use_case: str = Field(..., description="Intended use case")
    integration_type: str = Field(..., description="wordpress, html, api, custom")


class IntegrationInfo(BaseModel):
    """Integration information for client."""
    
    integration_id: str = Field(..., description="Public integration ID (safe to expose)")
    api_key: str = Field(..., description="Private API key (server-side only)")
    allowed_domains: List[str] = Field(..., description="Domains authorized for this integration")
    webhook_secret: str = Field(..., description="Secret for webhook verification")


@router.post("/register", response_model=IntegrationInfo)
async def register_client_integration(
    registration: ClientRegistration,
    current_user: UserInfo = Depends(get_current_user)
):
    """
    Register a new client integration with domain-based authentication.
    
    Creates both a public integration ID (safe for frontend) and 
    private API key (for server-side operations).
    """
    try:
        # Generate credentials
        integration_id = f"{registration.organization_type}_{uuid.uuid4().hex[:12]}"
        api_key = f"ak_{uuid.uuid4().hex}"
        webhook_secret = f"ws_{uuid.uuid4().hex[:16]}"
        
        # Validate domains
        all_domains = [registration.domain] + registration.additional_domains
        for domain in all_domains:
            if not domain or '.' not in domain:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid domain: {domain}"
                )
        
        # Store registration in database
        from services.shared.mongo.connection import get_database
        db = get_database()
        registrations_collection = db["client_registrations"]
        
        registration_data = {
            "integrationId": integration_id,
            "apiKey": api_key,
            "webhookSecret": webhook_secret,
            "organizationName": registration.organization_name,
            "domains": all_domains,
            "contactEmail": registration.contact_email,
            "organizationType": registration.organization_type,
            "useCase": registration.use_case,
            "integrationType": registration.integration_type,
            "registeredBy": current_user.sub,
            "registeredAt": datetime.utcnow(),
            "status": "active",
            "usage": {
                "documentsProcessed": 0,
                "lastActivity": None,
                "monthlyQuota": 1000,  # Default quota
            }
        }
        
        result = registrations_collection.insert_one(registration_data)
        
        return IntegrationInfo(
            integration_id=integration_id,
            api_key=api_key,
            allowed_domains=all_domains,
            webhook_secret=webhook_secret
        )
        
    except HTTPException:
        raise
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Client registration failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed"
        )


@router.get("/integrations")
async def list_client_integrations(
    current_user: UserInfo = Depends(get_current_user)
):
    """
    List all client integrations for the current user.
    """
    try:
        from services.shared.mongo.connection import get_database
        db = get_database()
        registrations_collection = db["client_registrations"]
        
        # Get registrations for current user (or all if admin)
        filter_query = {"registeredBy": current_user.sub}
        if current_user.role == "admin":
            filter_query = {}  # Admin sees all registrations
        
        registrations = list(registrations_collection.find(
            filter_query,
            {
                "apiKey": 0,        # Don't return API key in list
                "webhookSecret": 0  # Don't return webhook secret in list
            }
        ).sort("registeredAt", -1))
        
        return {
            "total": len(registrations),
            "integrations": registrations
        }
        
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to list integrations: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve integrations"
        )


@router.get("/integrations/{integration_id}")
async def get_integration_details(
    integration_id: str,
    current_user: UserInfo = Depends(get_current_user)
):
    """
    Get detailed information about a specific integration.
    """
    try:
        from services.shared.mongo.connection import get_database
        db = get_database()
        registrations_collection = db["client_registrations"]
        
        registration = registrations_collection.find_one({"integrationId": integration_id})
        
        if not registration:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Integration not found"
            )
        
        # Check access (owner or admin)
        if registration.get("registeredBy") != current_user.sub and current_user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        # Return full details including sensitive data for owner
        return {
            "integration_id": integration_id,
            "organization_name": registration.get("organizationName"),
            "domains": registration.get("domains", []),
            "contact_email": registration.get("contactEmail"),
            "organization_type": registration.get("organizationType"),
            "integration_type": registration.get("integrationType"),
            "status": registration.get("status"),
            "api_key": registration.get("apiKey"),  # Only for owner/admin
            "webhook_secret": registration.get("webhookSecret"),  # Only for owner/admin
            "usage": registration.get("usage", {}),
            "registered_at": registration.get("registeredAt"),
            "setup_instructions": {
                "wordpress": {
                    "plugin_download": "https://cdn.accesspdf.com/plugins/wordpress-accesspdf.zip",
                    "api_key": registration.get("apiKey"),
                    "setup_guide": "https://docs.accesspdf.com/wordpress-setup"
                },
                "html": {
                    "script_tag": f'<script>window.accesspdf_config = {{integrationId: "{integration_id}", domain: "{registration.get("domains", [""])[0]}"}};</script>',
                    "cdn_script": '<script src="https://cdn.accesspdf.com/integration.js"></script>',
                    "setup_guide": "https://docs.accesspdf.com/html-integration"
                }
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to get integration details: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve integration details"
        )


async def verify_domain_integration(
    domain: str, 
    integration_id: str
) -> Optional[Dict[str, Any]]:
    """
    Verify that a domain is authorized for the given integration ID.
    Used for domain-based authentication.
    """
    try:
        from services.shared.mongo.connection import get_database
        db = get_database()
        registrations_collection = db["client_registrations"]
        
        registration = registrations_collection.find_one({
            "integrationId": integration_id,
            "domains": domain,
            "status": "active"
        })
        
        return registration
        
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Domain verification failed: {e}")
        return None


@router.get("/verify/{integration_id}")
async def verify_integration(
    integration_id: str,
    domain: str = Query(..., description="Domain to verify")
):
    """
    Public endpoint to verify integration ID and domain combination.
    Used by frontend scripts to validate configuration.
    """
    registration = await verify_domain_integration(domain, integration_id)
    
    if registration:
        return {
            "valid": True,
            "integration_id": integration_id,
            "domain": domain,
            "organization": registration.get("organizationName"),
            "features_enabled": {
                "auto_enhancement": True,
                "llm_discovery": True,
                "accessibility_badges": True,
                "analytics_tracking": registration.get("usage", {}).get("analyticsEnabled", True)
            }
        }
    else:
        return {
            "valid": False,
            "integration_id": integration_id,
            "domain": domain,
            "error": "Integration ID not found or domain not authorized"
        }