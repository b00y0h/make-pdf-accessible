from aws_lambda_powertools import Logger
from fastapi import APIRouter, Depends

from ..auth import User, get_current_user

logger = Logger()

router = APIRouter(prefix="/auth", tags=["auth"])


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
