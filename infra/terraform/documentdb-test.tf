# Test Lambda function for DocumentDB connectivity
resource "aws_lambda_function" "documentdb_test" {
  function_name = "${local.name_prefix}-documentdb-test"
  role          = aws_iam_role.lambda_execution.arn
  
  filename         = "documentdb_test.zip"
  source_code_hash = data.archive_file.documentdb_test.output_base64sha256
  
  handler = "lambda_function.lambda_handler"
  runtime = "python3.11"
  timeout = 60
  
  # Add layers for DocumentDB connectivity
  layers = [
    aws_lambda_layer_version.rds_ca_certs.arn,
    aws_lambda_layer_version.python_documentdb_utils.arn
  ]
  
  # VPC Configuration for DocumentDB access
  vpc_config {
    subnet_ids         = aws_subnet.private[*].id
    security_group_ids = [aws_security_group.lambda_sg.id]
  }
  
  environment {
    variables = {
      DOCUMENTDB_SECRET_NAME = aws_secretsmanager_secret.documentdb_credentials.name
      DOCUMENTDB_ENDPOINT = aws_docdb_cluster.main.endpoint
      DOCUMENTDB_PORT = tostring(aws_docdb_cluster.main.port)
      AWS_REGION = var.aws_region
    }
  }
  
  depends_on = [
    aws_iam_role_policy_attachment.lambda_basic,
    aws_iam_role_policy_attachment.lambda_vpc,
    aws_iam_role_policy.lambda_custom,
    data.archive_file.documentdb_test
  ]

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-documentdb-test"
    Purpose = "DocumentDB connectivity testing"
  })
}

# Create the test Lambda code
data "archive_file" "documentdb_test" {
  type        = "zip"
  output_path = "documentdb_test.zip"
  
  source {
    content = <<EOF
import json
from documentdb_utils import get_documentdb_client

def lambda_handler(event, context):
    """Test DocumentDB connectivity using utility layer"""
    try:
        # Get reusable client from utility layer
        client = get_documentdb_client()
        
        # Test connection
        admin_db = client.admin
        server_status = admin_db.command("serverStatus")
        
        # Test basic CRUD operations
        test_db = client.test_database
        test_collection = test_db.test_collection
        
        # Insert test document
        test_doc = {"test": "document", "timestamp": str(context.aws_request_id)}
        insert_result = test_collection.insert_one(test_doc)
        
        # Read test document
        found_doc = test_collection.find_one({"_id": insert_result.inserted_id})
        
        # Update test document
        update_result = test_collection.update_one(
            {"_id": insert_result.inserted_id},
            {"$set": {"updated": True}}
        )
        
        # Delete test document
        delete_result = test_collection.delete_one({"_id": insert_result.inserted_id})
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'DocumentDB connectivity test successful',
                'server_info': {
                    'version': server_status.get('version'),
                    'uptime': server_status.get('uptime')
                },
                'crud_test': {
                    'insert_success': insert_result.acknowledged,
                    'read_success': found_doc is not None,
                    'update_success': update_result.modified_count == 1,
                    'delete_success': delete_result.deleted_count == 1
                },
                'connection_reuse': True  # Using utility layer connection manager
            })
        }
        
    except Exception as e:
        print(f"DocumentDB test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            'statusCode': 500,
            'body': json.dumps({
                'message': 'DocumentDB connectivity test failed',
                'error': str(e)
            })
        }
EOF
    filename = "lambda_function.py"
  }
  
  source {
    content = "pymongo==4.6.0\nboto3>=1.26.137"
    filename = "requirements.txt"
  }
}

# CloudWatch Log Group for test Lambda
resource "aws_cloudwatch_log_group" "documentdb_test" {
  name              = "/aws/lambda/${local.name_prefix}-documentdb-test"
  retention_in_days = 7
  
  tags = local.common_tags
}