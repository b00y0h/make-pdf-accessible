#!/bin/bash
set -e

echo "🚀 Initializing LocalStack AWS resources for PDF Accessibility Service..."

# Wait for LocalStack to be ready
echo "⏳ Waiting for LocalStack to be ready..."
while ! curl -s http://localhost:4566/_localstack/health | grep -q '"s3": "available"'; do
  echo "Waiting for LocalStack S3..."
  sleep 2
done

echo "✅ LocalStack is ready!"

# Set AWS CLI configuration for LocalStack
export AWS_ACCESS_KEY_ID=test
export AWS_SECRET_ACCESS_KEY=test
export AWS_DEFAULT_REGION=us-east-1
export AWS_ENDPOINT_URL=http://localhost:4566

echo "📦 Creating S3 buckets..."

# Create S3 buckets
awslocal s3 mb s3://pdf-accessibility-uploads
awslocal s3 mb s3://pdf-accessibility-processed  
awslocal s3 mb s3://pdf-accessibility-reports
awslocal s3 mb s3://pdf-accessibility-dev-pdf-originals

# Enable public read access for processed files (for development)
awslocal s3api put-bucket-cors --bucket pdf-accessibility-processed --cors-configuration '{
  "CORSRules": [
    {
      "AllowedOrigins": ["*"],
      "AllowedMethods": ["GET", "HEAD"],
      "AllowedHeaders": ["*"],
      "MaxAgeSeconds": 3600
    }
  ]
}'

# Enable CORS for demo uploads bucket (for browser uploads)
awslocal s3api put-bucket-cors --bucket pdf-accessibility-dev-pdf-originals --cors-configuration '{
  "CORSRules": [
    {
      "AllowedOrigins": ["http://localhost:3000", "https://localhost:3000"],
      "AllowedMethods": ["GET", "PUT", "POST", "DELETE", "HEAD"],
      "AllowedHeaders": ["*"],
      "ExposeHeaders": ["ETag", "x-amz-meta-custom-header"],
      "MaxAgeSeconds": 3000
    }
  ]
}'

# Set up bucket lifecycle policies for cleanup (optional)
awslocal s3api put-bucket-lifecycle-configuration --bucket pdf-accessibility-uploads --lifecycle-configuration '{
  "Rules": [
    {
      "ID": "DeleteUploadsAfter7Days",
      "Status": "Enabled",
      "Filter": {"Prefix": "uploads/"},
      "Expiration": {"Days": 7}
    }
  ]
}'

echo "📨 Creating SQS queues..."

# Create SQS queues
awslocal sqs create-queue --queue-name pdf-accessibility-ingest
awslocal sqs create-queue --queue-name pdf-accessibility-priority  
awslocal sqs create-queue --queue-name pdf-accessibility-callbacks

# Create dead letter queues
awslocal sqs create-queue --queue-name pdf-accessibility-ingest-dlq
awslocal sqs create-queue --queue-name pdf-accessibility-priority-dlq
awslocal sqs create-queue --queue-name pdf-accessibility-callbacks-dlq

# Set up DLQ redrive policies
INGEST_QUEUE_URL=$(awslocal sqs get-queue-url --queue-name pdf-accessibility-ingest --query 'QueueUrl' --output text)
INGEST_DLQ_URL=$(awslocal sqs get-queue-url --queue-name pdf-accessibility-ingest-dlq --query 'QueueUrl' --output text)

awslocal sqs set-queue-attributes --queue-url "$INGEST_QUEUE_URL" --attributes '{
  "RedrivePolicy": "{\"deadLetterTargetArn\":\"arn:aws:sqs:us-east-1:000000000000:pdf-accessibility-ingest-dlq\",\"maxReceiveCount\":3}",
  "VisibilityTimeoutSeconds": "300",
  "MessageRetentionPeriod": "1209600"
}'

echo "🔔 Creating SNS topics..."

# Create SNS topics for notifications
awslocal sns create-topic --name pdf-accessibility-notifications
awslocal sns create-topic --name pdf-accessibility-webhooks

# Get topic ARNs
NOTIFICATIONS_TOPIC_ARN=$(awslocal sns list-topics --query 'Topics[?contains(TopicArn, `pdf-accessibility-notifications`)].TopicArn' --output text)
WEBHOOKS_TOPIC_ARN=$(awslocal sns list-topics --query 'Topics[?contains(TopicArn, `pdf-accessibility-webhooks`)].TopicArn' --output text)

echo "🔐 Creating Secrets Manager secrets..."

# Create secrets for API keys and configurations
awslocal secretsmanager create-secret \
  --name pdf-accessibility/api-keys \
  --description "API keys for PDF accessibility service" \
  --secret-string '{
    "openai_api_key": "sk-test-key-for-development",
    "webhook_secret": "dev-webhook-secret-123",
    "jwt_secret": "dev-jwt-secret-456"
  }'

awslocal secretsmanager create-secret \
  --name pdf-accessibility/database \
  --description "Database connection strings" \
  --secret-string '{
    "mongodb_uri": "mongodb://mongo:27017/pdf_accessibility?replicaSet=rs0",
    "redis_url": "redis://redis:6379"
  }'

echo "⚙️  Creating Step Functions state machine..."

# Create a simple Step Functions state machine for document processing
awslocal stepfunctions create-state-machine \
  --name pdf-accessibility-processing \
  --definition '{
    "Comment": "PDF Accessibility Processing Pipeline",
    "StartAt": "Route",
    "States": {
      "Route": {
        "Type": "Task",
        "Resource": "arn:aws:lambda:us-east-1:000000000000:function:pdf-accessibility-router",
        "Next": "Structure"
      },
      "Structure": {
        "Type": "Task", 
        "Resource": "arn:aws:lambda:us-east-1:000000000000:function:pdf-accessibility-structure",
        "Next": "OCR"
      },
      "OCR": {
        "Type": "Task",
        "Resource": "arn:aws:lambda:us-east-1:000000000000:function:pdf-accessibility-ocr", 
        "Next": "Tag"
      },
      "Tag": {
        "Type": "Task",
        "Resource": "arn:aws:lambda:us-east-1:000000000000:function:pdf-accessibility-tagger",
        "Next": "Validate"
      },
      "Validate": {
        "Type": "Task",
        "Resource": "arn:aws:lambda:us-east-1:000000000000:function:pdf-accessibility-validator",
        "Next": "Export"
      },
      "Export": {
        "Type": "Task",
        "Resource": "arn:aws:lambda:us-east-1:000000000000:function:pdf-accessibility-exporter",
        "Next": "Notify"
      },
      "Notify": {
        "Type": "Task",
        "Resource": "arn:aws:lambda:us-east-1:000000000000:function:pdf-accessibility-notifier",
        "End": true
      }
    }
  }' \
  --role-arn arn:aws:iam::000000000000:role/StepFunctionsRole

echo "🧪 Creating test data in S3..."

# Create some test files
echo "This is a test PDF content" | awslocal s3 cp - s3://pdf-accessibility-uploads/test/sample-document.pdf
echo '{"test": "report", "issues": []}' | awslocal s3 cp - s3://pdf-accessibility-reports/test/sample-report.json

echo "📊 Displaying created resources..."

echo "S3 Buckets:"
awslocal s3 ls

echo -e "\nSQS Queues:" 
awslocal sqs list-queues --query 'QueueUrls' --output table

echo -e "\nSNS Topics:"
awslocal sns list-topics --query 'Topics[].TopicArn' --output table

echo -e "\nSecrets:"
awslocal secretsmanager list-secrets --query 'SecretList[].Name' --output table

echo -e "\nStep Functions:"
awslocal stepfunctions list-state-machines --query 'stateMachines[].name' --output table

echo "✅ LocalStack AWS resources initialized successfully!"
echo ""
echo "🎯 Access URLs:"
echo "  - LocalStack Dashboard: http://localhost:4566"
echo "  - S3 Console: http://localhost:4566/_localstack/s3"
echo ""
echo "🔧 Environment variables for applications:"
echo "  AWS_ENDPOINT_URL=http://localhost:4566"
echo "  AWS_DEFAULT_REGION=us-east-1"
echo "  AWS_ACCESS_KEY_ID=test"
echo "  AWS_SECRET_ACCESS_KEY=test"