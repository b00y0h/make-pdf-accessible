# Step Functions State Machine for PDF Processing
resource "aws_sfn_state_machine" "pdf_processing" {
  name     = "${local.name_prefix}-pdf-processing"
  role_arn = aws_iam_role.step_functions.arn
  definition = templatefile("${path.module}/../step-functions/pdf-processing-workflow.json", {
    OCRFunctionArn       = aws_lambda_function.ocr.arn
    StructureFunctionArn = aws_lambda_function.structure.arn
    AltTextFunctionArn   = aws_lambda_function.alt_text.arn
    TagPDFFunctionArn    = aws_lambda_function.tag_pdf.arn
    ExportsFunctionArn   = aws_lambda_function.exports.arn
    ValidateFunctionArn  = aws_lambda_function.validate.arn
    NotifyFunctionArn    = aws_lambda_function.notify.arn
  })

  logging_configuration {
    log_destination        = "${aws_cloudwatch_log_group.step_functions.arn}:*"
    include_execution_data = true
    level                  = "ERROR"
  }

  tracing_configuration {
    enabled = true
  }

  depends_on = [
    aws_lambda_function.ocr,
    aws_lambda_function.structure,
    aws_lambda_function.alt_text,
    aws_lambda_function.tag_pdf,
    aws_lambda_function.exports,
    aws_lambda_function.validate,
    aws_lambda_function.notify
  ]

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

# Outputs
output "step_functions_state_machine_arn" {
  description = "ARN of the PDF processing Step Functions state machine"
  value       = aws_sfn_state_machine.pdf_processing.arn
}

output "step_functions_state_machine_name" {
  description = "Name of the PDF processing Step Functions state machine"
  value       = aws_sfn_state_machine.pdf_processing.name
}