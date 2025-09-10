"""
Authentication module for BetterAuth JWT verification and role-based access control
"""
from .better_auth import (
    BetterAuthJWT,
    better_auth,
    require_admin,
    require_auth,
    require_viewer_or_admin,
)

# Keep backward compatibility by aliasing the old functions
verify_jwt_token = better_auth.verify_jwt_token
extract_user_info = better_auth.extract_user_info
check_user_roles = better_auth.check_user_roles

__all__ = [
    'BetterAuthJWT',
    'better_auth',
    'verify_jwt_token',
    'extract_user_info',
    'check_user_roles', 
    'require_auth',
    'require_admin',
    'require_viewer_or_admin',
]
