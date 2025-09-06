FROM public.ecr.aws/lambda/python:3.11

# Install system dependencies for PDF processing
RUN yum update -y && \
    yum install -y \
    gcc \
    gcc-c++ \
    make \
    && yum clean all

# Copy requirements first for better caching
COPY requirements.txt ${LAMBDA_TASK_ROOT}

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy function code
COPY models.py services.py main.py ${LAMBDA_TASK_ROOT}/

# Set the CMD to your handler
CMD ["main.lambda_handler"]
