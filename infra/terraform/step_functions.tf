# Step Functions State Machine for PDF Processing
resource "aws_sfn_state_machine" "pdf_processing" {
  name     = "${local.name_prefix}-pdf-processing"
  role_arn = aws_iam_role.step_functions.arn
  definition = templatefile("${path.module}/state_machine_definition.json", {
    documents_table_name = aws_dynamodb_table.documents.name
  })

  logging_configuration {
    log_destination        = "${aws_cloudwatch_log_group.step_functions.arn}:*"
    include_execution_data = true
    level                  = "ERROR"
  }

  tracing_configuration {
    enabled = true
  }

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-pdf-processing-state-machine"
  })
}

# CloudWatch Log Group for Step Functions
resource "aws_cloudwatch_log_group" "step_functions" {
  name              = "/aws/vendedlogs/states/${local.name_prefix}-pdf-processing"
  retention_in_days = var.log_retention_days

  tags = local.common_tags
}