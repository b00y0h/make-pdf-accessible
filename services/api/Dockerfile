FROM public.ecr.aws/lambda/python:3.11

# Copy requirements and install Python dependencies
COPY requirements.txt ${LAMBDA_TASK_ROOT}
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ ${LAMBDA_TASK_ROOT}/app/
COPY main.py ${LAMBDA_TASK_ROOT}/

# Set the CMD to your handler (could also be done as a parameter override outside of the Dockerfile)
CMD ["main.lambda_handler"]
