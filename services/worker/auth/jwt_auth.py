"""
JWT Authentication module for validating Cognito tokens
"""
import time
from functools import wraps
from typing import Any

import requests
from jose import JWTError, jwt
from jose.exceptions import ExpiredSignatureError, JWTClaimsError

from ..core.config import get_settings
from ..core.exceptions import AuthenticationError, AuthorizationError

# Cache for JWKS
_jwks_cache: dict[str, Any] = {}
_jwks_cache_expires = 0
JWKS_CACHE_TTL = 3600  # 1 hour


def get_jwks_keys() -> list[dict[str, Any]]:
    """
    Get JWKS keys from Cognito with caching
    """
    global _jwks_cache, _jwks_cache_expires

    current_time = time.time()

    # Check if cache is still valid
    if _jwks_cache and current_time < _jwks_cache_expires:
        return _jwks_cache.get('keys', [])

    settings = get_settings()
    jwks_url = f"https://cognito-idp.{settings.aws_region}.amazonaws.com/{settings.cognito_user_pool_id}/.well-known/jwks.json"

    try:
        response = requests.get(jwks_url, timeout=10)
        response.raise_for_status()

        jwks_data = response.json()
        _jwks_cache = jwks_data
        _jwks_cache_expires = current_time + JWKS_CACHE_TTL

        return jwks_data.get('keys', [])
    except Exception as e:
        raise AuthenticationError(f"Failed to fetch JWKS: {str(e)}")


def verify_jwt_token(token: str) -> dict[str, Any]:
    """
    Verify JWT token and return claims
    
    Args:
        token: JWT token string
        
    Returns:
        Dict containing token claims
        
    Raises:
        AuthenticationError: If token is invalid
    """
    settings = get_settings()

    try:
        # Get JWKS keys
        keys = get_jwks_keys()
        if not keys:
            raise AuthenticationError("No JWKS keys available")

        # Get token header
        unverified_header = jwt.get_unverified_header(token)

        # Find the key that matches the token's key ID
        key = None
        for jwk_key in keys:
            if jwk_key.get('kid') == unverified_header.get('kid'):
                key = jwk_key
                break

        if not key:
            raise AuthenticationError("Token key ID not found in JWKS")

        # Verify and decode token
        claims = jwt.decode(
            token,
            key,
            algorithms=['RS256'],
            audience=settings.cognito_client_id,
            issuer=f"https://cognito-idp.{settings.aws_region}.amazonaws.com/{settings.cognito_user_pool_id}",
            options={
                "verify_signature": True,
                "verify_aud": True,
                "verify_iat": True,
                "verify_exp": True,
                "verify_nbf": True,
                "verify_iss": True,
                "verify_sub": True,
                "verify_jti": True,
                "verify_at_hash": True,
                "require_aud": True,
                "require_iat": True,
                "require_exp": True,
                "require_nbf": False,
                "require_iss": True,
                "require_sub": True,
                "require_jti": True,
                "require_at_hash": False,
            }
        )

        # Additional validations
        token_use = claims.get('token_use')
        if token_use not in ['access', 'id']:
            raise AuthenticationError(f"Invalid token use: {token_use}")

        return claims

    except ExpiredSignatureError:
        raise AuthenticationError("Token has expired")
    except JWTClaimsError as e:
        raise AuthenticationError(f"Token claims validation failed: {str(e)}")
    except JWTError as e:
        raise AuthenticationError(f"Token validation failed: {str(e)}")
    except Exception as e:
        raise AuthenticationError(f"Token verification error: {str(e)}")


def extract_user_info(claims: dict[str, Any]) -> dict[str, Any]:
    """
    Extract user information from JWT claims
    
    Args:
        claims: JWT claims dictionary
        
    Returns:
        Dict containing user information
    """
    user_info = {
        'sub': claims.get('sub'),
        'email': claims.get('email'),
        'email_verified': claims.get('email_verified', False),
        'username': claims.get('cognito:username'),
        'groups': claims.get('cognito:groups', []),
        'given_name': claims.get('given_name'),
        'family_name': claims.get('family_name'),
        'picture': claims.get('picture'),
        'token_use': claims.get('token_use'),
        'client_id': claims.get('client_id'),
        'iss': claims.get('iss'),
        'exp': claims.get('exp'),
        'iat': claims.get('iat'),
    }

    # Clean up None values
    return {k: v for k, v in user_info.items() if v is not None}


def check_user_roles(user_groups: list[str], required_roles: list[str]) -> bool:
    """
    Check if user has any of the required roles
    
    Args:
        user_groups: List of user's groups from Cognito
        required_roles: List of required roles
        
    Returns:
        True if user has at least one required role
    """
    if not required_roles:
        return True

    return any(role in user_groups for role in required_roles)


def require_auth(required_roles: list[str] | None = None):
    """
    Decorator to require authentication for API endpoints
    
    Args:
        required_roles: Optional list of required roles
        
    Usage:
        @require_auth()
        def my_endpoint():
            pass
            
        @require_auth(['admin', 'manager'])
        def admin_endpoint():
            pass
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            from flask import g, request

            # Extract token from Authorization header
            auth_header = request.headers.get('Authorization', '')
            if not auth_header.startswith('Bearer '):
                raise AuthenticationError("Missing or invalid Authorization header")

            token = auth_header[7:]  # Remove 'Bearer ' prefix

            # Verify token
            claims = verify_jwt_token(token)

            # Extract user info
            user_info = extract_user_info(claims)

            # Check roles if specified
            if required_roles:
                user_groups = user_info.get('groups', [])
                if not check_user_roles(user_groups, required_roles):
                    raise AuthorizationError(
                        f"Insufficient permissions. Required roles: {required_roles}, "
                        f"User roles: {user_groups}"
                    )

            # Store user info in Flask g object for access in the endpoint
            g.current_user = user_info
            g.jwt_claims = claims

            return func(*args, **kwargs)
        return wrapper
    return decorator


def require_admin(func):
    """
    Decorator to require admin role
    """
    return require_auth(['admin'])(func)


def require_viewer_or_admin(func):
    """
    Decorator to require viewer or admin role
    """
    return require_auth(['viewer', 'admin'])(func)


class CognitoJWTAuth:
    """
    Cognito JWT Authentication class for use with Flask applications
    """

    def __init__(self, app=None):
        self.app = app
        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        """Initialize the authentication with Flask app"""
        self.app = app

        # Add error handlers
        @app.errorhandler(AuthenticationError)
        def handle_auth_error(error):
            return {'error': 'Authentication failed', 'message': str(error)}, 401

        @app.errorhandler(AuthorizationError)
        def handle_authz_error(error):
            return {'error': 'Authorization failed', 'message': str(error)}, 403

    def verify_token(self, token: str) -> dict[str, Any]:
        """Verify JWT token"""
        return verify_jwt_token(token)

    def get_user_info(self, claims: dict[str, Any]) -> dict[str, Any]:
        """Get user info from claims"""
        return extract_user_info(claims)
