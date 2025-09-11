"""
Unified JWT Authentication module for FastAPI microservices

This module provides BetterAuth JWT validation that can be shared across
all FastAPI microservices in the PDF accessibility platform.
"""

import os
from typing import Any, Dict, List, Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from jose.exceptions import ExpiredSignatureError, JWTClaimsError
from pydantic import BaseModel


class AuthenticationError(Exception):
    """Authentication related errors"""

    pass


class AuthorizationError(Exception):
    """Authorization related errors"""

    pass


class UserInfo(BaseModel):
    """User information extracted from JWT token"""

    sub: str  # User ID
    email: Optional[str] = None
    name: Optional[str] = None
    role: str = "viewer"
    org_id: Optional[str] = None
    iss: Optional[str] = None
    aud: Optional[str] = None
    exp: Optional[int] = None
    iat: Optional[int] = None
    token_type: str = "better_auth"

    def has_role(self, role: str) -> bool:
        """Check if user has specific role"""
        return self.role == role

    def is_admin(self) -> bool:
        """Check if user is admin"""
        return self.has_role("admin")

    def can_access_resource(self, resource_user_id: str) -> bool:
        """Check if user can access resource owned by another user"""
        return self.is_admin() or self.sub == resource_user_id


class BetterAuthJWT:
    """
    BetterAuth JWT Authentication for FastAPI microservices
    """

    def __init__(self):
        self.secret_key = self._get_jwt_secret()
        self.algorithm = os.getenv("JWT_ALGORITHM", "HS256")
        self.issuer = os.getenv("JWT_ISSUER", "accesspdf-dashboard")
        self.audience = os.getenv("JWT_AUDIENCE", "accesspdf-api")

    def _get_jwt_secret(self) -> str:
        """Get JWT secret from environment"""
        secret = os.getenv("API_JWT_SECRET")
        if not secret:
            raise AuthenticationError("JWT secret not configured (API_JWT_SECRET)")
        return secret

    def verify_jwt_token(self, token: str) -> Dict[str, Any]:
        """
        Verify BetterAuth JWT token and return claims

        Args:
            token: JWT token string

        Returns:
            Dict containing token claims

        Raises:
            AuthenticationError: If token is invalid
        """
        try:
            # Verify token with shared secret
            claims = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm],
                audience=self.audience,
                issuer=self.issuer,
                options={
                    "verify_exp": True,
                    "verify_aud": True,
                    "verify_iss": True,
                    "verify_signature": True,
                },
            )

            # Validate required claims exist
            if not claims.get("sub"):
                raise AuthenticationError("Token missing subject claim")

            return claims

        except ExpiredSignatureError:
            raise AuthenticationError("Token has expired")
        except JWTClaimsError as e:
            raise AuthenticationError(f"Token claims validation failed: {str(e)}")
        except JWTError as e:
            raise AuthenticationError(f"Token validation failed: {str(e)}")
        except Exception as e:
            raise AuthenticationError(f"Token verification error: {str(e)}")

    def extract_user_info(self, claims: Dict[str, Any]) -> UserInfo:
        """
        Extract user information from BetterAuth JWT claims

        Args:
            claims: JWT claims dictionary

        Returns:
            UserInfo object containing user information
        """
        return UserInfo(
            sub=claims.get("sub"),
            email=claims.get("email"),
            name=claims.get("name"),
            role=claims.get("role", "viewer"),
            org_id=claims.get("org_id"),
            iss=claims.get("iss"),
            aud=claims.get("aud"),
            exp=claims.get("exp"),
            iat=claims.get("iat"),
            token_type="better_auth",
        )

    def check_user_roles(self, user_role: str, required_roles: List[str]) -> bool:
        """
        Check if user has any of the required roles

        Args:
            user_role: User's role from BetterAuth
            required_roles: List of required roles

        Returns:
            True if user has at least one required role
        """
        if not required_roles:
            return True

        return user_role in required_roles


# Global authentication instance
auth_jwt = BetterAuthJWT()

# FastAPI security scheme
security = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> UserInfo:
    """
    FastAPI dependency to get current authenticated user

    Args:
        credentials: HTTP authorization credentials from request header

    Returns:
        UserInfo object for the authenticated user

    Raises:
        HTTPException: If authentication fails
    """
    try:
        # Verify the JWT token
        claims = auth_jwt.verify_jwt_token(credentials.credentials)

        # Extract user info
        user_info = auth_jwt.extract_user_info(claims)

        return user_info

    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


def get_admin_user(current_user: UserInfo = Depends(get_current_user)) -> UserInfo:
    """
    FastAPI dependency to get current user and verify admin role

    Args:
        current_user: Current authenticated user

    Returns:
        UserInfo object for the authenticated admin user

    Raises:
        HTTPException: If user is not admin
    """
    if not current_user.is_admin():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Admin role required"
        )
    return current_user


def require_roles(required_roles: List[str]):
    """
    FastAPI dependency factory for role-based access control

    Args:
        required_roles: List of roles that are allowed

    Returns:
        FastAPI dependency function that validates user roles
    """

    def role_checker(current_user: UserInfo = Depends(get_current_user)) -> UserInfo:
        if not auth_jwt.check_user_roles(current_user.role, required_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Required roles: {required_roles}, user role: {current_user.role}",
            )
        return current_user

    return role_checker


# Convenience dependencies for common role checks
require_admin = require_roles(["admin"])
require_viewer_or_admin = require_roles(["viewer", "admin"])
require_user_or_admin = require_roles(["user", "admin"])


def optional_auth(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(
        HTTPBearer(auto_error=False)
    ),
) -> Optional[UserInfo]:
    """
    FastAPI dependency for optional authentication

    Args:
        credentials: Optional HTTP authorization credentials

    Returns:
        UserInfo object if authenticated, None otherwise
    """
    if not credentials:
        return None

    try:
        claims = auth_jwt.verify_jwt_token(credentials.credentials)
        return auth_jwt.extract_user_info(claims)
    except:
        return None


def create_auth_middleware():
    """
    Create authentication middleware for FastAPI applications

    This middleware can be added to FastAPI apps to provide automatic
    authentication checking for all routes (except those marked as public)
    """

    async def auth_middleware(request: Request, call_next):
        # Skip authentication for health check and root endpoints
        if request.url.path in ["/", "/health", "/docs", "/openapi.json"]:
            response = await call_next(request)
            return response

        # Add authentication header check here if needed
        # For now, we'll rely on the dependencies to handle auth
        response = await call_next(request)
        return response

    return auth_middleware


# Export commonly used items
__all__ = [
    "UserInfo",
    "AuthenticationError",
    "AuthorizationError",
    "BetterAuthJWT",
    "auth_jwt",
    "get_current_user",
    "get_admin_user",
    "require_roles",
    "require_admin",
    "require_viewer_or_admin",
    "require_user_or_admin",
    "optional_auth",
    "create_auth_middleware",
]
