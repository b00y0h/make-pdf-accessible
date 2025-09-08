"""Job repository for MongoDB with specialized job operations."""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from pymongo import ASCENDING, DESCENDING

from .repository import BaseRepository
from .connection import get_mongo_connection

logger = logging.getLogger(__name__)


class JobRepository(BaseRepository):
    """Repository for job operations with MongoDB."""
    
    def __init__(self):
        super().__init__('jobs')
    
    def create_job(self, job_data: dict) -> dict:
        """Create a new job with validation."""
        try:
            # Validate required fields
            required_fields = ['jobId', 'docId', 'step', 'status']
            for field in required_fields:
                if field not in job_data:
                    raise ValueError(f"Missing required field: {field}")
            
            # Set default values
            now = datetime.utcnow()
            job_data.setdefault('createdAt', now)
            job_data.setdefault('updatedAt', now)
            job_data.setdefault('priority', 5)
            job_data.setdefault('attempts', 0)
            job_data.setdefault('maxAttempts', 3)
            job_data.setdefault('input', {})
            job_data.setdefault('logs', [])
            job_data.setdefault('retryPolicy', {
                'enabled': True,
                'backoffMultiplier': 2.0,
                'initialDelaySeconds': 30,
                'maxDelaySeconds': 1800
            })
            job_data.setdefault('timeout', {
                'executionTimeoutSeconds': 900,
                'heartbeatIntervalSeconds': 30
            })
            
            return self.create(job_data)
            
        except Exception as e:
            logger.error(f"Error creating job: {e}")
            raise
    
    def get_job(self, job_id: str) -> Optional[dict]:
        """Get job by jobId."""
        return self.find_one({'jobId': job_id}, hint={'jobId': 1})
    
    def get_jobs_for_document(
        self,
        doc_id: str,
        step_filter: Optional[List[str]] = None,
        status_filter: Optional[List[str]] = None
    ) -> List[dict]:
        """Get all jobs for a specific document."""
        try:
            filter_doc = {'docId': doc_id}
            
            if step_filter:
                filter_doc['step'] = {'$in': step_filter}
            
            if status_filter:
                filter_doc['status'] = {'$in': status_filter}
            
            sort = [('updatedAt', DESCENDING)]
            hint = {'docId': 1, 'updatedAt': -1}
            
            return self.find(
                filter_doc=filter_doc,
                sort=sort,
                hint=hint
            )
            
        except Exception as e:
            logger.error(f"Error getting jobs for document {doc_id}: {e}")
            return []
    
    def get_jobs_by_status(
        self,
        status: str,
        step_filter: Optional[List[str]] = None,
        limit: Optional[int] = None,
        priority_order: bool = True
    ) -> List[dict]:
        """Get jobs by status, optionally filtered by step and ordered by priority."""
        try:
            filter_doc = {'status': status}
            
            if step_filter:
                filter_doc['step'] = {'$in': step_filter}
            
            # Build sort order
            if priority_order:
                sort = [('priority', DESCENDING), ('createdAt', ASCENDING)]
                hint = {'status': 1, 'priority': -1, 'createdAt': 1}
            else:
                sort = [('updatedAt', DESCENDING)]
                hint = {'status': 1, 'updatedAt': -1}
            
            return self.find(
                filter_doc=filter_doc,
                sort=sort,
                limit=limit,
                hint=hint
            )
            
        except Exception as e:
            logger.error(f"Error getting jobs by status {status}: {e}")
            return []
    
    def get_pending_jobs(
        self,
        step: Optional[str] = None,
        limit: int = 10,
        priority_threshold: Optional[int] = None
    ) -> List[dict]:
        """Get pending jobs for processing."""
        try:
            filter_doc = {'status': 'pending'}
            
            if step:
                filter_doc['step'] = step
            
            if priority_threshold is not None:
                filter_doc['priority'] = {'$gte': priority_threshold}
            
            # Sort by priority (high to low), then by creation time (old to new)
            sort = [('priority', DESCENDING), ('createdAt', ASCENDING)]
            hint = {'status': 1, 'priority': -1, 'createdAt': 1}
            
            return self.find(
                filter_doc=filter_doc,
                sort=sort,
                limit=limit,
                hint=hint
            )
            
        except Exception as e:
            logger.error(f"Error getting pending jobs: {e}")
            return []
    
    def get_failed_jobs_for_retry(self, max_attempts: int = 3, limit: int = 10) -> List[dict]:
        """Get failed jobs that can be retried."""
        try:
            filter_doc = {
                'status': {'$in': ['failed', 'retry']},
                'attempts': {'$lt': max_attempts},
                'retryPolicy.enabled': True
            }
            
            # Sort by attempts (fewer first), then by update time (oldest first)
            sort = [('attempts', ASCENDING), ('updatedAt', ASCENDING)]
            hint = {'status': 1, 'attempts': 1, 'updatedAt': 1}
            
            return self.find(
                filter_doc=filter_doc,
                sort=sort,
                limit=limit,
                hint=hint
            )
            
        except Exception as e:
            logger.error(f"Error getting failed jobs for retry: {e}")
            return []
    
    def update_job_status(
        self,
        job_id: str,
        status: str,
        started_at: Optional[datetime] = None,
        completed_at: Optional[datetime] = None,
        execution_time_seconds: Optional[float] = None,
        error: Optional[dict] = None,
        output: Optional[dict] = None,
        worker_info: Optional[dict] = None
    ) -> bool:
        """Update job status and related fields."""
        try:
            update_doc = {
                '$set': {
                    'status': status,
                    'updatedAt': datetime.utcnow()
                }
            }
            
            if started_at is not None:
                update_doc['$set']['startedAt'] = started_at
            elif status == 'running' and started_at is None:
                update_doc['$set']['startedAt'] = datetime.utcnow()
            
            if completed_at is not None:
                update_doc['$set']['completedAt'] = completed_at
            elif status in ['completed', 'failed']:
                update_doc['$set']['completedAt'] = datetime.utcnow()
            
            if execution_time_seconds is not None:
                update_doc['$set']['executionTimeSeconds'] = execution_time_seconds
            
            if error is not None:
                update_doc['$set']['error'] = error
            
            if output is not None:
                update_doc['$set']['output'] = output
            
            if worker_info is not None:
                update_doc['$set']['worker'] = worker_info
            
            # Increment attempts for failed jobs
            if status == 'failed':
                update_doc['$inc'] = {'attempts': 1}
            
            return self.update_by_id(
                doc_id=job_id,
                update=update_doc,
                hint={'jobId': 1}
            )
            
        except Exception as e:
            logger.error(f"Error updating job status for {job_id}: {e}")
            return False
    
    def add_job_log(self, job_id: str, log_entry: dict) -> bool:
        """Add log entry to job."""
        try:
            # Ensure log entry has required fields
            log_entry.setdefault('timestamp', datetime.utcnow())
            
            update_doc = {
                '$push': {'logs': log_entry},
                '$set': {'updatedAt': datetime.utcnow()}
            }
            
            return self.update_by_id(
                doc_id=job_id,
                update=update_doc,
                hint={'jobId': 1}
            )
            
        except Exception as e:
            logger.error(f"Error adding log to job {job_id}: {e}")
            return False
    
    def set_job_heartbeat(self, job_id: str, worker_instance_id: str) -> bool:
        """Update job heartbeat to indicate worker is alive."""
        try:
            update_doc = {
                '$set': {
                    'updatedAt': datetime.utcnow(),
                    'worker.lastHeartbeat': datetime.utcnow(),
                    'worker.instanceId': worker_instance_id
                }
            }
            
            return self.update_by_id(
                doc_id=job_id,
                update=update_doc,
                hint={'jobId': 1}
            )
            
        except Exception as e:
            logger.error(f"Error setting heartbeat for job {job_id}: {e}")
            return False
    
    def get_stale_jobs(self, timeout_minutes: int = 30) -> List[dict]:
        """Get jobs that appear to be stuck or have stale heartbeats."""
        try:
            timeout_threshold = datetime.utcnow() - timedelta(minutes=timeout_minutes)
            
            filter_doc = {
                'status': 'running',
                'updatedAt': {'$lt': timeout_threshold}
            }
            
            return self.find(
                filter_doc=filter_doc,
                hint={'status': 1, 'updatedAt': -1}
            )
            
        except Exception as e:
            logger.error(f"Error getting stale jobs: {e}")
            return []
    
    def reset_stale_jobs(self, timeout_minutes: int = 30) -> int:
        """Reset stale running jobs back to pending."""
        try:
            timeout_threshold = datetime.utcnow() - timedelta(minutes=timeout_minutes)
            
            filter_doc = {
                'status': 'running',
                'updatedAt': {'$lt': timeout_threshold}
            }
            
            update_doc = {
                '$set': {
                    'status': 'retry',
                    'updatedAt': datetime.utcnow(),
                    'worker': None
                },
                '$unset': {
                    'startedAt': 1
                }
            }
            
            result = self.collection.update_many(filter_doc, update_doc)
            modified_count = result.modified_count
            
            if modified_count > 0:
                logger.info(f"Reset {modified_count} stale jobs")
            
            return modified_count
            
        except Exception as e:
            logger.error(f"Error resetting stale jobs: {e}")
            return 0
    
    def get_job_statistics(self) -> dict:
        """Get job processing statistics."""
        try:
            pipeline = [
                {
                    '$group': {
                        '_id': '$status',
                        'count': {'$sum': 1},
                        'avg_execution_time': {'$avg': '$executionTimeSeconds'},
                        'avg_attempts': {'$avg': '$attempts'}
                    }
                },
                {
                    '$group': {
                        '_id': None,
                        'total_jobs': {'$sum': '$count'},
                        'jobs_by_status': {
                            '$push': {
                                'status': '$_id',
                                'count': '$count',
                                'avg_execution_time': '$avg_execution_time',
                                'avg_attempts': '$avg_attempts'
                            }
                        }
                    }
                }
            ]
            
            results = self.aggregate(pipeline)
            
            if not results:
                return {
                    'total_jobs': 0,
                    'jobs_by_status': {},
                    'avg_execution_time': 0,
                    'retry_rate': 0
                }
            
            result = results[0]
            status_counts = {item['status']: item['count'] for item in result['jobs_by_status']}
            
            # Calculate retry rate
            total_jobs = result['total_jobs']
            failed_jobs = status_counts.get('failed', 0)
            retry_rate = failed_jobs / total_jobs if total_jobs > 0 else 0
            
            # Calculate overall average execution time
            total_execution_time = sum(
                item['avg_execution_time'] * item['count']
                for item in result['jobs_by_status']
                if item['avg_execution_time'] is not None
            )
            total_completed = sum(
                item['count']
                for item in result['jobs_by_status']
                if item['status'] in ['completed', 'failed'] and item['avg_execution_time'] is not None
            )
            avg_execution_time = total_execution_time / total_completed if total_completed > 0 else 0
            
            return {
                'total_jobs': total_jobs,
                'jobs_by_status': status_counts,
                'avg_execution_time': avg_execution_time,
                'retry_rate': retry_rate
            }
            
        except Exception as e:
            logger.error(f"Error getting job statistics: {e}")
            return {
                'total_jobs': 0,
                'jobs_by_status': {},
                'avg_execution_time': 0,
                'retry_rate': 0
            }
    
    def get_step_performance(self, days: int = 7) -> List[dict]:
        """Get performance statistics by processing step."""
        try:
            start_date = datetime.utcnow() - timedelta(days=days)
            
            pipeline = [
                {
                    '$match': {
                        'createdAt': {'$gte': start_date},
                        'status': {'$in': ['completed', 'failed']}
                    }
                },
                {
                    '$group': {
                        '_id': '$step',
                        'total_jobs': {'$sum': 1},
                        'completed': {
                            '$sum': {
                                '$cond': [{'$eq': ['$status', 'completed']}, 1, 0]
                            }
                        },
                        'failed': {
                            '$sum': {
                                '$cond': [{'$eq': ['$status', 'failed']}, 1, 0]
                            }
                        },
                        'avg_execution_time': {'$avg': '$executionTimeSeconds'},
                        'avg_attempts': {'$avg': '$attempts'}
                    }
                },
                {
                    '$project': {
                        '_id': 1,
                        'total_jobs': 1,
                        'completed': 1,
                        'failed': 1,
                        'success_rate': {
                            '$divide': ['$completed', '$total_jobs']
                        },
                        'avg_execution_time': 1,
                        'avg_attempts': 1
                    }
                },
                {
                    '$sort': {'total_jobs': -1}
                }
            ]
            
            results = self.aggregate(pipeline)
            
            return [
                {
                    'step': result['_id'],
                    'total_jobs': result['total_jobs'],
                    'completed': result['completed'],
                    'failed': result['failed'],
                    'success_rate': result['success_rate'],
                    'avg_execution_time': result['avg_execution_time'] or 0,
                    'avg_attempts': result['avg_attempts'] or 0
                }
                for result in results
            ]
            
        except Exception as e:
            logger.error(f"Error getting step performance: {e}")
            return []
    
    def cleanup_old_jobs(self, days: int = 30, status_filter: List[str] = None) -> int:
        """Clean up old jobs (completed/failed only by default)."""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            filter_doc = {
                'completedAt': {'$lt': cutoff_date}
            }
            
            if status_filter:
                filter_doc['status'] = {'$in': status_filter}
            else:
                filter_doc['status'] = {'$in': ['completed', 'failed']}
            
            # Count jobs to be deleted
            count = self.count(filter_doc)
            
            if count > 0:
                # Delete old jobs
                result = self.collection.delete_many(filter_doc)
                deleted_count = result.deleted_count
                
                logger.info(f"Cleaned up {deleted_count} old jobs")
                return deleted_count
            
            return 0
            
        except Exception as e:
            logger.error(f"Error cleaning up old jobs: {e}")
            return 0


# Global repository instance
_job_repository = None


def get_job_repository() -> JobRepository:
    """Get global job repository instance."""
    global _job_repository
    if _job_repository is None:
        _job_repository = JobRepository()
    return _job_repository