# Throwaway Cognito user pool for the Shibboleth prototype (ADR-0007). It uses the Essentials
# plan with no advanced security, matching the recommendation in
# docs/research/identity-options-2026-10.md. Delete it with `terraform destroy` when done.
#
#   cd prototypes/shibboleth-cognito/terraform
#   AWS_PROFILE=pdf-dev terraform init
#   AWS_PROFILE=pdf-dev terraform apply

terraform {
  required_version = ">= 1.5"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.90"
    }
  }

  # State lives in the dev bucket under its own key so the pool isn't orphaned if this checkout goes away
  backend "s3" {
    bucket         = "pdf-accessibility-terraform-state-dev"
    key            = "prototypes/shibboleth-cognito/terraform.tfstate"
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
      purpose     = "shibboleth-cognito-prototype"
      managed_by  = "terraform"
      repo        = "github.com/b00y0h/make-pdf-accessible"
    }
  }
}

locals {
  callback_url  = "http://localhost:8080/callback"
  provider_name = "TestUniversity"
}

resource "aws_cognito_user_pool" "prototype" {
  name                = "pdf-accessibility-shibboleth-prototype"
  user_pool_tier      = "ESSENTIALS"
  deletion_protection = "INACTIVE"

  # Federated users only; nobody signs up with a password here
  admin_create_user_config {
    allow_admin_create_user_only = true
  }
}

resource "aws_cognito_user_pool_domain" "prototype" {
  domain       = "pdfa-shib-proto-403030"
  user_pool_id = aws_cognito_user_pool.prototype.id
}

# The test university, configured from the metadata a campus would send us
resource "aws_cognito_identity_provider" "university" {
  user_pool_id  = aws_cognito_user_pool.prototype.id
  provider_name = local.provider_name
  provider_type = "SAML"

  provider_details = {
    MetadataFile       = file("${path.module}/../idp/metadata/idp-metadata.xml")
    IDPSignout         = "false"
    EncryptedResponses = "true" # pass 3: Cognito publishes an encryption certificate the campus encrypts to
  }

  # Shibboleth sends attributes under their OID names
  attribute_mapping = {
    email              = "urn:oid:0.9.2342.19200300.100.1.3" # mail
    preferred_username = "urn:oid:1.3.6.1.4.1.5923.1.1.1.6"  # eduPersonPrincipalName
  }

  lifecycle {
    # Cognito adds derived keys (SSO URLs, certificates) to provider_details after creation
    ignore_changes = [provider_details["ActiveEncryptionCertificate"], provider_details["SSORedirectBindingURI"], provider_details["SLORedirectBindingURI"]]
  }
}

resource "aws_cognito_user_pool_client" "test_app" {
  name         = "shibboleth-prototype-test-app"
  user_pool_id = aws_cognito_user_pool.prototype.id

  generate_secret                      = false
  allowed_oauth_flows_user_pool_client = true
  allowed_oauth_flows                  = ["code"]
  allowed_oauth_scopes                 = ["openid", "email", "profile"]
  callback_urls                        = [local.callback_url]
  supported_identity_providers         = [aws_cognito_identity_provider.university.provider_name]
  explicit_auth_flows                  = ["ALLOW_REFRESH_TOKEN_AUTH"]
}

output "user_pool_id" {
  value = aws_cognito_user_pool.prototype.id
}

output "sp_entity_id" {
  description = "Cognito's SAML service-provider entity ID, which the campus configures"
  value       = "urn:amazon:cognito:sp:${aws_cognito_user_pool.prototype.id}"
}

output "acs_url" {
  description = "Where the campus IdP posts SAML responses"
  value       = "https://${aws_cognito_user_pool_domain.prototype.domain}.auth.us-east-1.amazoncognito.com/saml2/idpresponse"
}

output "domain" {
  value = "${aws_cognito_user_pool_domain.prototype.domain}.auth.us-east-1.amazoncognito.com"
}

output "client_id" {
  value = aws_cognito_user_pool_client.test_app.id
}

output "provider_name" {
  value = aws_cognito_identity_provider.university.provider_name
}

output "callback_url" {
  value = local.callback_url
}
