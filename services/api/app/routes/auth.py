import hashlib
import secrets
from datetime import datetime
from typing import Optional

from aws_lambda_powertools import Logger
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, EmailStr

from ..auth import User, get_current_user

logger = Logger()

router = APIRouter(prefix="/auth", tags=["auth"])
security = HTTPBearer(auto_error=False)

# Simple in-memory store for demo (replace with database in production)
users_db = {}
tokens_db = {}


class SignInRequest(BaseModel):
    email: EmailStr
    password: str


class SignUpRequest(BaseModel):
    email: EmailStr
    password: str
    name: Optional[str] = None


class AuthResponse(BaseModel):
    token: str
    user: dict


def hash_password(password: str) -> str:
    """Simple password hashing for demo"""
    return hashlib.sha256(password.encode()).hexdigest()


def create_token() -> str:
    """Create a simple random token"""
    return secrets.token_urlsafe(32)


@router.get(
    "/me",
    summary="Get current user profile",
    description="Get the current authenticated user's profile information from JWT claims.",
)
async def get_user_profile(current_user: User = Depends(get_current_user)) -> dict:
    """Get current user profile from JWT claims"""

    logger.info("User profile requested", extra={"user_id": current_user.sub})

    return {
        "sub": current_user.sub,
        "name": current_user.name,
        "email": current_user.email,
        "role": current_user.role,
        "orgId": current_user.org_id,
        "claims": {
            key: value
            for key, value in current_user.token_claims.items()
            if key in ["sub", "name", "email", "role", "orgId", "aud", "iss", "exp"]
        },
    }


@router.post("/sign-up", response_model=AuthResponse)
async def sign_up(request: SignUpRequest):
    """Sign up a new user"""
    # Check if user already exists
    if request.email in users_db:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User already exists"
        )

    # Create user
    user = {
        "id": secrets.token_hex(8),
        "email": request.email,
        "name": request.name or request.email.split('@')[0],
        "password_hash": hash_password(request.password),
        "created_at": datetime.utcnow().isoformat()
    }
    users_db[request.email] = user

    # Create token
    token = create_token()
    tokens_db[token] = request.email

    # Return user info without password
    user_response = {
        "id": user["id"],
        "email": user["email"],
        "name": user["name"]
    }

    return AuthResponse(token=token, user=user_response)


@router.post("/sign-in", response_model=AuthResponse)
async def sign_in(request: SignInRequest):
    """Sign in an existing user"""
    # Check if user exists
    if request.email not in users_db:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    user = users_db[request.email]

    # Verify password
    if user["password_hash"] != hash_password(request.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    # Create token
    token = create_token()
    tokens_db[token] = request.email

    # Return user info without password
    user_response = {
        "id": user["id"],
        "email": user["email"],
        "name": user["name"]
    }

    return AuthResponse(token=token, user=user_response)


@router.get("/verify")
async def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Verify if token is valid"""
    if not credentials or credentials.credentials not in tokens_db:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )

    user_email = tokens_db[credentials.credentials]
    current_user = users_db.get(user_email)

    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )

    return {
        "valid": True,
        "user": {
            "id": current_user["id"],
            "email": current_user["email"],
            "name": current_user["name"]
        }
    }
