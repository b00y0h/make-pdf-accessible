# AWS Athena resources for querying CUR data

# Athena workgroup for cost analytics queries
resource "aws_athena_workgroup" "cost_analytics" {
  name        = local.athena_workgroup_name
  description = "Workgroup for AWS cost analytics queries"
  state       = "ENABLED"
  
  configuration {
    enforce_workgroup_configuration    = true
    publish_cloudwatch_metrics_enabled = true
    
    result_configuration {
      output_location = "s3://${aws_s3_bucket.athena_results.bucket}/query-results/"
      
      encryption_configuration {
        encryption_option = "SSE_S3"
      }
    }
    
    # Query execution settings
    bytes_scanned_cutoff_per_query     = var.athena_bytes_scanned_cutoff
    engine_version {
      selected_engine_version = "Athena engine version 3"
    }
  }
  
  tags = local.common_tags
}

# IAM role for Athena query execution (for the application)
resource "aws_iam_role" "athena_execution" {
  name = "${local.name_prefix}-athena-execution-role"
  
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "athena.amazonaws.com"
        }
      },
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          AWS = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:root"
        }
        Condition = {
          StringEquals = {
            "sts:ExternalId" = var.external_id
          }
        }
      }
    ]
  })
  
  tags = local.common_tags
}

# IAM policy for Athena execution
resource "aws_iam_role_policy" "athena_execution" {
  name = "${local.name_prefix}-athena-execution-policy"
  role = aws_iam_role.athena_execution.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "athena:BatchGetQueryExecution",
          "athena:GetQueryExecution",
          "athena:GetQueryResults",
          "athena:GetWorkGroup",
          "athena:StartQueryExecution",
          "athena:StopQueryExecution"
        ]
        Resource = [
          aws_athena_workgroup.cost_analytics.arn,
          "arn:aws:athena:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:datacatalog/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "glue:GetDatabase",
          "glue:GetTable",
          "glue:GetPartitions",
          "glue:BatchCreatePartition",
          "glue:BatchGetPartition"
        ]
        Resource = [
          aws_glue_catalog_database.cost_analytics.arn,
          "arn:aws:glue:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:catalog",
          "arn:aws:glue:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:table/${aws_glue_catalog_database.cost_analytics.name}/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:ListBucket",
          "s3:GetBucketLocation"
        ]
        Resource = [
          aws_s3_bucket.cur_data.arn,
          "${aws_s3_bucket.cur_data.arn}/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:ListBucket",
          "s3:PutObject",
          "s3:DeleteObject"
        ]
        Resource = [
          aws_s3_bucket.athena_results.arn,
          "${aws_s3_bucket.athena_results.arn}/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "s3:ListAllMyBuckets"
        ]
        Resource = "*"
      }
    ]
  })
}

# Athena named queries for common cost analysis patterns
resource "aws_athena_named_query" "monthly_costs_by_service" {
  name        = "monthly-costs-by-service"
  workgroup   = aws_athena_workgroup.cost_analytics.name
  database    = aws_glue_catalog_database.cost_analytics.name
  description = "Get monthly costs grouped by AWS service"

  query = <<-EOT
    SELECT 
      date_format(line_item_usage_start_date, '%Y-%m') as month,
      line_item_product_code as service,
      SUM(line_item_unblended_cost) as unblended_cost,
      SUM(line_item_blended_cost) as blended_cost,
      line_item_currency_code as currency
    FROM ${aws_glue_catalog_database.cost_analytics.name}.${local.glue_table_name}
    WHERE line_item_line_item_type IN ('Usage', 'DiscountedUsage', 'Tax', 'Credit', 'Refund')
      AND line_item_usage_start_date >= date('2024-01-01')
      AND line_item_usage_start_date < current_date
      AND year = '{year}'
      AND month = '{month}'
    GROUP BY 
      date_format(line_item_usage_start_date, '%Y-%m'),
      line_item_product_code,
      line_item_currency_code
    ORDER BY month DESC, unblended_cost DESC
  EOT
}

resource "aws_athena_named_query" "costs_by_tag" {
  name        = "costs-by-tag"
  workgroup   = aws_athena_workgroup.cost_analytics.name
  database    = aws_glue_catalog_database.cost_analytics.name
  description = "Get costs grouped by resource tags"

  query = <<-EOT
    SELECT 
      date_format(line_item_usage_start_date, '%Y-%m') as month,
      COALESCE(resource_tags_application, 'untagged') as application,
      COALESCE(resource_tags_environment, 'untagged') as environment,
      COALESCE(resource_tags_component, 'untagged') as component,
      COALESCE(resource_tags_cost_center, 'untagged') as cost_center,
      line_item_product_code as service,
      SUM(line_item_unblended_cost) as unblended_cost,
      SUM(line_item_blended_cost) as blended_cost,
      line_item_currency_code as currency
    FROM ${aws_glue_catalog_database.cost_analytics.name}.${local.glue_table_name}
    WHERE line_item_line_item_type IN ('Usage', 'DiscountedUsage', 'Tax', 'Credit', 'Refund')
      AND line_item_usage_start_date >= date('2024-01-01')
      AND line_item_usage_start_date < current_date
      AND year = '{year}'
      AND month = '{month}'
    GROUP BY 
      date_format(line_item_usage_start_date, '%Y-%m'),
      COALESCE(resource_tags_application, 'untagged'),
      COALESCE(resource_tags_environment, 'untagged'),
      COALESCE(resource_tags_component, 'untagged'),
      COALESCE(resource_tags_cost_center, 'untagged'),
      line_item_product_code,
      line_item_currency_code
    ORDER BY month DESC, unblended_cost DESC
  EOT
}

resource "aws_athena_named_query" "daily_costs_trend" {
  name        = "daily-costs-trend"
  workgroup   = aws_athena_workgroup.cost_analytics.name
  database    = aws_glue_catalog_database.cost_analytics.name
  description = "Get daily cost trends for detailed analysis"

  query = <<-EOT
    SELECT 
      date(line_item_usage_start_date) as usage_date,
      line_item_product_code as service,
      SUM(line_item_unblended_cost) as unblended_cost,
      SUM(line_item_blended_cost) as blended_cost,
      line_item_currency_code as currency
    FROM ${aws_glue_catalog_database.cost_analytics.name}.${local.glue_table_name}
    WHERE line_item_line_item_type IN ('Usage', 'DiscountedUsage', 'Tax', 'Credit', 'Refund')
      AND line_item_usage_start_date >= date('{start_date}')
      AND line_item_usage_start_date < date('{end_date}')
      AND year = '{year}'
      AND month = '{month}'
    GROUP BY 
      date(line_item_usage_start_date),
      line_item_product_code,
      line_item_currency_code
    ORDER BY usage_date DESC, unblended_cost DESC
  EOT
}

resource "aws_athena_named_query" "resource_level_costs" {
  name        = "resource-level-costs"
  workgroup   = aws_athena_workgroup.cost_analytics.name
  database    = aws_glue_catalog_database.cost_analytics.name
  description = "Get costs at individual resource level for detailed drilldown"

  query = <<-EOT
    SELECT 
      date_format(line_item_usage_start_date, '%Y-%m') as month,
      line_item_product_code as service,
      line_item_resource_id as resource_id,
      product_region as region,
      line_item_availability_zone as availability_zone,
      COALESCE(resource_tags_application, 'untagged') as application,
      COALESCE(resource_tags_environment, 'untagged') as environment,
      COALESCE(resource_tags_component, 'untagged') as component,
      SUM(line_item_unblended_cost) as unblended_cost,
      SUM(line_item_usage_amount) as usage_amount,
      line_item_currency_code as currency
    FROM ${aws_glue_catalog_database.cost_analytics.name}.${local.glue_table_name}
    WHERE line_item_line_item_type IN ('Usage', 'DiscountedUsage')
      AND line_item_usage_start_date >= date('2024-01-01')
      AND line_item_usage_start_date < current_date
      AND line_item_resource_id != ''
      AND line_item_unblended_cost > 0
      AND year = '{year}'
      AND month = '{month}'
    GROUP BY 
      date_format(line_item_usage_start_date, '%Y-%m'),
      line_item_product_code,
      line_item_resource_id,
      product_region,
      line_item_availability_zone,
      COALESCE(resource_tags_application, 'untagged'),
      COALESCE(resource_tags_environment, 'untagged'),
      COALESCE(resource_tags_component, 'untagged'),
      line_item_currency_code
    ORDER BY month DESC, unblended_cost DESC
    LIMIT 1000
  EOT
}