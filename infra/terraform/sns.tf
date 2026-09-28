# SNS topics used by CloudWatch alarms (alerts) and the notify function
# (notifications). CloudWatch alarms cannot publish to a topic encrypted with
# the AWS-managed SNS key, so a customer-managed key with a CloudWatch grant is
# used instead.

resource "aws_kms_key" "sns" {
  description             = "KMS key for SNS topics"
  deletion_window_in_days = 7
  enable_key_rotation     = true

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "EnableRootPermissions"
        Effect = "Allow"
        Principal = {
          AWS = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:root"
        }
        Action   = "kms:*"
        Resource = "*"
      },
      {
        Sid    = "AllowCloudWatchAndEventsToUseKey"
        Effect = "Allow"
        Principal = {
          Service = [
            "cloudwatch.amazonaws.com",
            "events.amazonaws.com"
          ]
        }
        Action = [
          "kms:GenerateDataKey*",
          "kms:Decrypt"
        ]
        Resource = "*"
      }
    ]
  })

  tags = merge(local.monitoring_tags, {
    Name = "${local.name_prefix}-sns-kms"
  })
}

resource "aws_kms_alias" "sns" {
  name          = "alias/${local.name_prefix}-sns"
  target_key_id = aws_kms_key.sns.key_id
}

# Operational alerts (CloudWatch alarms, DLQ depth, failed executions)
resource "aws_sns_topic" "alerts" {
  name              = "${local.name_prefix}-alerts"
  kms_master_key_id = aws_kms_key.sns.id

  tags = merge(local.monitoring_tags, {
    Name    = "${local.name_prefix}-alerts"
    Purpose = "Operational alerts for on-call"
  })
}

# Customer-facing notifications published by the notify function
resource "aws_sns_topic" "notifications" {
  name              = "${local.name_prefix}-notifications"
  kms_master_key_id = aws_kms_key.sns.id

  tags = merge(local.common_tags, {
    Name    = "${local.name_prefix}-notifications"
    Purpose = "Job completion and status notifications"
  })
}

# Optional e-mail subscription for the alerts topic
resource "aws_sns_topic_subscription" "alerts_email" {
  count     = var.alerts_email != "" ? 1 : 0
  topic_arn = aws_sns_topic.alerts.arn
  protocol  = "email"
  endpoint  = var.alerts_email
}

output "sns_alerts_topic_arn" {
  description = "ARN of the operational alerts SNS topic"
  value       = aws_sns_topic.alerts.arn
}

output "sns_notifications_topic_arn" {
  description = "ARN of the customer notifications SNS topic"
  value       = aws_sns_topic.notifications.arn
}
