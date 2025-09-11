from typing import Dict, List, Optional

import requests
from fastapi import Depends, HTTPException, Request, status

from .config import settings
from .models import UserRole


class BetterAuthSessionValidator:
    """Custom session validator for BetterAuth"""

    def __init__(self, better_auth_url: str):
        self.better_auth_url = better_auth_url.rstrip("/")

    def validate_session(self, request: Request) -> Optional[Dict]:
        """Validate session with BetterAuth service by forwarding all cookies"""
        try:
            # Forward all cookies from the original request to BetterAuth
            cookies = dict(request.cookies)

            if not cookies:
                print("DEBUG: No cookies received from request")
                return None

            print(
                f"DEBUG: Forwarding {len(cookies)} cookies to BetterAuth: {list(cookies.keys())}"
            )
            print(f"DEBUG: BetterAuth URL: {self.better_auth_url}")

            auth_url = f"{self.better_auth_url}/api/auth/get-session"
            print(f"DEBUG: Making request to: {auth_url}")

            # Call BetterAuth session endpoint with all cookies
            response = requests.get(auth_url, cookies=cookies, timeout=5.0)

            print(f"DEBUG: BetterAuth response status: {response.status_code}")
            if response.status_code != 200:
                print(f"DEBUG: BetterAuth response body: {response.text}")
                return None

            # Better Auth returns null for no session, or {session: {...}, user: {...}} for valid session
            response_text = response.text.strip()
            print(f"DEBUG: BetterAuth raw response: {response_text}")
            
            if response_text == "null" or response_text == "":
                print("DEBUG: No session (null response)")
                return None
                
            try:
                session_data = response.json()
            except:
                print(f"DEBUG: Failed to parse response as JSON: {response_text}")
                return None
                
            print(f"DEBUG: BetterAuth session data: {session_data}")
            
            # Check if we have both session and user data
            if not session_data or not isinstance(session_data, dict):
                print("DEBUG: Invalid session data format")
                return None
                
            if not session_data.get("user"):
                print("DEBUG: No user in session data")
                return None

            return session_data

        except Exception as e:
            print(f"DEBUG: Session validation exception: {type(e).__name__}: {e}")
            return None


class User:
    """User model for authenticated requests"""

    def __init__(
        self,
        sub: str,
        name: Optional[str] = None,
        email: Optional[str] = None,
        role: Optional[str] = None,
        org_id: Optional[str] = None,
        token_claims: Optional[Dict] = None,
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


# Global session validator instance
session_validator = BetterAuthSessionValidator(settings.better_auth_dashboard_url)


async def get_current_user(request: Request) -> User:
    """Get current authenticated user"""
    session_data = session_validator.validate_session(request)

    if not session_data or not session_data.get("user"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not authenticated"
        )

    user_data = session_data["user"]

    return User(
        sub=user_data.get("id"),
        name=user_data.get("name"),
        email=user_data.get("email"),
        role=user_data.get("role", UserRole.VIEWER.value),
        org_id=user_data.get("orgId"),
        token_claims=user_data,
    )


async def get_admin_user(request: Request) -> User:
    """Get current user and verify admin role"""
    current_user = await get_current_user(request)
    if not current_user.is_admin():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Admin role required"
        )
    return current_user


def require_roles(required_roles: List[UserRole]):
    """Decorator factory for role-based access control"""

    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if not any(current_user.has_role(role) for role in required_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Required roles: {[role.value for role in required_roles]}",
            )
        return current_user

    return role_checker
