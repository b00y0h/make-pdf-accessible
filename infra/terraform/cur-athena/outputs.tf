# Output values from CUR to Athena infrastructure

output "cur_bucket_name" {
  description = "S3 bucket name for CUR data storage"
  value       = aws_s3_bucket.cur_data.bucket
}

output "cur_bucket_arn" {
  description = "S3 bucket ARN for CUR data storage"
  value       = aws_s3_bucket.cur_data.arn
}

output "athena_results_bucket_name" {
  description = "S3 bucket name for Athena query results"
  value       = aws_s3_bucket.athena_results.bucket
}

output "athena_results_bucket_arn" {
  description = "S3 bucket ARN for Athena query results"
  value       = aws_s3_bucket.athena_results.arn
}

output "cur_report_name" {
  description = "Name of the Cost and Usage Report"
  value       = aws_cur_report_definition.main.report_name
}

output "glue_database_name" {
  description = "Name of the Glue catalog database"
  value       = aws_glue_catalog_database.cost_analytics.name
}

output "glue_table_name" {
  description = "Name of the Glue catalog table for CUR data"
  value       = aws_glue_catalog_table.cur_table.name
}

output "glue_crawler_name" {
  description = "Name of the Glue crawler"
  value       = aws_glue_crawler.cur_crawler.name
}

output "athena_workgroup_name" {
  description = "Name of the Athena workgroup"
  value       = aws_athena_workgroup.cost_analytics.name
}

output "athena_workgroup_arn" {
  description = "ARN of the Athena workgroup"
  value       = aws_athena_workgroup.cost_analytics.arn
}

output "athena_execution_role_arn" {
  description = "ARN of the IAM role for Athena query execution"
  value       = aws_iam_role.athena_execution.arn
}

output "glue_crawler_role_arn" {
  description = "ARN of the IAM role for Glue crawler"
  value       = aws_iam_role.glue_crawler.arn
}

# Named queries for reference
output "monthly_costs_query_name" {
  description = "Name of the monthly costs by service named query"
  value       = aws_athena_named_query.monthly_costs_by_service.name
}

output "costs_by_tag_query_name" {
  description = "Name of the costs by tag named query"  
  value       = aws_athena_named_query.costs_by_tag.name
}

output "daily_costs_trend_query_name" {
  description = "Name of the daily costs trend named query"
  value       = aws_athena_named_query.daily_costs_trend.name
}

output "resource_level_costs_query_name" {
  description = "Name of the resource level costs named query"
  value       = aws_athena_named_query.resource_level_costs.name
}

# Configuration for application use
output "application_config" {
  description = "Configuration values needed by the application"
  value = {
    athena_workgroup        = aws_athena_workgroup.cost_analytics.name
    athena_database         = aws_glue_catalog_database.cost_analytics.name
    athena_table           = aws_glue_catalog_table.cur_table.name
    athena_results_bucket  = aws_s3_bucket.athena_results.bucket
    cur_bucket            = aws_s3_bucket.cur_data.bucket
    execution_role_arn    = aws_iam_role.athena_execution.arn
  }
}

# Summary of created resources
output "resource_summary" {
  description = "Summary of all created resources"
  value = {
    s3_buckets = [
      aws_s3_bucket.cur_data.bucket,
      aws_s3_bucket.athena_results.bucket
    ]
    cur_report = aws_cur_report_definition.main.report_name
    glue_resources = {
      database = aws_glue_catalog_database.cost_analytics.name
      table    = aws_glue_catalog_table.cur_table.name
      crawler  = aws_glue_crawler.cur_crawler.name
    }
    athena_resources = {
      workgroup = aws_athena_workgroup.cost_analytics.name
      named_queries = [
        aws_athena_named_query.monthly_costs_by_service.name,
        aws_athena_named_query.costs_by_tag.name,
        aws_athena_named_query.daily_costs_trend.name,
        aws_athena_named_query.resource_level_costs.name
      ]
    }
    iam_roles = [
      aws_iam_role.athena_execution.name,
      aws_iam_role.glue_crawler.name
    ]
  }
}