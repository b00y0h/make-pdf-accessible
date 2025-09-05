# Cognito User Pool
resource "aws_cognito_user_pool" "main" {
  name = "${local.name_prefix}-user-pool"

  # Password policy
  password_policy {
    minimum_length    = 12
    require_lowercase = true
    require_numbers   = true
    require_symbols   = true
    require_uppercase = true
  }

  # User attributes
  username_attributes = ["email"]
  
  auto_verified_attributes = ["email"]

  # Account recovery
  account_recovery_setting {
    recovery_mechanism {
      name     = "verified_email"
      priority = 1
    }
  }

  # User pool add-ons
  user_pool_add_ons {
    advanced_security_mode = "ENFORCED"
  }

  # Device tracking
  device_configuration {
    challenge_required_on_new_device      = true
    device_only_remembered_on_user_prompt = true
  }

  # Email configuration
  email_configuration {
    email_sending_account = "COGNITO_DEFAULT"
  }

  # Schema attributes (using Cognito defaults to avoid modification conflicts)

  # Verification message templates
  verification_message_template {
    default_email_option = "CONFIRM_WITH_CODE"
    email_subject        = "Your PDF Accessibility Platform verification code"
    email_message        = "Your verification code is {####}"
  }

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-user-pool"
  })

  lifecycle {
    create_before_destroy = true
  }
}

# Cognito User Pool Domain
resource "aws_cognito_user_pool_domain" "main" {
  domain       = "${local.name_prefix}-auth-${local.name_suffix}"
  user_pool_id = aws_cognito_user_pool.main.id
}

# Cognito User Pool Client
resource "aws_cognito_user_pool_client" "web_client" {
  name         = "${local.name_prefix}-web-client"
  user_pool_id = aws_cognito_user_pool.main.id

  callback_urls                        = [
    "http://localhost:3000/auth/callback",
    var.domain_name != "" ? "https://${var.domain_name}/auth/callback" : "https://example.com/auth/callback"
  ]
  logout_urls                          = [
    "http://localhost:3000",
    var.domain_name != "" ? "https://${var.domain_name}" : "https://example.com"
  ]
  
  allowed_oauth_flows_user_pool_client = true
  allowed_oauth_flows                  = ["code"]
  allowed_oauth_scopes                 = ["openid", "email", "profile"]

  supported_identity_providers = ["COGNITO"]

  # Token validity
  access_token_validity  = 1  # 1 hour
  id_token_validity     = 1  # 1 hour
  refresh_token_validity = 30 # 30 days

  token_validity_units {
    access_token  = "hours"
    id_token      = "hours"
    refresh_token = "days"
  }

  # Security
  prevent_user_existence_errors = "ENABLED"
  
  explicit_auth_flows = [
    "ALLOW_USER_PASSWORD_AUTH",
    "ALLOW_REFRESH_TOKEN_AUTH",
    "ALLOW_USER_SRP_AUTH"
  ]

  read_attributes = [
    "email",
    "email_verified",
    "given_name",
    "family_name"
  ]

  write_attributes = [
    "email",
    "given_name", 
    "family_name"
  ]
}

# Example SAML Identity Provider (placeholder - disabled by default)
# Uncomment and configure with real SAML metadata URL when ready
# resource "aws_cognito_identity_provider" "saml_example" {
#   user_pool_id  = aws_cognito_user_pool.main.id
#   provider_name = var.saml_provider_name
#   provider_type = "SAML"

#   attribute_mapping = {
#     email       = "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress"
#     given_name  = "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/givenname"
#     family_name = "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/surname"
#   }

#   provider_details = {
#     MetadataURL                = "https://your-actual-idp.com/saml/metadata"
#     SLORedirectBindingURI     = "https://your-actual-idp.com/saml/slo"
#     SSORedirectBindingURI     = "https://your-actual-idp.com/saml/sso"
#   }
# }

# Cognito Identity Pool
resource "aws_cognito_identity_pool" "main" {
  identity_pool_name               = "${local.name_prefix}-identity-pool"
  allow_unauthenticated_identities = false

  cognito_identity_providers {
    client_id               = aws_cognito_user_pool_client.web_client.id
    provider_name           = aws_cognito_user_pool.main.endpoint
    server_side_token_check = false
  }

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-identity-pool"
  })
}

# IAM roles for Cognito Identity Pool
resource "aws_iam_role" "cognito_authenticated" {
  name = "${local.name_prefix}-cognito-authenticated-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Federated = "cognito-identity.amazonaws.com"
        }
        Action = "sts:AssumeRoleWithWebIdentity"
        Condition = {
          StringEquals = {
            "cognito-identity.amazonaws.com:aud" = aws_cognito_identity_pool.main.id
          }
          "ForAnyValue:StringLike" = {
            "cognito-identity.amazonaws.com:amr" = "authenticated"
          }
        }
      }
    ]
  })

  tags = local.common_tags
}

resource "aws_iam_role_policy" "cognito_authenticated" {
  name = "${local.name_prefix}-cognito-authenticated-policy"
  role = aws_iam_role.cognito_authenticated.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "mobileanalytics:PutEvents",
          "cognito-sync:*",
          "cognito-identity:*"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject"
        ]
        Resource = [
          "${aws_s3_bucket.pdf_originals.arn}/uploads/$${cognito-identity.amazonaws.com:sub}/*",
          "${aws_s3_bucket.pdf_derivatives.arn}/downloads/$${cognito-identity.amazonaws.com:sub}/*"
        ]
      }
    ]
  })
}

# Identity pool role attachment
resource "aws_cognito_identity_pool_roles_attachment" "main" {
  identity_pool_id = aws_cognito_identity_pool.main.id

  roles = {
    authenticated = aws_iam_role.cognito_authenticated.arn
  }

  role_mapping {
    identity_provider         = "${aws_cognito_user_pool.main.endpoint}:${aws_cognito_user_pool_client.web_client.id}"
    ambiguous_role_resolution = "AuthenticatedRole"
    type                      = "Token"
  }
}