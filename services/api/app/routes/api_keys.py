"""
API Key Management Routes

Endpoints for creating, managing, and monitoring API keys.
"""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from services.shared.mongo.api_keys import (
    APIKey,
    RepositoryError,
    get_api_key_repository,
)

from ..auth import User, get_current_user
from ..middleware import APIKeyPermissions

router = APIRouter(prefix="/api-keys", tags=["API Keys"])


# Request/Response Models
class CreateAPIKeyRequest(BaseModel):
    name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Human-readable name for the API key",
    )
    permissions: list[str] = Field(
        default_factory=list, description="List of permissions to grant"
    )
    expires_in_days: Optional[int] = Field(
        None, ge=1, le=365, description="Expiration in days (optional)"
    )
    rate_limit: Optional[int] = Field(
        None, ge=1, le=10000, description="Requests per minute limit (optional)"
    )


class APIKeyResponse(BaseModel):
    id: str
    name: str
    key_prefix: str
    permissions: list[str]
    expires_at: Optional[datetime]
    last_used_at: Optional[datetime]
    created_at: datetime
    is_active: bool
    rate_limit: Optional[int]
    usage_count: int


class CreateAPIKeyResponse(BaseModel):
    api_key: APIKeyResponse
    key: str = Field(
        ...,
        description="The actual API key - store this securely, it won't be shown again",
    )


class UpdateAPIKeyRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    permissions: Optional[list[str]] = None
    rate_limit: Optional[int] = Field(None, ge=1, le=10000)
    is_active: Optional[bool] = None


class UsageStatsResponse(BaseModel):
    total_keys: int
    active_keys: int
    total_usage: int
    last_used: Optional[datetime]


# Helper functions
def validate_permissions(permissions: list[str]) -> list[str]:
    """Validate and filter permissions"""
    valid_permissions = APIKeyPermissions.get_all_permissions()
    invalid_perms = [p for p in permissions if p not in valid_permissions]

    if invalid_perms:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid permissions: {invalid_perms}. Valid permissions: {valid_permissions}",
        )

    return permissions


def api_key_to_response(api_key: APIKey) -> APIKeyResponse:
    """Convert APIKey to response model"""
    return APIKeyResponse(
        id=api_key.id,
        name=api_key.name,
        key_prefix=api_key.key_prefix,
        permissions=api_key.permissions,
        expires_at=api_key.expires_at,
        last_used_at=api_key.last_used_at,
        created_at=api_key.created_at,
        is_active=api_key.is_active,
        rate_limit=api_key.rate_limit,
        usage_count=api_key.usage_count,
    )


# Routes
@router.post(
    "/", response_model=CreateAPIKeyResponse, status_code=status.HTTP_201_CREATED
)
async def create_api_key(
    request: CreateAPIKeyRequest, current_user: User = Depends(get_current_user)
):
    """
    Create a new API key for the authenticated user

    - **name**: Human-readable name for identification
    - **permissions**: List of permissions to grant (defaults to basic permissions)
    - **expires_in_days**: Optional expiration (1-365 days)
    - **rate_limit**: Optional rate limit (requests per minute)
    """
    try:
        # Validate permissions
        permissions = request.permissions or APIKeyPermissions.get_default_permissions()
        permissions = validate_permissions(permissions)

        # Admin check for sensitive permissions
        sensitive_perms = [APIKeyPermissions.USERS_MANAGE, APIKeyPermissions.ADMIN]
        if any(p in permissions for p in sensitive_perms):
            if not current_user.is_admin():
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Admin role required for sensitive permissions",
                )

        # Create API key
        repo = get_api_key_repository()
        api_key, raw_key = repo.generate_api_key(
            user_id=current_user.sub,
            name=request.name,
            permissions=permissions,
            expires_in_days=request.expires_in_days,
            rate_limit=request.rate_limit,
        )

        return CreateAPIKeyResponse(api_key=api_key_to_response(api_key), key=raw_key)

    except RepositoryError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create API key: {str(e)}",
        )


@router.get("/", response_model=list[APIKeyResponse])
async def list_api_keys(current_user: dict = Depends(get_current_user)):
    """List all API keys for the authenticated user"""
    try:
        repo = get_api_key_repository()
        api_keys = repo.get_user_api_keys(current_user["id"])
        return [api_key_to_response(key) for key in api_keys]
    except RepositoryError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list API keys: {str(e)}",
        )


@router.get("/permissions", response_model=dict[str, list[str]])
async def get_available_permissions():
    """Get all available API key permissions"""
    return {
        "all_permissions": APIKeyPermissions.get_all_permissions(),
        "default_permissions": APIKeyPermissions.get_default_permissions(),
    }


@router.get("/usage-stats", response_model=UsageStatsResponse)
async def get_usage_stats(current_user: dict = Depends(get_current_user)):
    """Get API key usage statistics for the authenticated user"""
    try:
        repo = get_api_key_repository()
        stats = repo.get_usage_stats(current_user["id"])
        return UsageStatsResponse(**stats)
    except RepositoryError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get usage stats: {str(e)}",
        )


@router.get("/{key_id}", response_model=APIKeyResponse)
async def get_api_key(key_id: str, current_user: dict = Depends(get_current_user)):
    """Get details of a specific API key"""
    try:
        repo = get_api_key_repository()
        api_key = repo.get_api_key(key_id)

        if not api_key:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="API key not found"
            )

        # Check ownership
        if (
            api_key.user_id != current_user["id"]
            and current_user.get("role") != "admin"
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to access this API key",
            )

        return api_key_to_response(api_key)

    except RepositoryError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get API key: {str(e)}",
        )


@router.put("/{key_id}", response_model=APIKeyResponse)
async def update_api_key(
    key_id: str,
    request: UpdateAPIKeyRequest,
    current_user: dict = Depends(get_current_user),
):
    """Update an existing API key"""
    try:
        repo = get_api_key_repository()
        api_key = repo.get_api_key(key_id)

        if not api_key:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="API key not found"
            )

        # Check ownership
        if (
            api_key.user_id != current_user["id"]
            and current_user.get("role") != "admin"
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to modify this API key",
            )

        # Build updates
        updates = {}
        if request.name is not None:
            updates["name"] = request.name
        if request.permissions is not None:
            permissions = validate_permissions(request.permissions)
            # Check admin permissions
            sensitive_perms = [APIKeyPermissions.USERS_MANAGE, APIKeyPermissions.ADMIN]
            if any(p in permissions for p in sensitive_perms):
                if current_user.get("role") != "admin":
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Admin role required for sensitive permissions",
                    )
            updates["permissions"] = permissions
        if request.rate_limit is not None:
            updates["rate_limit"] = request.rate_limit
        if request.is_active is not None:
            updates["is_active"] = request.is_active

        # Update the key
        success = repo.update_api_key(key_id, updates)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update API key",
            )

        # Return updated key
        updated_key = repo.get_api_key(key_id)
        return api_key_to_response(updated_key)

    except RepositoryError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update API key: {str(e)}",
        )


@router.delete("/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_api_key(key_id: str, current_user: dict = Depends(get_current_user)):
    """Delete an API key"""
    try:
        repo = get_api_key_repository()
        api_key = repo.get_api_key(key_id)

        if not api_key:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="API key not found"
            )

        # Check ownership
        if (
            api_key.user_id != current_user["id"]
            and current_user.get("role") != "admin"
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to delete this API key",
            )

        success = repo.delete_api_key(key_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete API key",
            )

    except RepositoryError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete API key: {str(e)}",
        )


@router.post("/{key_id}/deactivate", response_model=APIKeyResponse)
async def deactivate_api_key(
    key_id: str, current_user: dict = Depends(get_current_user)
):
    """Deactivate an API key (safer than deletion)"""
    try:
        repo = get_api_key_repository()
        api_key = repo.get_api_key(key_id)

        if not api_key:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="API key not found"
            )

        # Check ownership
        if (
            api_key.user_id != current_user["id"]
            and current_user.get("role") != "admin"
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to modify this API key",
            )

        success = repo.deactivate_api_key(key_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to deactivate API key",
            )

        # Return updated key
        updated_key = repo.get_api_key(key_id)
        return api_key_to_response(updated_key)

    except RepositoryError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to deactivate API key: {str(e)}",
        )


# Admin-only endpoints
@router.get("/admin/all", response_model=list[APIKeyResponse])
async def list_all_api_keys(current_user: dict = Depends(get_current_user)):
    """Admin endpoint: List all API keys in the system"""
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Admin role required"
        )

    try:
        repo = get_api_key_repository()
        # Get all keys by aggregating across all users
        # This is inefficient but works for the current scale
        docs = repo.collection.find({}).sort([("created_at", -1)])
        api_keys = [APIKey.from_dict(doc) for doc in docs]
        return [api_key_to_response(key) for key in api_keys]
    except RepositoryError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list all API keys: {str(e)}",
        )


@router.post("/admin/cleanup", response_model=dict[str, int])
async def cleanup_expired_keys(current_user: dict = Depends(get_current_user)):
    """Admin endpoint: Clean up expired API keys"""
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Admin role required"
        )

    try:
        repo = get_api_key_repository()
        deleted_count = repo.cleanup_expired_keys()
        return {"deleted_count": deleted_count}
    except RepositoryError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to cleanup expired keys: {str(e)}",
        )
