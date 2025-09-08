# Lambda Layer for AWS RDS CA certificates
resource "aws_lambda_layer_version" "rds_ca_certs" {
  layer_name          = "${local.name_prefix}-rds-ca-certs"
  description         = "AWS RDS CA certificates for DocumentDB TLS connections"
  
  filename         = "rds-ca-certs-layer.zip"
  source_code_hash = data.archive_file.rds_ca_certs_layer.output_base64sha256
  
  compatible_runtimes = ["python3.9", "python3.10", "python3.11", "python3.12"]

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-rds-ca-certs-layer"
  })
}

# Create RDS CA certificates layer
data "archive_file" "rds_ca_certs_layer" {
  type        = "zip"
  output_path = "rds-ca-certs-layer.zip"
  
  source {
    # AWS RDS CA certificate (2019 root)
    content = <<EOF
-----BEGIN CERTIFICATE-----
MIIEBjCCAu6gAwIBAgIJAMc0ZzaSUK51MA0GCSqGSIb3DQEBBQUAMIGYMQswCQYD
VQQGEwJVUzEQMA4GA1UECAwHQXJpem9uYTETMBEGA1UEBwwKU2NvdHRzZGFsZTEm
MCQGA1UECgwdU3RhcmZpZWxkIFRlY2hub2xvZ2llcywgSW5jLjE6MDgGA1UEAwwx
U3RhcmZpZWxkIFNlcnZpY2VzIFJvb3QgQ2VydGlmaWNhdGUgQXV0aG9yaXR5IC0g
RzIwHhcNMDkwOTAxMDAwMDAwWhcNMzczMTMxMjM1OTU5WjCBmDELMAkGA1UEBhMC
VVMxEDAOBgNVBAgMB0FyaXpvbmExEzARBgNVBAcMClNjb3R0c2RhbGUxJjAkBgNV
BAoMHVN0YXJmaWVsZCBUZWNobm9sb2dpZXMsIEluYy4xOjA4BgNVBAMMMVN0YXJm
aWVsZCBTZXJ2aWNlcyBSb290IENlcnRpZmljYXRlIEF1dGhvcml0eSAtIEcyMIIB
IjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA2ce1x1tJJlvUJmUGf7sGpD7p
+VBTDaI3fOASLmI5F2N+4O+Z7RNhPlx3MXgXhpGYw6d9ZiX2i5VKLs1LdqJDBJ1I
2t0AxmjCTCXuTXUvYoV01Fh6B4F8cxfJr7J8uxYgRCKmnX39PFGQ2RG9qw0YtDnj
QVaEF4+JxKnnJMo8M7cjV17UqVB+8qKrvQjPeB1wT0SBH4i5UpbvCJSFl7R2Sxru
rUcAW30q4nE4bLVZ+l8Qr4pGQ1s4tFqF1f39wUKvpJKx/BYxJR4w9kqJIgZHgJ8L
l4fC3JX9JBl8k5jFQhxPHIiW9xU8yHNy3aVr0XOGcSTlg0pFnR2r4wgfzJrJQwID
AQABo0IwQDAPBgNVHRMBAf8EBTADAQH/MA4GA1UdDwEB/wQEAwIBBjAdBgNVHQ4E
FgQUjvQifi75a5ZyTguF3K+7qxPvqFMwDQYJKoZIhvcNAQEFBQADggEBAKf9xkly
nh8GDEhXTNn0C7T8VJ8yzuaWwPb+7oONJ8DP8MFwSKGR2UJJPi5P1xJa0XdjKSBa
WLRvBOJQSKRiVhyZBm7R2kT9ZhTNRAi2FnqP1L7QOhZl/jY7dJkP7aXb7A8eExU4
I/aXW7YbMkdOhPdgUNlV7nZjMCbF+x7j5L6nPkLKM5Zh0mjNgC5S3vQdpGnYZJJL
2VF3z7Q0bH1pTFk9x1YrHqKSdq4cW8bKw8P2Vd8PVJHhEQeHmLrq8a4BFy7oFHYo
3L3lHQjGQJyW3J7UWtGg2ZLOxQJb8TrF1xRWXjy5Rl7oINYw3WvN2x0LrGT7oJOl
qFW7g1V2+3V7l2Q=
-----END CERTIFICATE-----
EOF
    filename = "opt/rds-ca-2019-root.pem"
  }
}

# Python connection utility layer
resource "aws_lambda_layer_version" "python_documentdb_utils" {
  layer_name          = "${local.name_prefix}-documentdb-utils"
  description         = "Python utilities for DocumentDB connections with connection reuse"
  
  filename         = "documentdb-utils-layer.zip"
  source_code_hash = data.archive_file.documentdb_utils_layer.output_base64sha256
  
  compatible_runtimes = ["python3.9", "python3.10", "python3.11", "python3.12"]

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-documentdb-utils-layer"
  })
}

# Create DocumentDB utilities layer
data "archive_file" "documentdb_utils_layer" {
  type        = "zip"
  output_path = "documentdb-utils-layer.zip"
  
  source {
    content = <<EOF
import json
import boto3
import pymongo
import ssl
import os
from typing import Optional
from botocore.exceptions import ClientError

class DocumentDBConnection:
    """Singleton DocumentDB connection manager with connection reuse"""
    
    _instance: Optional['DocumentDBConnection'] = None
    _client: Optional[pymongo.MongoClient] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, '_initialized'):
            self._credentials = None
            self._initialized = True
    
    def get_credentials(self) -> dict:
        """Get DocumentDB credentials from Secrets Manager (cached)"""
        if self._credentials is None:
            secret_name = os.environ.get('DOCUMENTDB_SECRET_NAME')
            if not secret_name:
                raise ValueError("DOCUMENTDB_SECRET_NAME environment variable not set")
            
            region = os.environ.get('AWS_REGION', 'us-east-1')
            
            session = boto3.session.Session()
            client = session.client('secretsmanager', region_name=region)
            
            try:
                response = client.get_secret_value(SecretId=secret_name)
                self._credentials = json.loads(response['SecretString'])
            except ClientError as e:
                print(f"Error retrieving DocumentDB credentials: {e}")
                raise e
        
        return self._credentials
    
    def get_client(self) -> pymongo.MongoClient:
        """Get or create DocumentDB client with connection reuse"""
        if self._client is None:
            creds = self.get_credentials()
            
            # DocumentDB connection string with TLS
            connection_string = (
                f"mongodb://{creds['username']}:{creds['password']}"
                f"@{creds['endpoint']}:{creds['port']}"
                f"/?ssl=true&replicaSet=rs0&readPreference=secondaryPreferred&retryWrites=false"
            )
            
            # Create client with proper TLS configuration
            self._client = pymongo.MongoClient(
                connection_string,
                ssl=True,
                ssl_cert_reqs=ssl.CERT_REQUIRED,
                ssl_ca_certs='/opt/rds-ca-2019-root.pem',
                serverSelectionTimeoutMS=5000,
                maxPoolSize=50,  # Connection pooling for reuse
                minPoolSize=5,
                maxIdleTimeMS=30000,
                retryWrites=False,
                connectTimeoutMS=10000,
                socketTimeoutMS=20000
            )
            
            # Test connection
            self._client.admin.command('ping')
            print("DocumentDB connection established successfully")
        
        return self._client
    
    def close(self):
        """Close the DocumentDB connection"""
        if self._client:
            self._client.close()
            self._client = None

# Global connection instance
_db_connection = DocumentDBConnection()

def get_documentdb_client() -> pymongo.MongoClient:
    """Get DocumentDB client with connection reuse"""
    return _db_connection.get_client()

def close_documentdb_connection():
    """Close DocumentDB connection (call in Lambda cleanup if needed)"""
    _db_connection.close()
EOF
    filename = "python/documentdb_utils.py"
  }
  
  source {
    content = ""
    filename = "python/__init__.py"
  }
}

# Output the layer ARNs for use in Lambda functions
output "rds_ca_certs_layer_arn" {
  description = "ARN of the RDS CA certificates Lambda layer"
  value       = aws_lambda_layer_version.rds_ca_certs.arn
}

output "documentdb_utils_layer_arn" {
  description = "ARN of the DocumentDB utilities Lambda layer"
  value       = aws_lambda_layer_version.python_documentdb_utils.arn
}