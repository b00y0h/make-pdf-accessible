"""
Celery configuration for API service
"""
from celery import Celery

# Create Celery app
celery_app = Celery(
    "pdf_accessibility",
    broker="redis://redis:6379/0",
    backend="redis://redis:6379/0",
)

# Configure Celery
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=300,  # 5 minutes
    task_soft_time_limit=240,  # 4 minutes
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
)

# Define task routes
celery_app.conf.task_routes = {
    "worker.process_pdf": {"queue": "celery"},
}
