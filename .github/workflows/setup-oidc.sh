#!/bin/bash

# GitHub Actions OIDC Setup Script
# This script automates the setup of AWS IAM roles and GitHub OIDC integration

set -e

# Configuration
GITHUB_ORG="${GITHUB_ORG:-your-org}"
GITHUB_REPO="${GITHUB_REPO:-your-repo}"
AWS_ACCOUNT_ID="${AWS_ACCOUNT_ID:-123456789012}"
AWS_REGION="${AWS_REGION:-us-east-1}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."

    # Check AWS CLI
    if ! command -v aws &> /dev/null; then
        log_error "AWS CLI is not installed. Please install it first."
        exit 1
    fi

    # Check GitHub CLI
    if ! command -v gh &> /dev/null; then
        log_error "GitHub CLI is not installed. Please install it first."
        exit 1
    fi

    # Check AWS credentials
    if ! aws sts get-caller-identity &> /dev/null; then
        log_error "AWS credentials not configured. Please run 'aws configure' first."
        exit 1
    fi

    # Check GitHub authentication
    if ! gh auth status &> /dev/null; then
        log_error "GitHub CLI not authenticated. Please run 'gh auth login' first."
        exit 1
    fi

    log_info "Prerequisites check passed!"
}

# Create OIDC provider
create_oidc_provider() {
    log_info "Creating GitHub OIDC provider..."

    # Check if provider already exists
    if aws iam list-open-id-connect-providers --query 'OpenIDConnectProviderList[?contains(Arn, `token.actions.githubusercontent.com`)]' --output text | grep -q "token.actions.githubusercontent.com"; then
        log_warn "OIDC provider already exists, skipping creation."
        return 0
    fi

    aws iam create-openid-connect-provider \
        --url https://token.actions.githubusercontent.com \
        --client-id-list sts.amazonaws.com \
        --thumbprint-list 6938fd4d98bab03faadb97b34396831e3780aea1 \
        --tags Key=Purpose,Value=GitHubActions Key=Repository,Value="${GITHUB_ORG}/${GITHUB_REPO}"

    log_info "OIDC provider created successfully!"
}

# Create IAM role
create_iam_role() {
    local role_name=$1
    local policy_file=$2
    local trust_policy_file=$3

    log_info "Creating IAM role: $role_name"

    # Check if role already exists
    if aws iam get-role --role-name "$role_name" &> /dev/null; then
        log_warn "Role $role_name already exists, updating trust policy..."
        aws iam update-assume-role-policy --role-name "$role_name" --policy-document "file://$trust_policy_file"
    else
        # Create role
        aws iam create-role \
            --role-name "$role_name" \
            --assume-role-policy-document "file://$trust_policy_file" \
            --tags Key=Purpose,Value=GitHubActions Key=Repository,Value="${GITHUB_ORG}/${GITHUB_REPO}"
    fi

    # Attach policy
    if [ -f "$policy_file" ]; then
        aws iam put-role-policy \
            --role-name "$role_name" \
            --policy-name "${role_name}Policy" \
            --policy-document "file://$policy_file"
        log_info "Policy attached to role $role_name"
    else
        log_warn "Policy file $policy_file not found, skipping policy attachment"
    fi
}

# Generate trust policy
generate_trust_policy() {
    local role_name=$1
    local branches=$2
    local environments=$3

    cat > "/tmp/${role_name}-trust-policy.json" << EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Federated": "arn:aws:iam::${AWS_ACCOUNT_ID}:oidc-provider/token.actions.githubusercontent.com"
      },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringEquals": {
          "token.actions.githubusercontent.com:aud": "sts.amazonaws.com"
        },
        "StringLike": {
          "token.actions.githubusercontent.com:sub": [
$(echo "$branches" | sed 's/^/            "repo:'"${GITHUB_ORG}/${GITHUB_REPO}"':ref:refs\/heads\//' | sed 's/$/",/')
$(echo "$branches" | sed 's/^/            "repo:'"${GITHUB_ORG}/${GITHUB_REPO}"':ref:refs\/tags\//' | sed 's/$/",/' | sed '$s/,$//')
          ]
        }
      }
    }
  ]
}
EOF

    echo "/tmp/${role_name}-trust-policy.json"
}

# Setup infrastructure role
setup_infrastructure_role() {
    log_info "Setting up Infrastructure deployment role..."

    local trust_policy_file
    trust_policy_file=$(generate_trust_policy "GitHubActions-Infrastructure" "main" "production")

    create_iam_role "GitHubActions-Infrastructure" \
        ".github/workflows/policies/infrastructure-policy.json" \
        "$trust_policy_file"
}

# Setup Lambda deployment role
setup_lambda_role() {
    log_info "Setting up Lambda deployment role..."

    local trust_policy_file
    trust_policy_file=$(generate_trust_policy "GitHubActions-Lambda" "main\n*" "production")

    create_iam_role "GitHubActions-Lambda" \
        ".github/workflows/policies/lambda-deployment-policy.json" \
        "$trust_policy_file"
}

# Setup Web deployment role
setup_web_role() {
    log_info "Setting up Web deployment role..."

    local trust_policy_file
    trust_policy_file=$(generate_trust_policy "GitHubActions-Web" "main" "production")

    create_iam_role "GitHubActions-Web" \
        ".github/workflows/policies/web-deployment-policy.json" \
        "$trust_policy_file"
}

# Setup API deployment role
setup_api_role() {
    log_info "Setting up API deployment role..."

    local trust_policy_file
    trust_policy_file=$(generate_trust_policy "GitHubActions-API" "main" "production")

    create_iam_role "GitHubActions-API" \
        ".github/workflows/policies/api-deployment-policy.json" \
        "$trust_policy_file"
}

# Configure GitHub secrets
configure_github_secrets() {
    log_info "Configuring GitHub secrets..."

    # AWS Configuration
    gh secret set AWS_ACCOUNT_ID --body "$AWS_ACCOUNT_ID"
    gh secret set AWS_REGION --body "$AWS_REGION"

    # IAM Role ARNs
    gh secret set AWS_ROLE_ARN_INFRA --body "arn:aws:iam::${AWS_ACCOUNT_ID}:role/GitHubActions-Infrastructure"
    gh secret set AWS_ROLE_ARN_LAMBDA --body "arn:aws:iam::${AWS_ACCOUNT_ID}:role/GitHubActions-Lambda"
    gh secret set AWS_ROLE_ARN_WEB --body "arn:aws:iam::${AWS_ACCOUNT_ID}:role/GitHubActions-Web"
    gh secret set AWS_ROLE_ARN_API --body "arn:aws:iam::${AWS_ACCOUNT_ID}:role/GitHubActions-API"

    # Infrastructure secrets
    gh secret set TERRAFORM_BACKEND_BUCKET --body "pdf-accessibility-terraform-state"
    gh secret set ECR_REGISTRY --body "${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"

    # Web deployment secrets (you'll need to update these with actual values)
    gh secret set S3_BUCKET_WEB_PROD --body "pdf-accessibility-prod-web"
    gh secret set S3_BUCKET_WEB_DEV --body "pdf-accessibility-dev-web"
    gh secret set CLOUDFRONT_DISTRIBUTION_ID_PROD --body "E1234567890123"
    gh secret set CLOUDFRONT_DISTRIBUTION_ID_DEV --body "E0987654321098"

    log_info "GitHub secrets configured successfully!"
    log_warn "Please update CloudFront distribution IDs and S3 bucket names with actual values."
}

# Verify setup
verify_setup() {
    log_info "Verifying setup..."

    # Check OIDC provider
    if aws iam list-open-id-connect-providers --query 'OpenIDConnectProviderList[?contains(Arn, `token.actions.githubusercontent.com`)]' --output text | grep -q "token.actions.githubusercontent.com"; then
        log_info "✓ OIDC provider exists"
    else
        log_error "✗ OIDC provider not found"
    fi

    # Check IAM roles
    local roles=("GitHubActions-Infrastructure" "GitHubActions-Lambda" "GitHubActions-Web" "GitHubActions-API")
    for role in "${roles[@]}"; do
        if aws iam get-role --role-name "$role" &> /dev/null; then
            log_info "✓ Role $role exists"
        else
            log_error "✗ Role $role not found"
        fi
    done

    # Check GitHub secrets
    local secrets=("AWS_ACCOUNT_ID" "AWS_REGION" "AWS_ROLE_ARN_INFRA" "AWS_ROLE_ARN_LAMBDA" "AWS_ROLE_ARN_WEB" "AWS_ROLE_ARN_API")
    for secret in "${secrets[@]}"; do
        if gh secret list | grep -q "$secret"; then
            log_info "✓ Secret $secret configured"
        else
            log_error "✗ Secret $secret not found"
        fi
    done
}

# Create test workflow
create_test_workflow() {
    log_info "Creating test workflow..."

    cat > ".github/workflows/test-oidc.yml" << 'EOF'
name: Test OIDC Authentication
on:
  workflow_dispatch:

jobs:
  test-oidc:
    runs-on: ubuntu-latest
    permissions:
      id-token: write
      contents: read

    steps:
      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: ${{ secrets.AWS_ROLE_ARN_INFRA }}
          aws-region: ${{ secrets.AWS_REGION }}

      - name: Test AWS access
        run: |
          echo "Testing AWS access..."
          aws sts get-caller-identity
          echo "✓ OIDC authentication successful!"
EOF

    log_info "Test workflow created at .github/workflows/test-oidc.yml"
    log_info "Run 'gh workflow run test-oidc.yml' to test the setup"
}

# Main execution
main() {
    log_info "Starting GitHub Actions OIDC setup..."

    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --github-org)
                GITHUB_ORG="$2"
                shift 2
                ;;
            --github-repo)
                GITHUB_REPO="$2"
                shift 2
                ;;
            --aws-account-id)
                AWS_ACCOUNT_ID="$2"
                shift 2
                ;;
            --aws-region)
                AWS_REGION="$2"
                shift 2
                ;;
            --help)
                echo "Usage: $0 [options]"
                echo "Options:"
                echo "  --github-org ORG        GitHub organization name"
                echo "  --github-repo REPO      GitHub repository name"
                echo "  --aws-account-id ID     AWS account ID"
                echo "  --aws-region REGION     AWS region"
                echo "  --help                  Show this help message"
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                exit 1
                ;;
        esac
    done

    log_info "Configuration:"
    log_info "  GitHub Org: $GITHUB_ORG"
    log_info "  GitHub Repo: $GITHUB_REPO"
    log_info "  AWS Account ID: $AWS_ACCOUNT_ID"
    log_info "  AWS Region: $AWS_REGION"

    check_prerequisites
    create_oidc_provider
    setup_infrastructure_role
    setup_lambda_role
    setup_web_role
    setup_api_role
    configure_github_secrets
    verify_setup
    create_test_workflow

    log_info "Setup completed successfully!"
    log_info "Next steps:"
    log_info "1. Update CloudFront distribution IDs in GitHub secrets"
    log_info "2. Update S3 bucket names in GitHub secrets"
    log_info "3. Run the test workflow: gh workflow run test-oidc.yml"
    log_info "4. Review and customize IAM policies as needed"
}

# Run main function
main "$@"
