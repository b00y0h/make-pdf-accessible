# KMS Key for SQS Encryption
resource "aws_kms_key" "sqs" {
  description             = "KMS key for SQS encryption"
  deletion_window_in_days = 7
  enable_key_rotation     = true

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-sqs-kms-key"
  })
}

resource "aws_kms_alias" "sqs" {
  name          = "alias/${local.name_prefix}-sqs"
  target_key_id = aws_kms_key.sqs.key_id
}

# Dead Letter Queues
resource "aws_sqs_queue" "ingest_dlq" {
  name                              = "${local.name_prefix}-ingest-dlq"
  message_retention_seconds         = 1209600 # 14 days
  kms_master_key_id                 = aws_kms_key.sqs.arn
  kms_data_key_reuse_period_seconds = 300

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-ingest-dlq"
    Type = "dead-letter-queue"
  })
}

resource "aws_sqs_queue" "process_dlq" {
  name                              = "${local.name_prefix}-process-dlq"
  message_retention_seconds         = 1209600 # 14 days
  kms_master_key_id                 = aws_kms_key.sqs.arn
  kms_data_key_reuse_period_seconds = 300

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-process-dlq"
    Type = "dead-letter-queue"
  })
}

resource "aws_sqs_queue" "callback_dlq" {
  name                              = "${local.name_prefix}-callback-dlq"
  message_retention_seconds         = 1209600 # 14 days
  kms_master_key_id                 = aws_kms_key.sqs.arn
  kms_data_key_reuse_period_seconds = 300

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-callback-dlq"
    Type = "dead-letter-queue"
  })
}

# Main Queues
resource "aws_sqs_queue" "ingest_queue" {
  name                       = "${local.name_prefix}-ingest-queue"
  delay_seconds              = 0
  max_message_size           = 262144
  message_retention_seconds  = 345600 # 4 days
  receive_wait_time_seconds  = 20     # Long polling
  visibility_timeout_seconds = 900    # 15 minutes

  kms_master_key_id                 = aws_kms_key.sqs.arn
  kms_data_key_reuse_period_seconds = 300

  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.ingest_dlq.arn
    maxReceiveCount     = 3
  })

  tags = merge(local.common_tags, {
    Name    = "${local.name_prefix}-ingest-queue"
    Purpose = "Queue for PDF ingestion requests"
  })
}

resource "aws_sqs_queue" "process_queue" {
  name                       = "${local.name_prefix}-process-queue"
  delay_seconds              = 0
  max_message_size           = 262144
  message_retention_seconds  = 345600 # 4 days
  receive_wait_time_seconds  = 20     # Long polling
  visibility_timeout_seconds = 1800   # 30 minutes (longer for processing)

  kms_master_key_id                 = aws_kms_key.sqs.arn
  kms_data_key_reuse_period_seconds = 300

  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.process_dlq.arn
    maxReceiveCount     = 2
  })

  tags = merge(local.common_tags, {
    Name    = "${local.name_prefix}-process-queue"
    Purpose = "Queue for PDF processing jobs"
  })
}

resource "aws_sqs_queue" "callback_queue" {
  name                       = "${local.name_prefix}-callback-queue"
  delay_seconds              = 0
  max_message_size           = 262144
  message_retention_seconds  = 345600 # 4 days
  receive_wait_time_seconds  = 20     # Long polling
  visibility_timeout_seconds = 300    # 5 minutes

  kms_master_key_id                 = aws_kms_key.sqs.arn
  kms_data_key_reuse_period_seconds = 300

  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.callback_dlq.arn
    maxReceiveCount     = 3
  })

  tags = merge(local.common_tags, {
    Name    = "${local.name_prefix}-callback-queue"
    Purpose = "Queue for processing completion callbacks"
  })
}

# FIFO Queue for order-sensitive operations (optional)
resource "aws_sqs_queue" "priority_process_queue" {
  name                        = "${local.name_prefix}-priority-process-queue.fifo"
  fifo_queue                  = true
  content_based_deduplication = true
  delay_seconds               = 0
  max_message_size            = 262144
  message_retention_seconds   = 345600
  receive_wait_time_seconds   = 20
  visibility_timeout_seconds  = 1800

  kms_master_key_id                 = aws_kms_key.sqs.arn
  kms_data_key_reuse_period_seconds = 300

  tags = merge(local.common_tags, {
    Name    = "${local.name_prefix}-priority-process-queue"
    Purpose = "FIFO queue for priority processing jobs"
    Type    = "fifo"
  })
}

# CloudWatch Alarms for SQS
resource "aws_cloudwatch_metric_alarm" "ingest_queue_dlq_messages" {
  alarm_name          = "${local.name_prefix}-ingest-queue-dlq-messages"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "1"
  metric_name         = "ApproximateNumberOfVisibleMessages"
  namespace           = "AWS/SQS"
  period              = "300"
  statistic           = "Average"
  threshold           = "0"
  alarm_description   = "This metric monitors messages in ingest DLQ"
  alarm_actions       = []

  dimensions = {
    QueueName = aws_sqs_queue.ingest_dlq.name
  }

  tags = local.common_tags
}

resource "aws_cloudwatch_metric_alarm" "process_queue_dlq_messages" {
  alarm_name          = "${local.name_prefix}-process-queue-dlq-messages"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "1"
  metric_name         = "ApproximateNumberOfVisibleMessages"
  namespace           = "AWS/SQS"
  period              = "300"
  statistic           = "Average"
  threshold           = "0"
  alarm_description   = "This metric monitors messages in process DLQ"
  alarm_actions       = []

  dimensions = {
    QueueName = aws_sqs_queue.process_dlq.name
  }

  tags = local.common_tags
}

resource "aws_cloudwatch_metric_alarm" "callback_queue_dlq_messages" {
  alarm_name          = "${local.name_prefix}-callback-queue-dlq-messages"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "1"
  metric_name         = "ApproximateNumberOfVisibleMessages"
  namespace           = "AWS/SQS"
  period              = "300"
  statistic           = "Average"
  threshold           = "0"
  alarm_description   = "This metric monitors messages in callback DLQ"
  alarm_actions       = []

  dimensions = {
    QueueName = aws_sqs_queue.callback_dlq.name
  }

  tags = local.common_tags
}

resource "aws_cloudwatch_metric_alarm" "ingest_queue_age" {
  alarm_name          = "${local.name_prefix}-ingest-queue-message-age"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "ApproximateAgeOfOldestMessage"
  namespace           = "AWS/SQS"
  period              = "300"
  statistic           = "Average"
  threshold           = "1800" # 30 minutes
  alarm_description   = "This metric monitors age of oldest message in ingest queue"
  alarm_actions       = []

  dimensions = {
    QueueName = aws_sqs_queue.ingest_queue.name
  }

  tags = local.common_tags
}

resource "aws_cloudwatch_metric_alarm" "process_queue_age" {
  alarm_name          = "${local.name_prefix}-process-queue-message-age"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "ApproximateAgeOfOldestMessage"
  namespace           = "AWS/SQS"
  period              = "300"
  statistic           = "Average"
  threshold           = "3600" # 1 hour
  alarm_description   = "This metric monitors age of oldest message in process queue"
  alarm_actions       = []

  dimensions = {
    QueueName = aws_sqs_queue.process_queue.name
  }

  tags = local.common_tags
}