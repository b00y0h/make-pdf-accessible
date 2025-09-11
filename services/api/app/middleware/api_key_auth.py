"""
API Key Authentication Middleware

Provides API key based authentication for external API access.
Works alongside BetterAuth JWT for different authentication methods.
"""

import time
from collections import defaultdict
from typing import Any, Dict, Optional

from fastapi import HTTPException, Request, status
from starlette.middleware.base import BaseHTTPMiddleware

from services.shared.mongo.api_keys import APIKey, get_api_key_repository


class RateLimiter:
    """Simple in-memory rate limiter for API keys"""

    def __init__(self):
        self.requests: Dict[str, list] = defaultdict(list)
        self.last_cleanup = time.time()

    def is_allowed(self, key_id: str, rate_limit: int) -> bool:
        """
        Check if request is allowed based on rate limit

        Args:
            key_id: API key ID
            rate_limit: Requests per minute allowed

        Returns:
            True if allowed, False if rate limited
        """
        now = time.time()

        # Cleanup old requests every 60 seconds
        if now - self.last_cleanup > 60:
            self._cleanup_old_requests(now)
            self.last_cleanup = now

        # Get requests in the last minute
        requests = self.requests[key_id]
        cutoff = now - 60  # 60 seconds ago

        # Remove old requests
        self.requests[key_id] = [req_time for req_time in requests if req_time > cutoff]

        # Check if under limit
        if len(self.requests[key_id]) >= rate_limit:
            return False

        # Add this request
        self.requests[key_id].append(now)
        return True

    def _cleanup_old_requests(self, now: float):
        """Clean up old request data to prevent memory leaks"""
        cutoff = now - 300  # Keep 5 minutes of data
        for key_id in list(self.requests.keys()):
            self.requests[key_id] = [
                req_time for req_time in self.requests[key_id] if req_time > cutoff
            ]
            if not self.requests[key_id]:
                del self.requests[key_id]


# Global rate limiter instance
rate_limiter = RateLimiter()


class APIKeyAuthMiddleware(BaseHTTPMiddleware):
    """
    Middleware for API key authentication

    Checks for API keys in:
    1. Authorization header: "Bearer accesspdf_..."
    2. X-API-Key header: "accesspdf_..."
    3. Query parameter: "api_key=accesspdf_..."
    """

    def __init__(self, app, excluded_paths: Optional[list] = None):
        super().__init__(app)
        self.excluded_paths = excluded_paths or [
            "/docs",
            "/openapi.json",
            "/health",
            "/ping",
            "/auth",  # BetterAuth endpoints
        ]
        self.api_key_repo = get_api_key_repository()

    async def dispatch(self, request: Request, call_next):
        """Process request for API key authentication"""

        # Skip excluded paths
        if any(request.url.path.startswith(path) for path in self.excluded_paths):
            return await call_next(request)

        # Check if request already has user info (from BetterAuth JWT)
        if hasattr(request.state, "user"):
            # Already authenticated via JWT, skip API key check
            return await call_next(request)

        # Try to extract API key
        api_key = self._extract_api_key(request)
        if not api_key:
            # No API key provided - let other auth methods handle it
            return await call_next(request)

        try:
            # Validate API key
            key_obj = self.api_key_repo.validate_api_key(api_key)
            if not key_obj:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid or expired API key",
                )

            # Check rate limiting
            if key_obj.rate_limit and not rate_limiter.is_allowed(
                key_obj.id, key_obj.rate_limit
            ):
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Rate limit exceeded. Maximum {key_obj.rate_limit} requests per minute.",
                )

            # Add API key info to request state
            request.state.api_key = key_obj
            request.state.user_id = key_obj.user_id
            request.state.auth_method = "api_key"
            request.state.permissions = key_obj.permissions

            # Add some basic user info for compatibility
            request.state.user = {
                "id": key_obj.user_id,
                "auth_method": "api_key",
                "permissions": key_obj.permissions,
                "api_key_id": key_obj.id,
                "api_key_name": key_obj.name,
            }

        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"API key validation error: {str(e)}",
            )

        response = await call_next(request)
        return response

    def _extract_api_key(self, request: Request) -> Optional[str]:
        """
        Extract API key from request

        Priority order:
        1. Authorization header (Bearer token)
        2. X-API-Key header
        3. Query parameter
        """

        # 1. Check Authorization header
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer accesspdf_"):
            return auth_header[7:]  # Remove "Bearer "

        # 2. Check X-API-Key header
        api_key_header = request.headers.get("X-API-Key")
        if api_key_header and api_key_header.startswith("accesspdf_"):
            return api_key_header

        # 3. Check query parameter
        query_params = request.query_params
        api_key_param = query_params.get("api_key")
        if api_key_param and api_key_param.startswith("accesspdf_"):
            return api_key_param

        return None


def require_api_key_permission(permission: str):
    """
    Decorator to require specific API key permission

    Usage:
        @require_api_key_permission("documents.upload")
        async def upload_document():
            pass
    """

    def decorator(func):
        async def wrapper(request: Request, *args, **kwargs):
            # Check if authenticated via API key
            if not hasattr(request.state, "api_key"):
                # Not using API key auth - check if JWT user has permission
                if hasattr(request.state, "user") and hasattr(
                    request.state.user, "role"
                ):
                    # For JWT users, admin role has all permissions
                    if request.state.user.role == "admin":
                        return await func(request, *args, **kwargs)

                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Permission '{permission}' required",
                )

            # Check API key permissions
            api_key: APIKey = request.state.api_key
            if (
                permission not in api_key.permissions
                and "admin" not in api_key.permissions
            ):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"API key lacks permission: {permission}",
                )

            return await func(request, *args, **kwargs)

        return wrapper

    return decorator


def get_current_user_from_api_key(request: Request) -> Dict[str, Any]:
    """
    Extract user information from API key authentication

    Returns user dict compatible with BetterAuth user format
    """
    if hasattr(request.state, "api_key"):
        api_key: APIKey = request.state.api_key
        return {
            "id": api_key.user_id,
            "auth_method": "api_key",
            "permissions": api_key.permissions,
            "api_key_id": api_key.id,
            "api_key_name": api_key.name,
            "role": "admin" if "admin" in api_key.permissions else "user",
        }

    return None


# Common API key permissions
class APIKeyPermissions:
    """Standard API key permissions"""

    # Document operations
    DOCUMENTS_READ = "documents.read"
    DOCUMENTS_UPLOAD = "documents.upload"
    DOCUMENTS_DELETE = "documents.delete"
    DOCUMENTS_PROCESS = "documents.process"

    # Reports and analytics
    REPORTS_READ = "reports.read"
    REPORTS_DOWNLOAD = "reports.download"

    # Queue management
    QUEUE_READ = "queue.read"
    QUEUE_MANAGE = "queue.manage"

    # User management (admin only)
    USERS_READ = "users.read"
    USERS_MANAGE = "users.manage"

    # Full admin access
    ADMIN = "admin"

    @classmethod
    def get_all_permissions(cls) -> list:
        """Get all available permissions"""
        return [
            cls.DOCUMENTS_READ,
            cls.DOCUMENTS_UPLOAD,
            cls.DOCUMENTS_DELETE,
            cls.DOCUMENTS_PROCESS,
            cls.REPORTS_READ,
            cls.REPORTS_DOWNLOAD,
            cls.QUEUE_READ,
            cls.QUEUE_MANAGE,
            cls.USERS_READ,
            cls.USERS_MANAGE,
            cls.ADMIN,
        ]

    @classmethod
    def get_default_permissions(cls) -> list:
        """Get default permissions for new API keys"""
        return [
            cls.DOCUMENTS_READ,
            cls.DOCUMENTS_UPLOAD,
            cls.DOCUMENTS_PROCESS,
            cls.REPORTS_READ,
        ]
