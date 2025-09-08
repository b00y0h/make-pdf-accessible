"""
Authentication module for JWT verification and role-based access control
"""
from .jwt_auth import (
    CognitoJWTAuth,
    check_user_roles,
    extract_user_info,
    require_admin,
    require_auth,
    require_viewer_or_admin,
    verify_jwt_token,
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
