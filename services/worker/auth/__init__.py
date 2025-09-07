"""
Authentication module for JWT verification and role-based access control
"""
from .jwt_auth import (
    CognitoJWTAuth,
    verify_jwt_token,
    extract_user_info,
    check_user_roles,
    require_auth,
    require_admin,
    require_viewer_or_admin,
)

__all__ = [
    'CognitoJWTAuth',
    'verify_jwt_token',
    'extract_user_info',
    'check_user_roles',
    'require_auth',
    'require_admin',
    'require_viewer_or_admin',
]