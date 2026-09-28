FROM public.ecr.aws/lambda/python:3.13

# Copy requirements first for better caching
COPY requirements.txt ${LAMBDA_TASK_ROOT}

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy function code
COPY models.py services.py main.py ${LAMBDA_TASK_ROOT}/

# Set the CMD to your handler
CMD ["main.lambda_handler"]
