import time
from typing import Dict, List, Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from .config import settings
from .models import UserRole


class BetterAuthJWTBearer(HTTPBearer):
    """Custom JWT Bearer authentication for BetterAuth"""

    def __init__(self, auto_error: bool = True):
        super().__init__(auto_error=auto_error)

    async def __call__(self, request: Request) -> HTTPAuthorizationCredentials:
        credentials = await super().__call__(request)
        if credentials:
            if not credentials.scheme == "Bearer":
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Invalid authentication scheme"
                )

            # Validate the token
            await self._validate_token(credentials.credentials)

        return credentials

    async def _validate_token(self, token: str) -> None:
        """Validate JWT token with BetterAuth secret"""
        try:
            # Verify token with shared secret
            payload = jwt.decode(
                token,
                settings.better_auth_secret,
                algorithms=[settings.jwt_algorithm],
                audience=settings.jwt_audience,
                issuer=settings.jwt_issuer,
                options={"verify_exp": True, "verify_aud": True, "verify_iss": True}
            )

            # Validate required claims exist
            if not payload.get('sub'):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token missing subject claim"
                )

        except JWTError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Token validation failed: {str(e)}"
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Authentication service error: {str(e)}"
            )


class User:
    """User model for authenticated requests"""

    def __init__(
        self,
        sub: str,
        name: Optional[str] = None,
        email: Optional[str] = None,
        role: Optional[str] = None,
        org_id: Optional[str] = None,
        token_claims: Optional[Dict] = None
    ):
        self.sub = sub
        self.name = name or ""
        self.email = email
        self.role = role or UserRole.VIEWER.value
        self.org_id = org_id
        self.token_claims = token_claims or {}

    def has_role(self, role: UserRole) -> bool:
        """Check if user has specific role"""
        return self.role == role.value

    def is_admin(self) -> bool:
        """Check if user is admin"""
        return self.has_role(UserRole.ADMIN)

    def can_access_resource(self, resource_user_id: str) -> bool:
        """Check if user can access resource owned by another user"""
        return self.is_admin() or self.sub == resource_user_id


# Global JWT bearer instance
jwt_bearer = BetterAuthJWTBearer()


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(jwt_bearer)) -> User:
    """Get current authenticated user"""
    try:
        # Decode token without verification (already validated in jwt_bearer)
        token = credentials.credentials
        payload = jwt.get_unverified_claims(token)

        # Extract user information
        sub = payload.get('sub')
        name = payload.get('name')
        email = payload.get('email')
        role = payload.get('role', UserRole.VIEWER.value)
        org_id = payload.get('orgId')

        return User(
            sub=sub,
            name=name,
            email=email,
            role=role,
            org_id=org_id,
            token_claims=payload
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Failed to extract user information: {str(e)}"
        )


async def get_admin_user(current_user: User = Depends(get_current_user)) -> User:
    """Get current user and verify admin role"""
    if not current_user.is_admin():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required"
        )
    return current_user


def require_roles(required_roles: List[UserRole]):
    """Decorator factory for role-based access control"""
    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if not any(current_user.has_role(role) for role in required_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Required roles: {[role.value for role in required_roles]}"
            )
        return current_user

    return role_checker