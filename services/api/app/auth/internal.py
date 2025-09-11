"""
Internal dashboard authentication for same-system communication
"""

from typing import Optional
from fastapi import Header, HTTPException, status
from ..auth import User


async def get_dashboard_user(
    x_dashboard_internal: Optional[str] = Header(None),
    x_dashboard_secret: Optional[str] = Header(None),
) -> User:
    """
    Authentication for internal dashboard calls.
    
    Since dashboard and API are on different ports but same system,
    we use internal headers instead of cross-domain cookies.
    """
    
    # Check for dashboard internal headers
    if (x_dashboard_internal == "true" and 
        x_dashboard_secret == "dashboard_internal_secret_123"):
        
        # Return a dashboard system user
        return User(
            sub="dashboard_system_user",
            email="dashboard@system.local",
            name="Dashboard System",
            role="admin",  # Dashboard has admin access
            org_id="system",
        )
    
    # Not a dashboard internal call
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Dashboard authentication required"
    )


# Optional: Create a combined auth dependency that tries both methods
from ..auth import get_current_user

async def get_user_flexible(
    request,
    x_dashboard_internal: Optional[str] = Header(None),
    x_dashboard_secret: Optional[str] = Header(None),
):
    """
    Try dashboard internal auth first, fallback to normal user auth.
    """
    
    # Try dashboard internal auth first
    if (x_dashboard_internal == "true" and 
        x_dashboard_secret == "dashboard_internal_secret_123"):
        return User(
            sub="dashboard_system_user",
            email="dashboard@system.local", 
            name="Dashboard System",
            role="admin",
            org_id="system",
        )
    
    # Fallback to normal user authentication
    try:
        return await get_current_user(request)
    except HTTPException:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Authentication required (user or dashboard)"
        )