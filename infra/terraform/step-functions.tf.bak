# Step Functions State Machine for PDF Processing Pipeline

# IAM role for Step Functions
resource "aws_iam_role" "step_functions_role" {
  name = "${local.app_name}-${var.environment}-step-functions-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "states.amazonaws.com"
        }
      }
    ]
  })

  tags = local.common_tags
}

# IAM policy for Step Functions
resource "aws_iam_role_policy" "step_functions_policy" {
  name = "${local.app_name}-${var.environment}-step-functions-policy"
  role = aws_iam_role.step_functions_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      # Lambda invoke permissions
      {
        Effect = "Allow"
        Action = [
          "lambda:InvokeFunction"
        ]
        Resource = [
          aws_lambda_function.ocr.arn,
          aws_lambda_function.structure.arn,
          aws_lambda_function.alt_text.arn,
          aws_lambda_function.tag_pdf.arn,
          aws_lambda_function.exports.arn,
          aws_lambda_function.validate.arn,
          aws_lambda_function.notify.arn
        ]
      },
      # CloudWatch Logs
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogDelivery",
          "logs:GetLogDelivery",
          "logs:UpdateLogDelivery",
          "logs:DeleteLogDelivery",
          "logs:ListLogDeliveries",
          "logs:PutResourcePolicy",
          "logs:DescribeResourcePolicies",
          "logs:DescribeLogGroups"
        ]
        Resource = "*"
      },
      # X-Ray tracing
      {
        Effect = "Allow"
        Action = [
          "xray:PutTraceSegments",
          "xray:PutTelemetryRecords",
          "xray:GetSamplingRules",
          "xray:GetSamplingTargets"
        ]
        Resource = "*"
      }
    ]
  })
}

# Step Functions State Machine
resource "aws_sfn_state_machine" "pdf_processing" {
  name     = "${local.app_name}-${var.environment}-pdf-processing"
  role_arn = aws_iam_role.step_functions_role.arn

  definition = templatefile("${path.module}/../step-functions/pdf-processing-workflow.json", {
    OCRFunctionArn      = aws_lambda_function.ocr.arn
    StructureFunctionArn = aws_lambda_function.structure.arn
    AltTextFunctionArn  = aws_lambda_function.alt_text.arn
    TagPDFFunctionArn   = aws_lambda_function.tag_pdf.arn
    ExportsFunctionArn  = aws_lambda_function.exports.arn
    ValidateFunctionArn = aws_lambda_function.validate.arn
    NotifyFunctionArn   = aws_lambda_function.notify.arn
  })

  logging_configuration {
    log_destination        = "${aws_cloudwatch_log_group.step_functions_logs.arn}:*"
    include_execution_data = true
    level                  = "ALL"
  }

  tracing_configuration {
    enabled = true
  }

  tags = local.common_tags
}

# CloudWatch Log Group for Step Functions
resource "aws_cloudwatch_log_group" "step_functions_logs" {
  name              = "/aws/stepfunctions/${local.app_name}-${var.environment}-pdf-processing"
  retention_in_days = var.log_retention_days
  kms_key_id       = var.cloudwatch_logs_kms_key_id

  tags = local.common_tags
}

# CloudWatch Dashboard for Step Functions
resource "aws_cloudwatch_dashboard" "step_functions" {
  dashboard_name = "${local.app_name}-${var.environment}-step-functions"

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
            ["AWS/States", "ExecutionsStarted", "StateMachineArn", aws_sfn_state_machine.pdf_processing.arn],
            [".", "ExecutionsSucceeded", ".", "."],
            [".", "ExecutionsFailed", ".", "."],
            [".", "ExecutionsAborted", ".", "."],
            [".", "ExecutionsTimedOut", ".", "."]
          ]
          view    = "timeSeries"
          stacked = false
          region  = data.aws_region.current.name
          title   = "Step Functions Execution Metrics"
          period  = 300
        }
      },
      {
        type   = "metric"
        x      = 12
        y      = 0
        width  = 12
        height = 6
        properties = {
          metrics = [
            ["AWS/States", "ExecutionTime", "StateMachineArn", aws_sfn_state_machine.pdf_processing.arn]
          ]
          view    = "timeSeries"
          stacked = false
          region  = data.aws_region.current.name
          title   = "Execution Duration"
          period  = 300
        }
      }
    ]
  })

  tags = local.common_tags
}

# CloudWatch Alarms for monitoring
resource "aws_cloudwatch_metric_alarm" "step_functions_failures" {
  alarm_name          = "${local.app_name}-${var.environment}-step-functions-failures"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "ExecutionsFailed"
  namespace           = "AWS/States"
  period              = "300"
  statistic           = "Sum"
  threshold           = "5"
  alarm_description   = "This metric monitors Step Functions execution failures"
  alarm_actions       = [aws_sns_topic.alerts.arn]
  ok_actions         = [aws_sns_topic.alerts.arn]
  treat_missing_data = "notBreaching"

  dimensions = {
    StateMachineArn = aws_sfn_state_machine.pdf_processing.arn
  }

  tags = local.common_tags
}

# Outputs
output "step_functions_arn" {
  description = "ARN of the Step Functions state machine"
  value       = aws_sfn_state_machine.pdf_processing.arn
}

output "step_functions_name" {
  description = "Name of the Step Functions state machine"
  value       = aws_sfn_state_machine.pdf_processing.name
}