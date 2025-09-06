FROM public.ecr.aws/lambda/python:3.11

# Copy requirements and install Python dependencies
COPY requirements.txt ${LAMBDA_TASK_ROOT}
RUN pip install --no-cache-dir -r requirements.txt

# Copy function code
COPY models.py ${LAMBDA_TASK_ROOT}/
COPY services.py ${LAMBDA_TASK_ROOT}/
COPY main.py ${LAMBDA_TASK_ROOT}/

# Set the CMD to the handler
CMD ["main.lambda_handler"]