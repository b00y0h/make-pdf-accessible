import time
from typing import Dict, List, Optional

import httpx
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from .config import settings
from .models import UserRole


class CognitoJWKSError(Exception):
    """Exception for JWKS-related errors"""
    pass


class JWKSClient:
    """Client for fetching and caching Cognito JWKS"""

    def __init__(self):
        self._jwks: Optional[Dict] = None
        self._last_fetch: float = 0
        self._cache_ttl: int = 3600  # 1 hour cache

    async def get_jwks(self) -> Dict:
        """Get JWKS, fetching from Cognito if needed"""
        current_time = time.time()

        if self._jwks is None or (current_time - self._last_fetch) > self._cache_ttl:
            await self._fetch_jwks()

        return self._jwks

    async def _fetch_jwks(self) -> None:
        """Fetch JWKS from Cognito"""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(settings.cognito_jwks_url)
                response.raise_for_status()
                self._jwks = response.json()
                self._last_fetch = time.time()
        except httpx.RequestError as e:
            raise CognitoJWKSError(f"Failed to fetch JWKS: {str(e)}")
        except httpx.HTTPStatusError as e:
            raise CognitoJWKSError(f"JWKS endpoint returned {e.response.status_code}")


class CognitoJWTBearer(HTTPBearer):
    """Custom JWT Bearer authentication for Cognito"""

    def __init__(self, auto_error: bool = True):
        super().__init__(auto_error=auto_error)
        self.jwks_client = JWKSClient()

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
        """Validate JWT token with Cognito JWKS"""
        try:
            # Get JWKS
            jwks = await self.jwks_client.get_jwks()

            # Decode header to get kid
            unverified_header = jwt.get_unverified_header(token)
            kid = unverified_header.get('kid')

            if not kid:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token missing kid claim"
                )

            # Find matching key
            key = None
            for jwk_key in jwks.get('keys', []):
                if jwk_key.get('kid') == kid:
                    key = jwk_key
                    break

            if not key:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Unable to find appropriate key"
                )

            # Verify token
            payload = jwt.decode(
                token,
                key,
                algorithms=[settings.jwt_algorithm],
                audience=settings.cognito_client_id,
                issuer=settings.cognito_issuer,
                options={"verify_exp": True, "verify_aud": True}
            )

            # Validate token type
            if payload.get('token_use') != 'access':
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token type"
                )

        except JWTError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Token validation failed: {str(e)}"
            )
        except CognitoJWKSError as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Authentication service error: {str(e)}"
            )


class User:
    """User model for authenticated requests"""

    def __init__(
        self,
        sub: str,
        username: str,
        email: Optional[str] = None,
        roles: Optional[List[str]] = None,
        token_claims: Optional[Dict] = None
    ):
        self.sub = sub
        self.username = username
        self.email = email
        self.roles = roles or []
        self.token_claims = token_claims or {}

    def has_role(self, role: UserRole) -> bool:
        """Check if user has specific role"""
        return role.value in self.roles

    def is_admin(self) -> bool:
        """Check if user is admin"""
        return self.has_role(UserRole.ADMIN)

    def can_access_resource(self, resource_user_id: str) -> bool:
        """Check if user can access resource owned by another user"""
        return self.is_admin() or self.sub == resource_user_id


# Global JWT bearer instance
jwt_bearer = CognitoJWTBearer()


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(jwt_bearer)) -> User:
    """Get current authenticated user"""
    try:
        # Decode token without verification (already validated in jwt_bearer)
        token = credentials.credentials
        payload = jwt.get_unverified_claims(token)

        # Extract user information
        sub = payload.get('sub')
        username = payload.get('username', payload.get('cognito:username', ''))
        email = payload.get('email')

        # Extract roles from custom claims or groups
        roles = []
        if 'custom:roles' in payload:
            roles = payload['custom:roles'].split(',')
        elif 'cognito:groups' in payload:
            roles = payload['cognito:groups']

        # Default role assignment
        if not roles:
            roles = [UserRole.VIEWER.value]

        return User(
            sub=sub,
            username=username,
            email=email,
            roles=roles,
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
        user_roles = [UserRole(role) for role in current_user.roles if role in [r.value for r in UserRole]]

        if not any(role in user_roles for role in required_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Required roles: {[role.value for role in required_roles]}"
            )
        return current_user

    return role_checker
