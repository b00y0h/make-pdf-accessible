# Lambda image for the API. Build from services/ so the shared package is in the context:
#   docker build -f services/api/Dockerfile services
# Local development uses Dockerfile.dev instead (see docker-compose.yml).
FROM public.ecr.aws/lambda/python:3.13

# Install dependencies into the function directory, which the Lambda runtime imports from.
# Every dependency ships a prebuilt wheel for this image, so no compilers are needed.
COPY api/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt --target "${LAMBDA_TASK_ROOT}" \
    && rm /tmp/requirements.txt

# Copy application code
COPY api/app/ ${LAMBDA_TASK_ROOT}/app/
COPY api/main.py ${LAMBDA_TASK_ROOT}/

# Copy shared services code
COPY shared/ ${LAMBDA_TASK_ROOT}/services/shared/

CMD ["main.lambda_handler"]
