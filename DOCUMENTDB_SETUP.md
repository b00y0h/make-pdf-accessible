# DocumentDB Setup for Lambda VPC Connectivity

## Overview

This document describes the DocumentDB infrastructure setup that ensures secure connectivity between Lambda functions in VPC and DocumentDB with proper TLS encryption and connection reuse.

## Infrastructure Components

### 1. VPC Configuration

- **Private Subnets**: Lambda functions are deployed in private subnets (`aws_subnet.private[*].id`)
- **NAT Gateway**: Provides egress access for Lambda functions to reach AWS services
- **Route Tables**: Private route tables configured with NAT Gateway for outbound traffic

### 2. DocumentDB Cluster (`documentdb.tf`)

- **Engine**: DocumentDB 5.0 with TLS enabled
- **Subnet Group**: Uses private subnets for secure placement
- **Parameter Group**: TLS and TTL monitoring enabled
- **Encryption**: Storage encrypted at rest
- **Backup**: 7-day retention with point-in-time recovery
- **Monitoring**: CloudWatch logs for audit and profiler

### 3. Security Groups

- **DocumentDB Security Group**:
  - Allows inbound port 27017 from Lambda security groups
  - Restricts access to MongoDB protocol only
- **Lambda Security Group**:
  - Allows outbound HTTPS (443) for AWS services
  - Allows outbound port 27017 to DocumentDB security group
  - Allows outbound HTTP (80) for general internet access

### 4. Secrets Management

- **AWS Secrets Manager**: Stores DocumentDB credentials securely
- **IAM Permissions**: Lambda roles have `secretsmanager:GetSecretValue` access
- **Credential Rotation**: Configured for production environments

### 5. Lambda Layers for TLS and Connection Reuse

#### RDS CA Certificates Layer (`lambda-layers.tf`)

- Contains AWS RDS CA certificate for TLS validation
- Path: `/opt/rds-ca-2019-root.pem`
- Compatible with Python 3.9-3.12

#### DocumentDB Utilities Layer

- Singleton connection manager for connection reuse
- Handles credential retrieval from Secrets Manager
- Implements proper connection pooling and TLS configuration
- Minimizes cold start overhead through global connection caching

### 6. Environment Variables

All Lambda functions include:

```
DOCUMENTDB_SECRET_NAME = <secrets-manager-secret-name>
DOCUMENTDB_ENDPOINT = <cluster-endpoint>
DOCUMENTDB_PORT = 27017
```

### 7. IAM Permissions

Lambda execution roles include:

- VPC access permissions (`AWSLambdaVPCAccessExecutionRole`)
- Secrets Manager read access for DocumentDB credentials
- KMS decrypt permissions for encrypted secrets

## Connection Pattern

### Python Connection Code Example

```python
from documentdb_utils import get_documentdb_client

def lambda_handler(event, context):
    # Get reusable client (connection pooling)
    client = get_documentdb_client()

    # Use the client
    db = client.your_database
    collection = db.your_collection

    # Perform operations...
    result = collection.find_one({"_id": document_id})
    return result
```

### TLS Configuration

- **SSL Mode**: Required with certificate validation
- **CA Certificate**: `/opt/rds-ca-2019-root.pem` from Lambda layer
- **Connection String**: Includes `ssl=true&replicaSet=rs0&readPreference=secondaryPreferred`
- **Retry Writes**: Disabled (DocumentDB requirement)

### Connection Reuse Features

- **Singleton Pattern**: One connection instance per Lambda container
- **Connection Pooling**: maxPoolSize=50, minPoolSize=5
- **Timeout Configuration**: Optimized for Lambda environment
- **Credential Caching**: Secrets Manager calls minimized

## Testing

### Smoke Test Lambda (`documentdb-test.tf`)

A test Lambda function is included that:

- Tests basic DocumentDB connectivity
- Performs CRUD operations
- Validates TLS connection
- Demonstrates connection reuse
- Reports server status and performance metrics

### Running Tests

```bash
# Deploy infrastructure
terraform apply

# Invoke test function
aws lambda invoke --function-name <prefix>-documentdb-test response.json
```

## Security Features

1. **Network Isolation**: DocumentDB in private subnets only
2. **TLS Encryption**: All connections use TLS 1.2+
3. **Certificate Validation**: AWS CA bundle validates server certificates
4. **Credential Security**: Secrets stored in AWS Secrets Manager
5. **Least Privilege**: IAM roles with minimal required permissions
6. **Audit Logging**: CloudWatch logs for connection monitoring

## Performance Optimizations

1. **Connection Reuse**: Global connection instance per Lambda container
2. **Connection Pooling**: Multiple connections per client
3. **Timeout Tuning**: Optimized for Lambda execution environment
4. **Credential Caching**: Reduces Secrets Manager API calls
5. **Regional Placement**: All resources in same region/AZs

## Monitoring and Troubleshooting

### CloudWatch Logs

- DocumentDB audit logs: `/aws/docdb/<cluster>/audit`
- DocumentDB profiler logs: `/aws/docdb/<cluster>/profiler`
- Lambda logs: `/aws/lambda/<function-name>`

### Key Metrics to Monitor

- Connection establishment time
- Query execution time
- Failed connection attempts
- TLS handshake errors
- Memory usage for connection pools

### Common Issues

1. **Connection Timeouts**: Check security group rules and NAT Gateway
2. **TLS Errors**: Verify CA certificate in Lambda layer
3. **Authentication Failures**: Check Secrets Manager permissions
4. **High Latency**: Optimize connection pooling settings

## Deployment Commands

```bash
# Navigate to terraform directory
cd infra/terraform

# Initialize and apply
terraform init
terraform plan
terraform apply

# Test connectivity
aws lambda invoke \
  --function-name $(terraform output -raw api_lambda_function_name)-documentdb-test \
  --payload '{}' \
  response.json && cat response.json
```

This setup ensures production-ready, secure, and performant DocumentDB connectivity from Lambda functions with proper VPC isolation, TLS encryption, and connection reuse patterns.
