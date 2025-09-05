# API Gateway HTTP API
resource "aws_apigatewayv2_api" "main" {
  name          = "${local.name_prefix}-api"
  protocol_type = "HTTP"
  description   = "PDF Accessibility Platform API"

  cors_configuration {
    allow_credentials = false
    allow_headers = [
      "content-type",
      "x-amz-date",
      "authorization",
      "x-api-key",
      "x-amz-security-token",
      "x-amz-user-agent"
    ]
    allow_methods = ["*"]
    allow_origins = [
      "http://localhost:3000",
      var.domain_name != "" ? "https://${var.domain_name}" : "https://example.com"
    ]
    expose_headers = ["date", "keep-alive"]
    max_age        = 86400
  }

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-api-gateway"
  })
}

# Cognito JWT Authorizer
resource "aws_apigatewayv2_authorizer" "cognito" {
  api_id           = aws_apigatewayv2_api.main.id
  authorizer_type  = "JWT"
  identity_sources = ["$request.header.Authorization"]
  name             = "cognito-authorizer"

  jwt_configuration {
    audience = [aws_cognito_user_pool_client.web_client.id]
    issuer   = "https://${aws_cognito_user_pool.main.endpoint}"
  }
}

# API Gateway Stage
resource "aws_apigatewayv2_stage" "default" {
  api_id      = aws_apigatewayv2_api.main.id
  name        = "$default"
  auto_deploy = true

  default_route_settings {
    throttling_rate_limit  = 1000
    throttling_burst_limit = 2000
  }

  access_log_settings {
    destination_arn = aws_cloudwatch_log_group.api_gateway.arn
    format = jsonencode({
      requestId        = "$context.requestId"
      ip               = "$context.identity.sourceIp"
      requestTime      = "$context.requestTime"
      httpMethod       = "$context.httpMethod"
      routeKey         = "$context.routeKey"
      status           = "$context.status"
      protocol         = "$context.protocol"
      responseLength   = "$context.responseLength"
      error            = "$context.error.message"
      integrationError = "$context.integrationErrorMessage"
    })
  }

  tags = local.common_tags
}

# CloudWatch Log Group for API Gateway
resource "aws_cloudwatch_log_group" "api_gateway" {
  name              = "/aws/apigateway/${aws_apigatewayv2_api.main.name}"
  retention_in_days = var.log_retention_days

  tags = local.common_tags
}

# Example API Routes (placeholders for Lambda integrations)
resource "aws_apigatewayv2_route" "health" {
  api_id    = aws_apigatewayv2_api.main.id
  route_key = "GET /health"
  target    = "integrations/${aws_apigatewayv2_integration.health.id}"
}

resource "aws_apigatewayv2_route" "documents" {
  api_id             = aws_apigatewayv2_api.main.id
  route_key          = "GET /documents"
  target             = "integrations/${aws_apigatewayv2_integration.documents.id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito.id
}

resource "aws_apigatewayv2_route" "documents_post" {
  api_id             = aws_apigatewayv2_api.main.id
  route_key          = "POST /documents"
  target             = "integrations/${aws_apigatewayv2_integration.documents_post.id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito.id
}

resource "aws_apigatewayv2_route" "document_by_id" {
  api_id             = aws_apigatewayv2_api.main.id
  route_key          = "GET /documents/{documentId}"
  target             = "integrations/${aws_apigatewayv2_integration.document_by_id.id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito.id
}

# HTTP proxy integrations (to be replaced with Lambda integrations)
resource "aws_apigatewayv2_integration" "health" {
  api_id             = aws_apigatewayv2_api.main.id
  integration_type   = "HTTP_PROXY"
  integration_method = "GET"
  integration_uri    = "https://httpbin.org/status/200"
}

resource "aws_apigatewayv2_integration" "documents" {
  api_id             = aws_apigatewayv2_api.main.id
  integration_type   = "HTTP_PROXY"
  integration_method = "GET"
  integration_uri    = "https://httpbin.org/json"
}

resource "aws_apigatewayv2_integration" "documents_post" {
  api_id             = aws_apigatewayv2_api.main.id
  integration_type   = "HTTP_PROXY"
  integration_method = "POST"
  integration_uri    = "https://httpbin.org/post"
}

resource "aws_apigatewayv2_integration" "document_by_id" {
  api_id             = aws_apigatewayv2_api.main.id
  integration_type   = "HTTP_PROXY"
  integration_method = "GET"
  integration_uri    = "https://httpbin.org/json"
}

# Custom Domain (optional)
resource "aws_apigatewayv2_domain_name" "api" {
  count       = var.certificate_arn != "" ? 1 : 0
  domain_name = "api.${var.domain_name}"

  domain_name_configuration {
    certificate_arn = var.certificate_arn
    endpoint_type   = "REGIONAL"
    security_policy = "TLS_1_2"
  }

  tags = local.common_tags
}

resource "aws_apigatewayv2_api_mapping" "api" {
  count       = var.certificate_arn != "" ? 1 : 0
  api_id      = aws_apigatewayv2_api.main.id
  domain_name = aws_apigatewayv2_domain_name.api[0].id
  stage       = aws_apigatewayv2_stage.default.id
}