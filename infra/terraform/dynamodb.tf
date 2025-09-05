# KMS Key for DynamoDB Encryption
resource "aws_kms_key" "dynamodb" {
  description             = "KMS key for DynamoDB encryption"
  deletion_window_in_days = 7
  enable_key_rotation     = true

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-dynamodb-kms-key"
  })
}

resource "aws_kms_alias" "dynamodb" {
  name          = "alias/${local.name_prefix}-dynamodb"
  target_key_id = aws_kms_key.dynamodb.key_id
}

# DynamoDB Table: Documents
resource "aws_dynamodb_table" "documents" {
  name         = "${local.name_prefix}-documents"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "docId"

  attribute {
    name = "docId"
    type = "S"
  }

  attribute {
    name = "status"
    type = "S"
  }

  attribute {
    name = "createdAt"
    type = "S"
  }

  attribute {
    name = "userId"
    type = "S"
  }

  # GSI: Query documents by status
  global_secondary_index {
    name            = "byStatus"
    hash_key        = "status"
    range_key       = "createdAt"
    projection_type = "ALL"
  }

  # GSI: Query documents by user
  global_secondary_index {
    name            = "byUserId"
    hash_key        = "userId"
    range_key       = "createdAt"
    projection_type = "ALL"
  }

  server_side_encryption {
    enabled = true
  }

  point_in_time_recovery {
    enabled = true
  }

  tags = merge(local.common_tags, {
    Name      = "${local.name_prefix}-documents-table"
    Purpose   = "Store document metadata and processing status"
    DataClass = "primary"
  })
}

# DynamoDB Table: Jobs
resource "aws_dynamodb_table" "jobs" {
  name         = "${local.name_prefix}-jobs"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "jobId"

  attribute {
    name = "jobId"
    type = "S"
  }

  attribute {
    name = "docId"
    type = "S"
  }

  attribute {
    name = "status"
    type = "S"
  }

  attribute {
    name = "createdAt"
    type = "S"
  }

  # TTL attribute
  ttl {
    attribute_name = "expiresAt"
    enabled        = true
  }

  # GSI: Query jobs by document ID
  global_secondary_index {
    name            = "byDocId"
    hash_key        = "docId"
    range_key       = "createdAt"
    projection_type = "ALL"
  }

  # GSI: Query jobs by status
  global_secondary_index {
    name            = "byStatus"
    hash_key        = "status"
    range_key       = "createdAt"
    projection_type = "ALL"
  }

  server_side_encryption {
    enabled = true
  }

  point_in_time_recovery {
    enabled = true
  }

  tags = merge(local.common_tags, {
    Name      = "${local.name_prefix}-jobs-table"
    Purpose   = "Store job processing information"
    DataClass = "transient"
  })
}

# DynamoDB Table: User Sessions (optional)
resource "aws_dynamodb_table" "user_sessions" {
  name         = "${local.name_prefix}-user-sessions"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "sessionId"

  attribute {
    name = "sessionId"
    type = "S"
  }

  attribute {
    name = "userId"
    type = "S"
  }

  # TTL for automatic session cleanup
  ttl {
    attribute_name = "expiresAt"
    enabled        = true
  }

  # GSI: Query sessions by user ID
  global_secondary_index {
    name            = "byUserId"
    hash_key        = "userId"
    projection_type = "ALL"
  }

  server_side_encryption {
    enabled = true
  }

  tags = merge(local.common_tags, {
    Name      = "${local.name_prefix}-sessions-table"
    Purpose   = "Store user session data"
    DataClass = "session"
  })
}

# CloudWatch Alarms for DynamoDB
resource "aws_cloudwatch_metric_alarm" "documents_throttled_requests" {
  alarm_name          = "${local.name_prefix}-documents-throttled-requests"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "ThrottledRequests"
  namespace           = "AWS/DynamoDB"
  period              = "300"
  statistic           = "Sum"
  threshold           = "0"
  alarm_description   = "This metric monitors DynamoDB throttled requests for documents table"
  alarm_actions       = []

  dimensions = {
    TableName = aws_dynamodb_table.documents.name
  }

  tags = local.common_tags
}

resource "aws_cloudwatch_metric_alarm" "jobs_throttled_requests" {
  alarm_name          = "${local.name_prefix}-jobs-throttled-requests"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "ThrottledRequests"
  namespace           = "AWS/DynamoDB"
  period              = "300"
  statistic           = "Sum"
  threshold           = "0"
  alarm_description   = "This metric monitors DynamoDB throttled requests for jobs table"
  alarm_actions       = []

  dimensions = {
    TableName = aws_dynamodb_table.jobs.name
  }

  tags = local.common_tags
}