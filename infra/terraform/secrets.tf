# Google OAuth Secrets
resource "aws_secretsmanager_secret" "google_oauth" {
  name        = "${var.environment}/accesspdf/google-oauth"
  description = "Google OAuth2 credentials for Cognito OIDC integration"

  tags = merge(local.common_tags, {
    Name        = "${local.name_prefix}-google-oauth"
    Environment = var.environment
  })
}

resource "aws_secretsmanager_secret_version" "google_oauth" {
  secret_id = aws_secretsmanager_secret.google_oauth.id
  secret_string = jsonencode({
    client_id     = var.google_oauth_client_id
    client_secret = var.google_oauth_client_secret
  })

  lifecycle {
    ignore_changes = [secret_string]
  }
}

# JWT Signing Secrets
resource "aws_secretsmanager_secret" "jwt_secrets" {
  name        = "${var.environment}/accesspdf/jwt-secrets"
  description = "JWT signing secrets for API authentication"

  tags = merge(local.common_tags, {
    Name        = "${local.name_prefix}-jwt-secrets"
    Environment = var.environment
  })
}

resource "aws_secretsmanager_secret_version" "jwt_secrets" {
  secret_id = aws_secretsmanager_secret.jwt_secrets.id
  secret_string = jsonencode({
    jwt_secret_key = var.jwt_secret_key != "" ? var.jwt_secret_key : random_password.jwt_secret.result
  })

  lifecycle {
    ignore_changes = [secret_string]
  }
}

# Generate random JWT secret if not provided
resource "random_password" "jwt_secret" {
  length  = 64
  special = true
}