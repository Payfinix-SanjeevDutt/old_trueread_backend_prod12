# Start from the AWS Base Image for Python (correct tag)
FROM public.ecr.aws/lambda/python:3.11

# Install dependencies (ensure serverless-wsgi is in requirements.txt)
COPY lamdareq.txt .
RUN pip install --no-cache-dir -r lamdareq.txt

# Copy your entire Django project into the Lambda task root (/var/task)
COPY . ${LAMBDA_TASK_ROOT}

# CRITICAL: Use the handler file as the entry point for the Lambda Runtime Interface Client
CMD ["lambda_handler.handler"]