# AWS Glue resources for CUR data catalog and ETL

# Glue database for cost analytics
resource "aws_glue_catalog_database" "cost_analytics" {
  name        = local.glue_database_name
  description = "Database for AWS Cost and Usage Report analysis"
  
  tags = local.common_tags
}

# IAM role for Glue crawler
resource "aws_iam_role" "glue_crawler" {
  name = "${local.name_prefix}-glue-crawler-role"
  
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "glue.amazonaws.com"
        }
      }
    ]
  })
  
  tags = local.common_tags
}

# IAM policy for Glue crawler to access S3 and create tables
resource "aws_iam_role_policy" "glue_crawler" {
  name = "${local.name_prefix}-glue-crawler-policy"
  role = aws_iam_role.glue_crawler.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:ListBucket"
        ]
        Resource = [
          aws_s3_bucket.cur_data.arn,
          "${aws_s3_bucket.cur_data.arn}/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "glue:*",
          "iam:ListRolePolicies",
          "iam:GetRole",
          "iam:GetRolePolicy"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:*:*:*"
      }
    ]
  })
}

# Attach AWS managed policy for Glue service
resource "aws_iam_role_policy_attachment" "glue_service" {
  role       = aws_iam_role.glue_crawler.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSGlueServiceRole"
}

# Glue crawler for CUR data
resource "aws_glue_crawler" "cur_crawler" {
  database_name = aws_glue_catalog_database.cost_analytics.name
  name          = "${local.name_prefix}-cur-crawler"
  role          = aws_iam_role.glue_crawler.arn
  
  description = "Crawler for AWS Cost and Usage Report data"
  
  s3_target {
    path = "s3://${aws_s3_bucket.cur_data.bucket}/cur-data/${local.cur_report_name}/"
    
    # Exclude manifest files and other non-data files
    exclusions = [
      "**.json",
      "**_$folder$",
      "**/cost-and-usage-data-status/*"
    ]
  }
  
  # Crawler configuration
  configuration = jsonencode({
    Version = 1.0
    CrawlerOutput = {
      Partitions = {
        AddOrUpdateBehavior = "InheritFromTable"
      }
      Tables = {
        AddOrUpdateBehavior = "MergeNewColumns"
      }
    }
  })
  
  # Schema change policy
  schema_change_policy {
    update_behavior = "UPDATE_IN_DATABASE"
    delete_behavior = "DEPRECATE_IN_DATABASE"
  }
  
  # Run crawler daily to pick up new data
  schedule = var.crawler_schedule
  
  tags = local.common_tags
  
  depends_on = [
    aws_iam_role_policy_attachment.glue_service,
    aws_cur_report_definition.main
  ]
}

# Glue table for CUR data (manual definition for better control)
resource "aws_glue_catalog_table" "cur_table" {
  name          = local.glue_table_name
  database_name = aws_glue_catalog_database.cost_analytics.name
  description   = "AWS Cost and Usage Report table with optimized schema"
  
  table_type = "EXTERNAL_TABLE"
  
  parameters = {
    "classification"           = "parquet"
    "compressionType"         = "gzip"
    "typeOfData"              = "file"
    "areColumnsQuoted"        = "false"
    "columnsOrdered"          = "true"
    "delimiter"               = ""
    "skip.header.line.count"  = "0"
    "serialization.format"    = "1"
  }
  
  storage_descriptor {
    location      = "s3://${aws_s3_bucket.cur_data.bucket}/cur-data/${local.cur_report_name}/"
    input_format  = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat"
    output_format = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat"
    
    ser_de_info {
      serialization_library = "org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe"
    }
    
    # Key columns for cost analysis
    columns {
      name    = "identity_line_item_id"
      type    = "string"
      comment = "Unique identifier for each line item"
    }
    
    columns {
      name    = "bill_billing_entity"
      type    = "string"
      comment = "The AWS billing entity"
    }
    
    columns {
      name    = "bill_bill_type"
      type    = "string"
      comment = "The type of bill"
    }
    
    columns {
      name    = "bill_payer_account_id"
      type    = "string"
      comment = "The account ID of the paying account"
    }
    
    columns {
      name    = "bill_billing_period_start_date"
      type    = "timestamp"
      comment = "The start date of the billing period"
    }
    
    columns {
      name    = "bill_billing_period_end_date"
      type    = "timestamp"
      comment = "The end date of the billing period"
    }
    
    columns {
      name    = "line_item_usage_account_id"
      type    = "string"
      comment = "The account ID that used the resource"
    }
    
    columns {
      name    = "line_item_line_item_type"
      type    = "string"
      comment = "The type of line item"
    }
    
    columns {
      name    = "line_item_usage_start_date"
      type    = "timestamp"
      comment = "The start date of the usage"
    }
    
    columns {
      name    = "line_item_usage_end_date"
      type    = "timestamp"
      comment = "The end date of the usage"
    }
    
    columns {
      name    = "line_item_product_code"
      type    = "string"
      comment = "The AWS service code"
    }
    
    columns {
      name    = "line_item_usage_type"
      type    = "string"
      comment = "The usage type"
    }
    
    columns {
      name    = "line_item_operation"
      type    = "string"
      comment = "The operation"
    }
    
    columns {
      name    = "line_item_availability_zone"
      type    = "string"
      comment = "The Availability Zone"
    }
    
    columns {
      name    = "line_item_resource_id"
      type    = "string"
      comment = "The resource ID"
    }
    
    columns {
      name    = "line_item_usage_amount"
      type    = "double"
      comment = "The usage amount"
    }
    
    columns {
      name    = "line_item_normalization_factor"
      type    = "double"
      comment = "The normalization factor"
    }
    
    columns {
      name    = "line_item_normalized_usage_amount"
      type    = "double"
      comment = "The normalized usage amount"
    }
    
    columns {
      name    = "line_item_currency_code"
      type    = "string"
      comment = "The currency code"
    }
    
    columns {
      name    = "line_item_unblended_rate"
      type    = "string"
      comment = "The unblended rate"
    }
    
    columns {
      name    = "line_item_unblended_cost"
      type    = "double"
      comment = "The unblended cost"
    }
    
    columns {
      name    = "line_item_blended_rate"
      type    = "string"
      comment = "The blended rate"
    }
    
    columns {
      name    = "line_item_blended_cost"
      type    = "double"
      comment = "The blended cost"
    }
    
    columns {
      name    = "product_product_name"
      type    = "string"
      comment = "The product name"
    }
    
    columns {
      name    = "product_region"
      type    = "string"
      comment = "The AWS region"
    }
    
    # Resource tags (dynamic based on your tag structure)
    columns {
      name    = "resource_tags_application"
      type    = "string"
      comment = "Application tag"
    }
    
    columns {
      name    = "resource_tags_environment"
      type    = "string"
      comment = "Environment tag"
    }
    
    columns {
      name    = "resource_tags_component"
      type    = "string"
      comment = "Component tag"
    }
    
    columns {
      name    = "resource_tags_cost_center"
      type    = "string"
      comment = "Cost center tag"
    }
    
    columns {
      name    = "resource_tags_service"
      type    = "string"
      comment = "Service tag"
    }
    
    columns {
      name    = "resource_tags_managed_by"
      type    = "string"
      comment = "Managed by tag"
    }
  }
  
  # Partition keys for efficient querying
  partition_keys {
    name    = "year"
    type    = "string"
    comment = "Year partition"
  }
  
  partition_keys {
    name    = "month"
    type    = "string"
    comment = "Month partition"
  }
  
  tags = local.common_tags
}