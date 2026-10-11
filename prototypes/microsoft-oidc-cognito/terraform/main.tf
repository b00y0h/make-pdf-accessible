# ADR-0007 prototype 2: Microsoft 365 sign-in through Cognito, one identity provider per customer
# organization. It adds to the Shibboleth prototype's throwaway pool (read from that prototype's
# state), so apply prototypes/shibboleth-cognito/terraform first.
#
# Nothing is created until microsoft_tenants and entra_client_id are set (see ../README.md). The
# app registration's client secret is read from AWS Secrets Manager, where you store it yourself.
#
#   cd prototypes/microsoft-oidc-cognito/terraform
#   AWS_PROFILE=pdf-dev terraform init
#   AWS_PROFILE=pdf-dev terraform apply -var-file=tenants.tfvars

terraform {
  required_version = ">= 1.5"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.90"
    }
  }

  backend "s3" {
    bucket         = "pdf-accessibility-terraform-state-dev"
    key            = "prototypes/microsoft-oidc-cognito/terraform.tfstate"
    region         = "us-east-1"
    dynamodb_table = "pdf-accessibility-terraform-locks-dev"
    encrypt        = true
  }
}

provider "aws" {
  region              = "us-east-1"
  allowed_account_ids = ["403030570295"]

  default_tags {
    tags = {
      application = "accesspdf"
      component   = "prototype"
      environment = "dev"
      purpose     = "microsoft-oidc-cognito-prototype"
      managed_by  = "terraform"
      repo        = "github.com/b00y0h/make-pdf-accessible"
    }
  }
}

variable "entra_client_id" {
  description = "Application (client) ID of our multi-tenant Entra app registration"
  type        = string
  default     = ""
}

variable "entra_client_secret_name" {
  description = "Secrets Manager secret holding the app registration's client secret (plain text)"
  type        = string
  default     = "prototypes/entra-oidc/client-secret"
}

variable "microsoft_tenants" {
  description = "Customer organizations, keyed by a short provider code (Cognito usernames are <code>_<id>, capped at 128 characters)"
  type = map(object({
    tenant_id = string
    domains   = list(string)
  }))
  default = {}

  validation {
    condition     = alltrue([for code, _ in var.microsoft_tenants : can(regex("^[a-z0-9]{2,12}$", code))])
    error_message = "Provider codes must be 2 to 12 lowercase letters or digits, such as m0001."
  }
}

data "terraform_remote_state" "pool" {
  backend = "s3"
  config = {
    bucket = "pdf-accessibility-terraform-state-dev"
    key    = "prototypes/shibboleth-cognito/terraform.tfstate"
    region = "us-east-1"
  }
}

locals {
  enabled      = length(var.microsoft_tenants) > 0 && var.entra_client_id != ""
  user_pool_id = data.terraform_remote_state.pool.outputs.user_pool_id
  domain       = data.terraform_remote_state.pool.outputs.domain
  callback_url = "http://localhost:8080/callback"
}

data "aws_secretsmanager_secret_version" "client_secret" {
  count     = local.enabled ? 1 : 0
  secret_id = var.entra_client_secret_name
}

# One OIDC provider per customer organization. The issuer is that organization's own
# (login.microsoftonline.com/<tenant>/v2.0), never "common": Cognito checks the token's issuer
# against this value, and only accounts from that organization can sign in through it.
resource "aws_cognito_identity_provider" "microsoft" {
  for_each = local.enabled ? var.microsoft_tenants : {}

  user_pool_id  = local.user_pool_id
  provider_name = each.key
  provider_type = "OIDC"

  # Email-first routing: an authorize request with idp_identifier=<domain> lands here
  idp_identifiers = [for d in each.value.domains : lower(d)]

  provider_details = {
    client_id                 = var.entra_client_id
    client_secret             = data.aws_secretsmanager_secret_version.client_secret[0].secret_string
    authorize_scopes          = "openid email profile"
    oidc_issuer               = "https://login.microsoftonline.com/${each.value.tenant_id}/v2.0"
    attributes_request_method = "GET"
  }

  attribute_mapping = {
    email              = "email"
    preferred_username = "preferred_username"
    name               = "name"
  }

  lifecycle {
    # Cognito fills in the endpoints it discovers from the issuer
    ignore_changes = [provider_details["attributes_url"], provider_details["attributes_url_add_attributes"], provider_details["authorize_url"], provider_details["jwks_uri"], provider_details["token_url"]]
  }
}

resource "aws_cognito_user_pool_client" "microsoft_test_app" {
  count = local.enabled ? 1 : 0

  name         = "microsoft-prototype-test-app"
  user_pool_id = local.user_pool_id

  generate_secret                      = false
  allowed_oauth_flows_user_pool_client = true
  allowed_oauth_flows                  = ["code"]
  allowed_oauth_scopes                 = ["openid", "email", "profile"]
  callback_urls                        = [local.callback_url]
  supported_identity_providers         = [for p in aws_cognito_identity_provider.microsoft : p.provider_name]
  explicit_auth_flows                  = ["ALLOW_REFRESH_TOKEN_AUTH"]
}

output "entra_redirect_uri" {
  description = "Register this as a Web redirect URI on the Entra app registration"
  value       = "https://${local.domain}/oauth2/idpresponse"
}

output "domain" {
  value = local.domain
}

output "client_id" {
  value = local.enabled ? aws_cognito_user_pool_client.microsoft_test_app[0].id : null
}

output "callback_url" {
  value = local.callback_url
}

output "providers" {
  value = { for code, p in aws_cognito_identity_provider.microsoft : code => p.idp_identifiers }
}
