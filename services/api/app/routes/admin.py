import math
import sqlite3
from pathlib import Path
from typing import Optional

from aws_lambda_powertools import Logger
from fastapi import APIRouter, HTTPException, Query, Request, status
from fastapi.responses import JSONResponse

from ..auth import get_admin_user
from ..models import UserListResponse, UserSummary

logger = Logger()

router = APIRouter(prefix="/admin", tags=["admin"])


def get_better_auth_db_path() -> str:
    """Get the BetterAuth SQLite database path"""
    # Both API and dashboard containers mount the auth_data volume
    # The database file is stored in the shared volume
    shared_path = "/app/auth_data/sqlite.db"

    if Path(shared_path).exists():
        return shared_path

    # Fallback for local development outside Docker
    local_path = "./sqlite.db"
    return local_path


def get_better_auth_db():
    """Get connection to BetterAuth SQLite database"""
    db_path = get_better_auth_db_path()
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row  # Enable column access by name
        return conn
    except Exception as e:
        logger.error(f"Failed to connect to BetterAuth database at {db_path}: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="User database unavailable",
        )


def get_document_stats(user_id: str) -> dict:
    """Get document statistics for a user from MongoDB"""
    # TODO: Connect to MongoDB and get actual document stats
    # For now, return placeholder data
    return {
        "document_count": 0,
        "documents_completed": 0,
        "documents_processing": 0,
        "documents_failed": 0,
    }


@router.get(
    "/users",
    response_model=UserListResponse,
    summary="Get users list",
    description="Get paginated list of users with search and filtering capabilities. Admin access required.",
)
async def get_users(
    request: Request,
    page: int = Query(1, ge=1, description="Page number"),
    pageSize: int = Query(
        20, ge=1, le=100, description="Items per page", alias="pageSize"
    ),
    sortBy: str = Query("createdAt", description="Sort field", alias="sortBy"),
    sortOrder: str = Query(
        "desc", description="Sort order (asc/desc)", alias="sortOrder"
    ),
    search: Optional[str] = Query(None, description="Search term"),
    role: Optional[str] = Query(None, description="Role filter"),
) -> JSONResponse:
    """Get users list with pagination and filtering"""

    # Validate admin access
    current_user = await get_admin_user(request)

    logger.info(
        "Admin users list requested",
        extra={
            "admin_user_id": current_user.sub,
            "page": page,
            "page_size": pageSize,
            "search": search,
            "role": role,
        },
    )

    try:
        conn = get_better_auth_db()

        # Build the SQL query
        where_conditions = []
        params = []

        # Search functionality
        if search:
            where_conditions.append("(name LIKE ? OR email LIKE ?)")
            search_term = f"%{search}%"
            params.extend([search_term, search_term])

        # Role filter
        if role and role != "all":
            where_conditions.append("role = ?")
            params.append(role)

        where_clause = (
            "WHERE " + " AND ".join(where_conditions) if where_conditions else ""
        )

        # Map frontend sort fields to database columns
        sort_field_map = {
            "createdAt": "createdAt",
            "email": "email",
            "name": "name",
            "documentCount": "createdAt",  # Fallback to createdAt for now since document count is calculated
        }

        db_sort_field = sort_field_map.get(sortBy, "createdAt")
        sort_direction = "DESC" if sortOrder.lower() == "desc" else "ASC"

        # Count total users
        count_query = f"SELECT COUNT(*) as total FROM user {where_clause}"
        cursor = conn.execute(count_query, params)
        total = cursor.fetchone()["total"]

        # Calculate pagination
        total_pages = math.ceil(total / pageSize) if total > 0 else 1
        offset = (page - 1) * pageSize

        # Get users with pagination
        users_query = f"""
            SELECT id, name, email, role, createdAt, updatedAt
            FROM user
            {where_clause}
            ORDER BY {db_sort_field} {sort_direction}
            LIMIT ? OFFSET ?
        """
        params.extend([pageSize, offset])

        cursor = conn.execute(users_query, params)
        rows = cursor.fetchall()

        # Convert to UserSummary objects with document stats
        users = []
        for row in rows:
            # Get document statistics for this user
            doc_stats = get_document_stats(row["id"])

            user_summary = UserSummary(
                id=row["id"],
                name=row["name"],
                email=row["email"],
                role=row["role"] or "user",
                created_at=row["createdAt"],
                updated_at=row["updatedAt"],
                last_activity=None,  # BetterAuth doesn't track this by default
                **doc_stats,
            )
            users.append(user_summary)

        conn.close()

        response_data = UserListResponse(
            users=users,
            total=total,
            total_pages=total_pages,
            current_page=page,
            page_size=pageSize,
        )

        return JSONResponse(
            content={"success": True, "data": response_data.model_dump()}
        )

    except Exception as e:
        logger.exception(f"Error fetching users: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"success": False, "error": f"Failed to fetch users: {str(e)}"},
        )


@router.get(
    "/users/{user_id}",
    response_model=UserSummary,
    summary="Get user details",
    description="Get detailed information about a specific user. Admin access required.",
)
async def get_user(
    request: Request,
    user_id: str,
) -> JSONResponse:
    """Get detailed user information"""

    # Validate admin access
    current_user = await get_admin_user(request)

    logger.info(
        "Admin user detail requested",
        extra={"admin_user_id": current_user.sub, "target_user_id": user_id},
    )

    try:
        conn = get_better_auth_db()

        cursor = conn.execute(
            "SELECT id, name, email, role, createdAt, updatedAt FROM user WHERE id = ?",
            (user_id,),
        )
        row = cursor.fetchone()

        if not row:
            conn.close()
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"success": False, "error": "User not found"},
            )

        # Get document statistics
        doc_stats = get_document_stats(user_id)

        user_summary = UserSummary(
            id=row["id"],
            name=row["name"],
            email=row["email"],
            role=row["role"] or "user",
            created_at=row["createdAt"],
            updated_at=row["updatedAt"],
            last_activity=None,
            **doc_stats,
        )

        conn.close()

        return JSONResponse(
            content={"success": True, "data": user_summary.model_dump()}
        )

    except Exception as e:
        logger.exception(f"Error fetching user {user_id}: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"success": False, "error": f"Failed to fetch user: {str(e)}"},
        )


@router.delete(
    "/users/{user_id}",
    summary="Delete user",
    description="Delete a user account and all associated data. Admin access required.",
)
async def delete_user(
    request: Request,
    user_id: str,
) -> JSONResponse:
    """Delete a user account"""

    # Validate admin access
    current_user = await get_admin_user(request)

    # Prevent admin from deleting themselves
    if current_user.sub == user_id:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"success": False, "error": "Cannot delete your own account"},
        )

    logger.info(
        "Admin user deletion requested",
        extra={"admin_user_id": current_user.sub, "target_user_id": user_id},
    )

    try:
        conn = get_better_auth_db()

        # Check if user exists
        cursor = conn.execute("SELECT id, role FROM user WHERE id = ?", (user_id,))
        row = cursor.fetchone()

        if not row:
            conn.close()
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"success": False, "error": "User not found"},
            )

        # Prevent deleting other admin users
        if row["role"] == "admin":
            conn.close()
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"success": False, "error": "Cannot delete admin users"},
            )

        # Delete user from BetterAuth database
        conn.execute("DELETE FROM user WHERE id = ?", (user_id,))

        # Also delete any related session data
        conn.execute("DELETE FROM session WHERE userId = ?", (user_id,))

        conn.commit()
        conn.close()

        # TODO: Also delete user's documents from MongoDB

        logger.info(f"User {user_id} deleted by admin {current_user.sub}")

        return JSONResponse(
            content={"success": True, "message": "User deleted successfully"}
        )

    except Exception as e:
        logger.exception(f"Error deleting user {user_id}: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"success": False, "error": f"Failed to delete user: {str(e)}"},
        )
