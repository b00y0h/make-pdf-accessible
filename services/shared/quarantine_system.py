"""
File Quarantine System

This module provides a comprehensive quarantine system for isolating and managing
suspicious files that fail security validation or require additional review.
"""

import hashlib
import json
import os
import shutil
import tempfile
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional


class QuarantineReason(Enum):
    """Reasons for file quarantine"""

    VIRUS_DETECTED = "virus_detected"
    MALICIOUS_CONTENT = "malicious_content"
    SUSPICIOUS_SIGNATURE = "suspicious_signature"
    FILE_TYPE_SPOOFING = "file_type_spoofing"
    DANGEROUS_FILE_TYPE = "dangerous_file_type"
    CONTENT_VALIDATION_FAILED = "content_validation_failed"
    EXCESSIVE_SIZE = "excessive_size"
    POLICY_VIOLATION = "policy_violation"
    MANUAL_REVIEW_REQUIRED = "manual_review_required"
    UNKNOWN_THREAT = "unknown_threat"


class QuarantineStatus(Enum):
    """Status of quarantined files"""

    QUARANTINED = "quarantined"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    DELETED = "deleted"
    EXPIRED = "expired"


@dataclass
class QuarantineRecord:
    """Record of a quarantined file"""

    quarantine_id: str
    original_filename: str
    file_hash: str
    file_size: int
    quarantine_reason: QuarantineReason
    quarantine_status: QuarantineStatus
    quarantined_at: str
    user_id: str
    org_id: Optional[str]
    threat_level: str  # "low", "medium", "high", "critical"
    validation_details: Dict[str, Any]
    review_notes: List[str]
    reviewer_id: Optional[str]
    reviewed_at: Optional[str]
    expires_at: str
    storage_path: str
    metadata: Dict[str, Any]


class QuarantineSystem:
    """
    Comprehensive file quarantine system for managing suspicious files
    """

    def __init__(self, quarantine_dir: str = None, max_retention_days: int = 30):
        """
        Initialize quarantine system

        Args:
            quarantine_dir: Directory for quarantine storage
            max_retention_days: Maximum days to retain quarantined files
        """
        self.quarantine_dir = quarantine_dir or self._get_default_quarantine_dir()
        self.max_retention_days = max_retention_days

        # Ensure quarantine directory exists
        os.makedirs(self.quarantine_dir, exist_ok=True)
        os.makedirs(os.path.join(self.quarantine_dir, "files"), exist_ok=True)
        os.makedirs(os.path.join(self.quarantine_dir, "records"), exist_ok=True)
        os.makedirs(os.path.join(self.quarantine_dir, "logs"), exist_ok=True)

        # Create access log
        self.access_log_path = os.path.join(self.quarantine_dir, "logs", "access.log")

    def _get_default_quarantine_dir(self) -> str:
        """Get default quarantine directory"""
        base_dir = os.getenv("QUARANTINE_DIR", tempfile.gettempdir())
        return os.path.join(base_dir, "pdf_accessibility_quarantine")

    def quarantine_file(
        self,
        file_path: str,
        original_filename: str,
        user_id: str,
        quarantine_reason: QuarantineReason,
        threat_level: str = "medium",
        validation_details: Dict[str, Any] = None,
        org_id: str = None,
        metadata: Dict[str, Any] = None,
    ) -> str:
        """
        Quarantine a suspicious file

        Args:
            file_path: Path to the file to quarantine
            original_filename: Original filename
            user_id: User who uploaded the file
            quarantine_reason: Reason for quarantine
            threat_level: Threat level assessment
            validation_details: Details from security validation
            org_id: Organization ID
            metadata: Additional metadata

        Returns:
            Quarantine ID
        """
        try:
            # Generate quarantine ID
            quarantine_id = str(uuid.uuid4())

            # Calculate file hash
            file_hash = self._calculate_file_hash(file_path)
            file_size = os.path.getsize(file_path)

            # Check for duplicate quarantine
            existing_record = self._find_by_hash(file_hash)
            if existing_record:
                self._log_access(
                    "DUPLICATE_QUARANTINE_ATTEMPT",
                    quarantine_id,
                    user_id,
                    f"File already quarantined: {existing_record.quarantine_id}",
                )
                return existing_record.quarantine_id

            # Create storage path
            storage_filename = f"{quarantine_id}_{file_hash[:8]}"
            storage_path = os.path.join(self.quarantine_dir, "files", storage_filename)

            # Copy file to quarantine storage
            shutil.copy2(file_path, storage_path)

            # Set restrictive permissions
            os.chmod(storage_path, 0o600)  # Read/write for owner only

            # Calculate expiration date
            expires_at = (
                datetime.utcnow() + timedelta(days=self.max_retention_days)
            ).isoformat()

            # Create quarantine record
            record = QuarantineRecord(
                quarantine_id=quarantine_id,
                original_filename=original_filename,
                file_hash=file_hash,
                file_size=file_size,
                quarantine_reason=quarantine_reason,
                quarantine_status=QuarantineStatus.QUARANTINED,
                quarantined_at=datetime.utcnow().isoformat(),
                user_id=user_id,
                org_id=org_id,
                threat_level=threat_level,
                validation_details=validation_details or {},
                review_notes=[],
                reviewer_id=None,
                reviewed_at=None,
                expires_at=expires_at,
                storage_path=storage_path,
                metadata=metadata or {},
            )

            # Save record
            self._save_record(record)

            # Log quarantine action
            self._log_access(
                "FILE_QUARANTINED",
                quarantine_id,
                user_id,
                f"File quarantined: {original_filename}, reason: {quarantine_reason.value}, threat: {threat_level}",
            )

            return quarantine_id

        except Exception as e:
            self._log_access(
                "QUARANTINE_ERROR",
                "unknown",
                user_id,
                f"Failed to quarantine file {original_filename}: {str(e)}",
            )
            raise Exception(f"Failed to quarantine file: {str(e)}")

    def get_quarantine_record(self, quarantine_id: str) -> Optional[QuarantineRecord]:
        """
        Get quarantine record by ID

        Args:
            quarantine_id: Quarantine ID

        Returns:
            QuarantineRecord if found, None otherwise
        """
        try:
            record_path = os.path.join(
                self.quarantine_dir, "records", f"{quarantine_id}.json"
            )
            if os.path.exists(record_path):
                with open(record_path) as f:
                    data = json.load(f)

                # Convert enums back from strings
                data["quarantine_reason"] = QuarantineReason(data["quarantine_reason"])
                data["quarantine_status"] = QuarantineStatus(data["quarantine_status"])

                return QuarantineRecord(**data)
            return None
        except Exception:
            return None

    def list_quarantined_files(
        self,
        user_id: str = None,
        org_id: str = None,
        status: QuarantineStatus = None,
        threat_level: str = None,
        limit: int = 100,
    ) -> List[QuarantineRecord]:
        """
        List quarantined files with optional filters

        Args:
            user_id: Filter by user ID
            org_id: Filter by organization ID
            status: Filter by quarantine status
            threat_level: Filter by threat level
            limit: Maximum number of records to return

        Returns:
            List of QuarantineRecord objects
        """
        records = []
        records_dir = os.path.join(self.quarantine_dir, "records")

        if not os.path.exists(records_dir):
            return records

        for filename in os.listdir(records_dir):
            if not filename.endswith(".json"):
                continue

            try:
                record = self.get_quarantine_record(
                    filename[:-5]
                )  # Remove .json extension
                if not record:
                    continue

                # Apply filters
                if user_id and record.user_id != user_id:
                    continue
                if org_id and record.org_id != org_id:
                    continue
                if status and record.quarantine_status != status:
                    continue
                if threat_level and record.threat_level != threat_level:
                    continue

                records.append(record)

                if len(records) >= limit:
                    break

            except Exception:
                continue

        # Sort by quarantined date (newest first)
        records.sort(key=lambda r: r.quarantined_at, reverse=True)
        return records

    def update_quarantine_status(
        self,
        quarantine_id: str,
        new_status: QuarantineStatus,
        reviewer_id: str,
        review_notes: str = None,
    ) -> bool:
        """
        Update quarantine status

        Args:
            quarantine_id: Quarantine ID
            new_status: New status
            reviewer_id: ID of the reviewer
            review_notes: Optional review notes

        Returns:
            True if updated successfully
        """
        try:
            record = self.get_quarantine_record(quarantine_id)
            if not record:
                return False

            # Update record
            record.quarantine_status = new_status
            record.reviewer_id = reviewer_id
            record.reviewed_at = datetime.utcnow().isoformat()

            if review_notes:
                record.review_notes.append(
                    f"{datetime.utcnow().isoformat()}: {review_notes}"
                )

            # Save updated record
            self._save_record(record)

            # Log status change
            self._log_access(
                "STATUS_UPDATED",
                quarantine_id,
                reviewer_id,
                f"Status changed to {new_status.value}: {review_notes or 'No notes'}",
            )

            # Handle status-specific actions
            if new_status == QuarantineStatus.APPROVED:
                self._handle_approved_file(record)
            elif new_status == QuarantineStatus.REJECTED:
                self._handle_rejected_file(record)
            elif new_status == QuarantineStatus.DELETED:
                self._handle_deleted_file(record)

            return True

        except Exception as e:
            self._log_access(
                "STATUS_UPDATE_ERROR",
                quarantine_id,
                reviewer_id,
                f"Failed to update status: {str(e)}",
            )
            return False

    def retrieve_quarantined_file(
        self, quarantine_id: str, reviewer_id: str
    ) -> Optional[str]:
        """
        Retrieve a quarantined file for review (creates temporary copy)

        Args:
            quarantine_id: Quarantine ID
            reviewer_id: ID of the reviewer

        Returns:
            Path to temporary copy of the file, or None if not found
        """
        try:
            record = self.get_quarantine_record(quarantine_id)
            if not record:
                return None

            if not os.path.exists(record.storage_path):
                return None

            # Create temporary copy for review
            temp_dir = tempfile.mkdtemp(prefix="quarantine_review_")
            temp_path = os.path.join(temp_dir, record.original_filename)
            shutil.copy2(record.storage_path, temp_path)

            # Log file access
            self._log_access(
                "FILE_RETRIEVED",
                quarantine_id,
                reviewer_id,
                f"File retrieved for review: {record.original_filename}",
            )

            return temp_path

        except Exception as e:
            self._log_access(
                "RETRIEVAL_ERROR",
                quarantine_id,
                reviewer_id,
                f"Failed to retrieve file: {str(e)}",
            )
            return None

    def cleanup_expired_files(self) -> int:
        """
        Clean up expired quarantined files

        Returns:
            Number of files cleaned up
        """
        cleaned_count = 0
        current_time = datetime.utcnow()

        try:
            records = self.list_quarantined_files(limit=1000)

            for record in records:
                try:
                    expires_at = datetime.fromisoformat(record.expires_at)

                    if current_time > expires_at:
                        # Mark as expired and delete
                        record.quarantine_status = QuarantineStatus.EXPIRED
                        self._save_record(record)

                        # Delete file if it exists
                        if os.path.exists(record.storage_path):
                            os.remove(record.storage_path)

                        cleaned_count += 1

                        self._log_access(
                            "FILE_EXPIRED",
                            record.quarantine_id,
                            "system",
                            f"Expired file cleaned up: {record.original_filename}",
                        )

                except Exception as e:
                    self._log_access(
                        "CLEANUP_ERROR",
                        record.quarantine_id,
                        "system",
                        f"Error cleaning up expired file: {str(e)}",
                    )
                    continue

            return cleaned_count

        except Exception as e:
            self._log_access(
                "CLEANUP_SYSTEM_ERROR",
                "unknown",
                "system",
                f"System error during cleanup: {str(e)}",
            )
            return cleaned_count

    def get_quarantine_statistics(self) -> Dict[str, Any]:
        """
        Get quarantine system statistics

        Returns:
            Dictionary with statistics
        """
        try:
            records = self.list_quarantined_files(limit=10000)

            stats = {
                "total_files": len(records),
                "by_status": {},
                "by_threat_level": {},
                "by_reason": {},
                "files_under_review": 0,
                "files_pending_action": 0,
                "oldest_quarantine": None,
                "newest_quarantine": None,
                "total_size_bytes": 0,
            }

            if not records:
                return stats

            # Calculate statistics
            for record in records:
                # Count by status
                status_key = record.quarantine_status.value
                stats["by_status"][status_key] = (
                    stats["by_status"].get(status_key, 0) + 1
                )

                # Count by threat level
                threat_key = record.threat_level
                stats["by_threat_level"][threat_key] = (
                    stats["by_threat_level"].get(threat_key, 0) + 1
                )

                # Count by reason
                reason_key = record.quarantine_reason.value
                stats["by_reason"][reason_key] = (
                    stats["by_reason"].get(reason_key, 0) + 1
                )

                # Count files needing attention
                if record.quarantine_status == QuarantineStatus.UNDER_REVIEW:
                    stats["files_under_review"] += 1
                elif record.quarantine_status == QuarantineStatus.QUARANTINED:
                    stats["files_pending_action"] += 1

                # Track size
                stats["total_size_bytes"] += record.file_size

            # Find oldest and newest
            stats["oldest_quarantine"] = min(
                records, key=lambda r: r.quarantined_at
            ).quarantined_at
            stats["newest_quarantine"] = max(
                records, key=lambda r: r.quarantined_at
            ).quarantined_at

            return stats

        except Exception:
            return {"error": "Failed to calculate statistics"}

    def _calculate_file_hash(self, file_path: str) -> str:
        """Calculate SHA-256 hash of file"""
        hash_sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()

    def _find_by_hash(self, file_hash: str) -> Optional[QuarantineRecord]:
        """Find quarantine record by file hash"""
        records = self.list_quarantined_files(limit=10000)
        for record in records:
            if record.file_hash == file_hash:
                return record
        return None

    def _save_record(self, record: QuarantineRecord):
        """Save quarantine record to disk"""
        record_path = os.path.join(
            self.quarantine_dir, "records", f"{record.quarantine_id}.json"
        )

        # Convert record to dict and handle enums
        record_dict = asdict(record)
        record_dict["quarantine_reason"] = record.quarantine_reason.value
        record_dict["quarantine_status"] = record.quarantine_status.value

        with open(record_path, "w") as f:
            json.dump(record_dict, f, indent=2)

    def _log_access(self, action: str, quarantine_id: str, user_id: str, details: str):
        """Log access to quarantine system"""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "action": action,
            "quarantine_id": quarantine_id,
            "user_id": user_id,
            "details": details,
        }

        try:
            with open(self.access_log_path, "a") as f:
                f.write(json.dumps(log_entry) + "\n")
        except:
            pass  # Don't fail if logging fails

    def _handle_approved_file(self, record: QuarantineRecord):
        """Handle approved file - could move to safe storage"""
        # In a real implementation, you might move the file to safe storage
        # or notify the user that their file has been approved
        pass

    def _handle_rejected_file(self, record: QuarantineRecord):
        """Handle rejected file - could notify user"""
        # In a real implementation, you might notify the user
        # that their file was rejected and provide guidance
        pass

    def _handle_deleted_file(self, record: QuarantineRecord):
        """Handle deleted file - remove from storage"""
        try:
            if os.path.exists(record.storage_path):
                os.remove(record.storage_path)
        except:
            pass


# Global quarantine system instance
quarantine_system = QuarantineSystem()


def quarantine_suspicious_file(
    file_path: str,
    original_filename: str,
    user_id: str,
    reason: QuarantineReason,
    threat_level: str = "medium",
    validation_details: Dict[str, Any] = None,
    org_id: str = None,
) -> str:
    """
    Convenience function to quarantine a suspicious file

    Args:
        file_path: Path to file to quarantine
        original_filename: Original filename
        user_id: User who uploaded the file
        reason: Reason for quarantine
        threat_level: Threat level assessment
        validation_details: Security validation details
        org_id: Organization ID

    Returns:
        Quarantine ID
    """
    return quarantine_system.quarantine_file(
        file_path,
        original_filename,
        user_id,
        reason,
        threat_level,
        validation_details,
        org_id,
    )


# Export commonly used items
__all__ = [
    "QuarantineReason",
    "QuarantineStatus",
    "QuarantineRecord",
    "QuarantineSystem",
    "quarantine_system",
    "quarantine_suspicious_file",
]
