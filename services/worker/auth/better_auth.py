"""
BetterAuth JWT Authentication module for worker service
"""
import time
from functools import wraps
from typing import Any, Dict, Optional

from jose import JWTError, jwt
from jose.exceptions import ExpiredSignatureError, JWTClaimsError

from ..src.pdf_worker.core.config import config
from ..src.pdf_worker.core.exceptions import AuthenticationError, AuthorizationError


class BetterAuthJWT:
    """
    BetterAuth JWT Authentication class for worker service
    """
    
    def __init__(self):
        self.secret_key = self._get_better_auth_secret()
        self.algorithm = "HS256"
        self.issuer = "accesspdf-dashboard"
        self.audience = "accesspdf-api"
    
    def _get_better_auth_secret(self) -> str:
        """Get BetterAuth secret from environment"""
        import os
        secret = os.getenv("API_JWT_SECRET", "")
        if not secret:
            raise AuthenticationError("BetterAuth secret not configured (API_JWT_SECRET)")
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
                    "verify_signature": True
                }
            )
            
            # Validate required claims exist
            if not claims.get('sub'):
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
    
    def extract_user_info(self, claims: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract user information from BetterAuth JWT claims
        
        Args:
            claims: JWT claims dictionary
            
        Returns:
            Dict containing user information
        """
        user_info = {
            'sub': claims.get('sub'),  # User ID
            'email': claims.get('email'),
            'name': claims.get('name'),
            'role': claims.get('role', 'viewer'),
            'org_id': claims.get('org_id'),  # Organization/tenant ID
            'iss': claims.get('iss'),
            'aud': claims.get('aud'),
            'exp': claims.get('exp'),
            'iat': claims.get('iat'),
            'token_type': 'better_auth'  # Mark as BetterAuth token
        }
        
        # Clean up None values
        return {k: v for k, v in user_info.items() if v is not None}
    
    def check_user_roles(self, user_role: str, required_roles: list[str]) -> bool:
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


def require_auth(required_roles: Optional[list[str]] = None):
    """
    Decorator to require BetterAuth authentication for worker endpoints
    
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
            
            auth = BetterAuthJWT()
            
            # Extract token from Authorization header
            auth_header = request.headers.get('Authorization', '')
            if not auth_header.startswith('Bearer '):
                raise AuthenticationError("Missing or invalid Authorization header")
            
            token = auth_header[7:]  # Remove 'Bearer ' prefix
            
            # Verify token
            claims = auth.verify_jwt_token(token)
            
            # Extract user info
            user_info = auth.extract_user_info(claims)
            
            # Check roles if specified
            if required_roles:
                user_role = user_info.get('role', 'viewer')
                if not auth.check_user_roles(user_role, required_roles):
                    raise AuthorizationError(
                        f"Insufficient permissions. Required roles: {required_roles}, "
                        f"User role: {user_role}"
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


# Global BetterAuth instance
better_auth = BetterAuthJWT()