# Multi-stage build to handle C++20 compilation requirements
FROM python:3.11-slim AS builder

# Install build dependencies for pikepdf with C++20 support
RUN apt-get update && apt-get install -y \
    g++ \
    gcc \
    make \
    cmake \
    && rm -rf /var/lib/apt/lists/*

# Create a virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy and install Python dependencies
COPY api/requirements.txt /tmp/
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# Final stage
FROM public.ecr.aws/lambda/python:3.11

# Copy the virtual environment from builder
COPY --from=builder /opt/venv /opt/venv

# Make sure we use the virtualenv
ENV PATH="/opt/venv/bin:$PATH"

# Copy application code
COPY api/app/ ${LAMBDA_TASK_ROOT}/app/
COPY api/main.py ${LAMBDA_TASK_ROOT}/

# Copy shared services code
COPY shared/ ${LAMBDA_TASK_ROOT}/services/shared/

# For local development, we override the entrypoint in docker-compose.yml
# For Lambda deployment, use the handler
CMD ["main.lambda_handler"]

# Override Lambda entrypoint for local development
ENTRYPOINT []
