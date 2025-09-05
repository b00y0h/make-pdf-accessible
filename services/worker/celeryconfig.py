import os

broker_url = os.getenv("REDIS_URL", "redis://redis:6379")
result_backend = os.getenv("REDIS_URL", "redis://redis:6379")
task_serializer = "json"
accept_content = ["json"]
result_serializer = "json"
timezone = "UTC"
enable_utc = True
