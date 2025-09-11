# Timeout Monitor Service Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY services/shared/requirements.txt requirements-shared.txt
COPY services/timeout-monitor/requirements.txt requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements-shared.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY services/shared/ /app/services/shared/
COPY services/timeout-monitor/ /app/services/timeout-monitor/

# Set Python path
ENV PYTHONPATH=/app

# Run timeout monitor
CMD ["python", "services/shared/timeout_monitor.py", "--interval", "300"]