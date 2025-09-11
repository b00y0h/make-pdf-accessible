"""
Demo Session Management for Anonymous Uploads

Tracks demo uploads by session/IP to enable:
- Rate limiting per session/IP
- Attribution of anonymous uploads to users after signup
- Preview access without authentication
"""

from datetime import datetime, timedelta
from typing import Optional

from pydantic import BaseModel, Field
from pymongo import ASCENDING, DESCENDING, IndexModel
from pymongo.errors import DuplicateKeyError

from .repository import BaseRepository


class DemoSession(BaseModel):
    """Demo session for tracking anonymous uploads"""

    session_id: str = Field(..., description="Unique session identifier (fingerprint)")
    ip_address: str = Field(..., description="IP address of the user")
    user_agent: str = Field(..., description="Browser user agent")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_activity: datetime = Field(default_factory=datetime.utcnow)

    # Upload tracking
    document_ids: list[str] = Field(default_factory=list, description="List of uploaded document IDs")
    upload_count: int = Field(default=0, description="Total uploads in this session")
    last_upload_at: Optional[datetime] = Field(None, description="Last upload timestamp")

    # User attribution
    claimed_by_user: Optional[str] = Field(None, description="User ID who claimed these uploads")
    claimed_at: Optional[datetime] = Field(None, description="When the session was claimed")

    # Rate limiting
    hourly_uploads: int = Field(default=0, description="Uploads in the last hour")
    hourly_reset_at: datetime = Field(default_factory=lambda: datetime.utcnow() + timedelta(hours=1))

    # Browser fingerprint components
    fingerprint_data: dict = Field(default_factory=dict, description="Browser fingerprint data")


class DemoSessionRepository(BaseRepository):
    """Repository for managing demo sessions"""

    def __init__(self, db_name: str = None):
        super().__init__(collection_name="demo_sessions")
        self._ensure_indexes()

    def _ensure_indexes(self):
        """Create indexes for demo sessions collection"""
        indexes = [
            IndexModel([("session_id", ASCENDING)], unique=True),
            IndexModel([("ip_address", ASCENDING)]),
            IndexModel([("created_at", DESCENDING)]),
            IndexModel([("last_activity", DESCENDING)]),
            IndexModel([("claimed_by_user", ASCENDING)]),
            IndexModel([("document_ids", ASCENDING)]),
            # TTL index to auto-delete old unclaimed sessions after 30 days
            IndexModel(
                [("last_activity", ASCENDING)],
                expireAfterSeconds=30 * 24 * 60 * 60,  # 30 days
                partialFilterExpression={"claimed_by_user": None}
            ),
        ]
        self.collection.create_indexes(indexes)

    def get_or_create_session(
        self,
        session_id: str,
        ip_address: str,
        user_agent: str,
        fingerprint_data: dict = None
    ) -> DemoSession:
        """Get existing session or create new one"""

        # Try to find existing session
        session_doc = self.collection.find_one({"session_id": session_id})

        if session_doc:
            # Update last activity
            self.collection.update_one(
                {"session_id": session_id},
                {"$set": {"last_activity": datetime.utcnow()}}
            )
            return DemoSession(**session_doc)

        # Create new session
        session = DemoSession(
            session_id=session_id,
            ip_address=ip_address,
            user_agent=user_agent,
            fingerprint_data=fingerprint_data or {}
        )

        try:
            self.collection.insert_one(session.dict())
            return session
        except DuplicateKeyError:
            # Race condition - session was created by another request
            session_doc = self.collection.find_one({"session_id": session_id})
            return DemoSession(**session_doc)

    def check_rate_limit(self, session_id: str, ip_address: str, max_per_hour: int = 5) -> tuple[bool, str]:
        """
        Check if session/IP is within rate limits

        Returns:
            (allowed, reason) - True if allowed, False with reason if not
        """
        
        # Check if rate limiting is disabled via environment variable
        try:
            import os
            if os.getenv("DISABLE_RATE_LIMITING", "").lower() in ["true", "1", "yes"]:
                return True, "Rate limiting disabled for development"
        except:
            pass

        now = datetime.utcnow()

        # Check session-based limit
        session_doc = self.collection.find_one({"session_id": session_id})
        if session_doc:
            session = DemoSession(**session_doc)

            # Reset hourly counter if needed
            if now >= session.hourly_reset_at:
                self.collection.update_one(
                    {"session_id": session_id},
                    {
                        "$set": {
                            "hourly_uploads": 0,
                            "hourly_reset_at": now + timedelta(hours=1)
                        }
                    }
                )
                session.hourly_uploads = 0

            if session.hourly_uploads >= max_per_hour:
                reset_time = session.hourly_reset_at.strftime("%H:%M UTC")
                return False, f"Rate limit exceeded. Try again after {reset_time}"

        # Check IP-based limit (across all sessions)
        hour_ago = now - timedelta(hours=1)
        ip_uploads = self.collection.count_documents({
            "ip_address": ip_address,
            "last_upload_at": {"$gte": hour_ago}
        })

        if ip_uploads >= max_per_hour * 2:  # Allow 2x limit per IP
            return False, "Too many uploads from this IP address. Try again later."

        return True, "OK"

    def record_upload(self, session_id: str, document_id: str) -> DemoSession:
        """Record a new upload for the session"""

        now = datetime.utcnow()

        result = self.collection.find_one_and_update(
            {"session_id": session_id},
            {
                "$push": {"document_ids": document_id},
                "$inc": {"upload_count": 1, "hourly_uploads": 1},
                "$set": {
                    "last_upload_at": now,
                    "last_activity": now
                }
            },
            return_document=True
        )

        return DemoSession(**result) if result else None

    def claim_session(self, session_id: str, user_id: str) -> bool:
        """
        Claim a demo session for a user after signup/login

        This transfers ownership of all documents to the user
        """

        result = self.collection.update_one(
            {
                "session_id": session_id,
                "claimed_by_user": None  # Only claim unclaimed sessions
            },
            {
                "$set": {
                    "claimed_by_user": user_id,
                    "claimed_at": datetime.utcnow()
                }
            }
        )

        return result.modified_count > 0

    def get_session_documents(self, session_id: str) -> list[str]:
        """Get all document IDs for a session"""

        session_doc = self.collection.find_one(
            {"session_id": session_id},
            {"document_ids": 1}
        )

        return session_doc.get("document_ids", []) if session_doc else []

    def get_unclaimed_sessions_by_ip(self, ip_address: str, limit: int = 10) -> list[DemoSession]:
        """Get recent unclaimed sessions from an IP (for auto-attribution)"""

        cursor = self.collection.find(
            {
                "ip_address": ip_address,
                "claimed_by_user": None
            }
        ).sort("created_at", DESCENDING).limit(limit)

        return [DemoSession(**doc) for doc in cursor]

    def cleanup_old_sessions(self, days: int = 30):
        """Manually cleanup old unclaimed sessions (backup to TTL index)"""

        cutoff = datetime.utcnow() - timedelta(days=days)

        result = self.collection.delete_many({
            "last_activity": {"$lt": cutoff},
            "claimed_by_user": None
        })

        return result.deleted_count


# Singleton instance
_demo_session_repo = None


def get_demo_session_repository(db_name: str = None) -> DemoSessionRepository:
    """Get or create the demo session repository singleton"""
    global _demo_session_repo
    if _demo_session_repo is None:
        _demo_session_repo = DemoSessionRepository(db_name)
    return _demo_session_repo
