# Comprehensive CloudWatch Monitoring and Alarms

# CloudWatch Log Groups for comprehensive logging
resource "aws_cloudwatch_log_group" "api_logs" {
  name              = "/aws/lambda/${local.app_name}-${var.environment}-api"
  retention_in_days = var.log_retention_days
  kms_key_id       = var.cloudwatch_logs_kms_key_id

  tags = local.common_tags
}

resource "aws_cloudwatch_log_group" "worker_logs" {
  name              = "/aws/ecs/${local.app_name}-${var.environment}-worker"
  retention_in_days = var.log_retention_days
  kms_key_id       = var.cloudwatch_logs_kms_key_id

  tags = local.common_tags
}

# Custom CloudWatch Dashboard
resource "aws_cloudwatch_dashboard" "pdf_processing_dashboard" {
  dashboard_name = "${local.app_name}-${var.environment}-processing-dashboard"

  dashboard_body = jsonencode({
    widgets = [
      {
        type   = "metric"
        x      = 0
        y      = 0
        width  = 12
        height = 6

        properties = {
          metrics = [
            ["PDF-Accessibility", "DocumentsProcessed", "Service", "pdf-api"],
            [".", "ProcessingErrors", ".", "."],
            [".", "ProcessingTime", ".", "."],
          ]
          view    = "timeSeries"
          stacked = false
          region  = data.aws_region.current.name
          title   = "Processing Metrics"
          period  = 300
        }
      },
      {
        type   = "metric"
        x      = 0
        y      = 6
        width  = 6
        height = 6

        properties = {
          metrics = [
            ["PDF-Accessibility", "LambdaInvocations", "Service", "pdf-ocr"],
            [".", ".", ".", "pdf-structure"],
            [".", ".", ".", "pdf-alt-text"],
            [".", ".", ".", "pdf-tagger"],
            [".", ".", ".", "pdf-validator"],
          ]
          view    = "timeSeries"
          stacked = true
          region  = data.aws_region.current.name
          title   = "Lambda Function Activity"
          period  = 300
        }
      },
      {
        type   = "metric"
        x      = 6
        y      = 6
        width  = 6
        height = 6

        properties = {
          metrics = [
            ["AWS/Lambda", "Errors", "FunctionName", aws_lambda_function.ocr.function_name],
            [".", ".", ".", aws_lambda_function.structure.function_name],
            [".", ".", ".", aws_lambda_function.alt_text.function_name],
            [".", ".", ".", aws_lambda_function.tag_pdf.function_name],
            [".", ".", ".", aws_lambda_function.validate.function_name],
            [".", ".", ".", aws_lambda_function.notify.function_name],
          ]
          view    = "timeSeries"
          stacked = true
          region  = data.aws_region.current.name
          title   = "Lambda Errors"
          period  = 300
        }
      }
    ]
  })
}

# CloudWatch Alarms for Lambda function errors
resource "aws_cloudwatch_metric_alarm" "lambda_error_rate" {
  for_each = local.lambda_functions

  alarm_name          = "${local.app_name}-${var.environment}-${each.key}-error-rate"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "Errors"
  namespace           = "AWS/Lambda"
  period              = "300"
  statistic           = "Sum"
  threshold           = "5"
  alarm_description   = "This metric monitors error rate for ${each.key} function"
  insufficient_data_actions = []

  dimensions = {
    FunctionName = "${local.app_name}-${var.environment}-${each.key}"
  }

  alarm_actions = [
    aws_sns_topic.alerts.arn
  ]

  tags = local.common_tags
}

# CloudWatch Alarms for Lambda function duration
resource "aws_cloudwatch_metric_alarm" "lambda_duration" {
  for_each = local.lambda_functions

  alarm_name          = "${local.app_name}-${var.environment}-${each.key}-duration"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "Duration"
  namespace           = "AWS/Lambda"
  period              = "300"
  statistic           = "Average"
  threshold           = tostring(each.value.timeout * 1000 * 0.8) # 80% of timeout
  alarm_description   = "This metric monitors duration for ${each.key} function"
  insufficient_data_actions = []

  dimensions = {
    FunctionName = "${local.app_name}-${var.environment}-${each.key}"
  }

  alarm_actions = [
    aws_sns_topic.alerts.arn
  ]

  tags = local.common_tags
}

# Step Functions execution failure alarm
resource "aws_cloudwatch_metric_alarm" "step_functions_failures" {
  alarm_name          = "${local.app_name}-${var.environment}-stepfunctions-failures"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "1"
  metric_name         = "ExecutionsFailed"
  namespace           = "AWS/States"
  period              = "300"
  statistic           = "Sum"
  threshold           = "1"
  alarm_description   = "This metric monitors Step Functions execution failures"
  insufficient_data_actions = []

  dimensions = {
    StateMachineArn = aws_sfn_state_machine.pdf_processing.arn
  }

  alarm_actions = [
    aws_sns_topic.alerts.arn
  ]

  tags = local.common_tags
}

# DynamoDB throttling alarms
resource "aws_cloudwatch_metric_alarm" "dynamodb_read_throttles" {
  for_each = {
    documents = aws_dynamodb_table.documents.name
    jobs      = aws_dynamodb_table.jobs.name
  }

  alarm_name          = "${local.app_name}-${var.environment}-${each.key}-read-throttles"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "ThrottledRequests"
  namespace           = "AWS/DynamoDB"
  period              = "300"
  statistic           = "Sum"
  threshold           = "1"
  alarm_description   = "This metric monitors read throttling for ${each.key} table"
  insufficient_data_actions = []

  dimensions = {
    TableName = each.value
    Operation = "GetItem"
  }

  alarm_actions = [
    aws_sns_topic.alerts.arn
  ]

  tags = local.common_tags
}

# S3 bucket metrics and alarms
resource "aws_cloudwatch_metric_alarm" "s3_4xx_errors" {
  for_each = {
    originals   = aws_s3_bucket.pdf_originals.bucket
    derivatives = aws_s3_bucket.pdf_derivatives.bucket
    temp        = aws_s3_bucket.pdf_temp.bucket
    reports     = aws_s3_bucket.pdf_reports.bucket
  }

  alarm_name          = "${local.app_name}-${var.environment}-s3-${each.key}-4xx-errors"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "4xxErrors"
  namespace           = "AWS/S3"
  period              = "300"
  statistic           = "Sum"
  threshold           = "10"
  alarm_description   = "This metric monitors 4xx errors for S3 bucket ${each.key}"
  insufficient_data_actions = []

  dimensions = {
    BucketName = each.value
    FilterId   = "EntireBucket"
  }

  alarm_actions = [
    aws_sns_topic.alerts.arn
  ]

  tags = local.common_tags
}

# OpenSearch collection health alarm
resource "aws_cloudwatch_metric_alarm" "opensearch_indexing_rate" {
  alarm_name          = "${local.app_name}-${var.environment}-opensearch-indexing-failures"
  comparison_operator = "LessThanThreshold"
  evaluation_periods  = "3"
  metric_name         = "IndexingRate"
  namespace           = "AWS/AOSS"
  period              = "300"
  statistic           = "Average"
  threshold           = "0.95"  # 95% success rate
  alarm_description   = "This metric monitors OpenSearch indexing success rate"
  insufficient_data_actions = []

  dimensions = {
    CollectionName = aws_opensearchserverless_collection.pdf_embeddings.name
  }

  alarm_actions = [
    aws_sns_topic.alerts.arn
  ]

  treat_missing_data = "notBreaching"

  tags = local.common_tags
}

# Custom application metrics alarms
resource "aws_cloudwatch_metric_alarm" "processing_success_rate" {
  alarm_name          = "${local.app_name}-${var.environment}-processing-success-rate"
  comparison_operator = "LessThanThreshold"
  evaluation_periods  = "3"
  metric_name         = "ProcessingSuccessRate"
  namespace           = "PDF-Accessibility"
  period              = "900"  # 15 minutes
  statistic           = "Average"
  threshold           = "0.9"  # 90% success rate
  alarm_description   = "Overall PDF processing success rate too low"
  insufficient_data_actions = []

  alarm_actions = [
    aws_sns_topic.alerts.arn
  ]

  tags = local.common_tags
}

# Log metric filters for error tracking
resource "aws_cloudwatch_log_metric_filter" "api_errors" {
  name           = "${local.app_name}-${var.environment}-api-errors"
  log_group_name = aws_cloudwatch_log_group.api_logs.name
  pattern        = "[timestamp, request_id, ERROR]"

  metric_transformation {
    name          = "APIErrors"
    namespace     = "PDF-Accessibility"
    value         = "1"
    default_value = "0"
  }
}

resource "aws_cloudwatch_log_metric_filter" "processing_failures" {
  for_each = aws_cloudwatch_log_group.processing_lambda_logs

  name           = "${local.app_name}-${var.environment}-${each.key}-failures"
  log_group_name = each.value.name
  pattern        = "[timestamp, request_id, FAILED]"

  metric_transformation {
    name          = "ProcessingFailures"
    namespace     = "PDF-Accessibility"
    value         = "1"
    default_value = "0"
    
    dimensions = {
      FunctionName = each.key
    }
  }
}

# Outputs for monitoring
output "cloudwatch_dashboard_url" {
  description = "URL to the CloudWatch dashboard"
  value       = "https://${data.aws_region.current.name}.console.aws.amazon.com/cloudwatch/home?region=${data.aws_region.current.name}#dashboards:name=${aws_cloudwatch_dashboard.pdf_processing_dashboard.dashboard_name}"
}

output "monitoring_alarms" {
  description = "List of monitoring alarm names"
  value = merge(
    {
      for k, v in aws_cloudwatch_metric_alarm.lambda_error_rate : k => v.alarm_name
    },
    {
      step_functions_failures = aws_cloudwatch_metric_alarm.step_functions_failures.alarm_name
      processing_success_rate = aws_cloudwatch_metric_alarm.processing_success_rate.alarm_name
    }
  )
}