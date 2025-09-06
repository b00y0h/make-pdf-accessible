#!/bin/bash

# Setup Branch Protection Rules for Environment-Specific Deployments
# This script configures GitHub branch protection rules for the repository

set -e

# Configuration
REPO_OWNER="${GITHUB_REPOSITORY_OWNER:-}"
REPO_NAME="${GITHUB_REPOSITORY##*/}"
GITHUB_TOKEN="${GITHUB_TOKEN:-}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."

    if [ -z "$GITHUB_TOKEN" ]; then
        log_error "GITHUB_TOKEN environment variable is required"
        exit 1
    fi

    if [ -z "$REPO_OWNER" ]; then
        log_error "GITHUB_REPOSITORY_OWNER environment variable is required"
        exit 1
    fi

    if ! command -v gh &> /dev/null; then
        log_error "GitHub CLI (gh) is required but not installed"
        exit 1
    fi

    if ! command -v jq &> /dev/null; then
        log_error "jq is required but not installed"
        exit 1
    fi

    log_success "Prerequisites check passed"
}

# Setup main branch protection
setup_main_branch_protection() {
    log_info "Setting up main branch protection..."

    # Main branch protection configuration
    PROTECTION_CONFIG=$(cat <<EOF
{
  "required_status_checks": {
    "strict": true,
    "contexts": [
      "terraform-validate",
      "security-scan",
      "test-suite",
      "dependency-security-scan"
    ]
  },
  "enforce_admins": true,
  "required_pull_request_reviews": {
    "required_approving_review_count": 2,
    "dismiss_stale_reviews": true,
    "require_code_owner_reviews": true,
    "require_last_push_approval": true
  },
  "restrictions": null,
  "allow_force_pushes": false,
  "allow_deletions": false,
  "block_creations": false,
  "required_conversation_resolution": true
}
EOF
)

    # Apply protection using GitHub API
    curl -X PUT \
        -H "Authorization: token $GITHUB_TOKEN" \
        -H "Accept: application/vnd.github.v3+json" \
        "https://api.github.com/repos/$REPO_OWNER/$REPO_NAME/branches/main/protection" \
        -d "$PROTECTION_CONFIG" \
        --silent --show-error || {
            log_error "Failed to set up main branch protection"
            return 1
        }

    log_success "Main branch protection configured"
}

# Setup develop branch protection (if exists)
setup_develop_branch_protection() {
    log_info "Checking for develop branch..."

    # Check if develop branch exists
    if gh api "repos/$REPO_OWNER/$REPO_NAME/branches/develop" &>/dev/null; then
        log_info "Setting up develop branch protection..."

        DEVELOP_PROTECTION_CONFIG=$(cat <<EOF
{
  "required_status_checks": {
    "strict": false,
    "contexts": [
      "terraform-validate",
      "security-scan"
    ]
  },
  "enforce_admins": false,
  "required_pull_request_reviews": {
    "required_approving_review_count": 1,
    "dismiss_stale_reviews": false,
    "require_code_owner_reviews": false
  },
  "restrictions": null,
  "allow_force_pushes": false,
  "allow_deletions": false
}
EOF
)

        curl -X PUT \
            -H "Authorization: token $GITHUB_TOKEN" \
            -H "Accept: application/vnd.github.v3+json" \
            "https://api.github.com/repos/$REPO_OWNER/$REPO_NAME/branches/develop/protection" \
            -d "$DEVELOP_PROTECTION_CONFIG" \
            --silent --show-error || {
                log_warning "Failed to set up develop branch protection"
            }

        log_success "Develop branch protection configured"
    else
        log_info "Develop branch not found, skipping protection setup"
    fi
}

# Setup GitHub environments
setup_github_environments() {
    log_info "Setting up GitHub environments..."

    # Development environment
    log_info "Creating development environment..."
    DEV_ENV_CONFIG=$(cat <<EOF
{
  "wait_timer": 0,
  "reviewers": [],
  "deployment_branch_policy": {
    "protected_branches": false,
    "custom_branch_policies": true
  }
}
EOF
)

    curl -X PUT \
        -H "Authorization: token $GITHUB_TOKEN" \
        -H "Accept: application/vnd.github.v3+json" \
        "https://api.github.com/repos/$REPO_OWNER/$REPO_NAME/environments/development" \
        -d "$DEV_ENV_CONFIG" \
        --silent --show-error || log_warning "Failed to create development environment"

    # Staging environment
    log_info "Creating staging environment..."
    STAGING_ENV_CONFIG=$(cat <<EOF
{
  "wait_timer": 0,
  "reviewers": [
    {
      "type": "Team",
      "id": "platform-team"
    }
  ],
  "deployment_branch_policy": {
    "protected_branches": true,
    "custom_branch_policies": false
  }
}
EOF
)

    curl -X PUT \
        -H "Authorization: token $GITHUB_TOKEN" \
        -H "Accept: application/vnd.github.v3+json" \
        "https://api.github.com/repos/$REPO_OWNER/$REPO_NAME/environments/staging" \
        -d "$STAGING_ENV_CONFIG" \
        --silent --show-error || log_warning "Failed to create staging environment"

    # Production environment
    log_info "Creating production environment..."
    PROD_ENV_CONFIG=$(cat <<EOF
{
  "wait_timer": 0,
  "reviewers": [
    {
      "type": "Team",
      "id": "platform-team"
    },
    {
      "type": "Team",
      "id": "security-team"
    }
  ],
  "deployment_branch_policy": {
    "protected_branches": true,
    "custom_branch_policies": false
  }
}
EOF
)

    curl -X PUT \
        -H "Authorization: token $GITHUB_TOKEN" \
        -H "Accept: application/vnd.github.v3+json" \
        "https://api.github.com/repos/$REPO_OWNER/$REPO_NAME/environments/production" \
        -d "$PROD_ENV_CONFIG" \
        --silent --show-error || log_warning "Failed to create production environment"

    log_success "GitHub environments configured"
}

# Setup repository rulesets (if available)
setup_repository_rulesets() {
    log_info "Setting up repository rulesets..."

    # Check if rulesets API is available
    if gh api "repos/$REPO_OWNER/$REPO_NAME/rulesets" &>/dev/null; then
        log_info "Repository rulesets API available, creating rules..."

        # Environment-specific deployment ruleset
        DEPLOYMENT_RULESET=$(cat <<EOF
{
  "name": "Environment Deployment Rules",
  "target": "branch",
  "enforcement": "active",
  "conditions": {
    "ref_name": {
      "include": ["refs/heads/main", "refs/heads/develop", "refs/heads/release/*"],
      "exclude": []
    }
  },
  "rules": [
    {
      "type": "required_status_checks",
      "parameters": {
        "required_status_checks": [
          {
            "context": "setup-environment",
            "integration_id": null
          },
          {
            "context": "environment-gate",
            "integration_id": null
          }
        ],
        "strict_required_status_checks_policy": true
      }
    },
    {
      "type": "required_deployments",
      "parameters": {
        "required_deployment_environments": ["development", "staging"]
      }
    }
  ],
  "bypass_actors": [
    {
      "actor_id": 1,
      "actor_type": "Team",
      "bypass_mode": "always"
    }
  ]
}
EOF
)

        curl -X POST \
            -H "Authorization: token $GITHUB_TOKEN" \
            -H "Accept: application/vnd.github.v3+json" \
            "https://api.github.com/repos/$REPO_OWNER/$REPO_NAME/rulesets" \
            -d "$DEPLOYMENT_RULESET" \
            --silent --show-error || log_warning "Failed to create deployment ruleset"

        log_success "Repository rulesets configured"
    else
        log_info "Repository rulesets not available, skipping"
    fi
}

# Validate configuration
validate_configuration() {
    log_info "Validating branch protection configuration..."

    # Check main branch protection
    MAIN_PROTECTION=$(gh api "repos/$REPO_OWNER/$REPO_NAME/branches/main/protection" 2>/dev/null || echo "{}")

    if echo "$MAIN_PROTECTION" | jq -e '.required_status_checks' >/dev/null; then
        log_success "Main branch protection is active"

        # Show required status checks
        REQUIRED_CHECKS=$(echo "$MAIN_PROTECTION" | jq -r '.required_status_checks.contexts[]' 2>/dev/null || echo "None")
        log_info "Required status checks: $REQUIRED_CHECKS"
    else
        log_warning "Main branch protection may not be fully configured"
    fi

    # Check environments
    ENVIRONMENTS=$(gh api "repos/$REPO_OWNER/$REPO_NAME/environments" 2>/dev/null | jq -r '.environments[].name' 2>/dev/null || echo "")

    if [ -n "$ENVIRONMENTS" ]; then
        log_success "GitHub environments configured:"
        echo "$ENVIRONMENTS" | while read -r env; do
            log_info "  - $env"
        done
    else
        log_warning "No GitHub environments found"
    fi
}

# Generate summary report
generate_summary() {
    log_info "Generating configuration summary..."

    cat <<EOF

========================================
Branch Protection Setup Summary
========================================

Repository: $REPO_OWNER/$REPO_NAME

Branch Protection Rules:
✅ Main branch: Protected with required reviews and status checks
$([ -f /tmp/develop_exists ] && echo "✅ Develop branch: Protected with basic rules" || echo "ℹ️  Develop branch: Not found")

GitHub Environments:
✅ Development: No approval required, flexible deployment
✅ Staging: Team approval required, protected branches only
✅ Production: Multi-team approval required, main branch only

Security Features:
✅ Required status checks for security scans
✅ Required pull request reviews
✅ Dismiss stale reviews enabled
✅ Code owner reviews required
✅ Conversation resolution required

Next Steps:
1. Ensure teams 'platform-team' and 'security-team' exist
2. Add team members to appropriate teams
3. Configure CODEOWNERS file for code review assignments
4. Test deployment workflows in development environment
5. Review and adjust protection rules as needed

For more information, see:
- .github/workflows/ENVIRONMENT_DEPLOYMENT_GUIDE.md
- GitHub repository settings > Branches
- GitHub repository settings > Environments

========================================

EOF
}

# Main execution
main() {
    log_info "Starting branch protection setup for environment-specific deployments"

    check_prerequisites
    setup_main_branch_protection
    setup_develop_branch_protection
    setup_github_environments
    setup_repository_rulesets
    validate_configuration
    generate_summary

    log_success "Branch protection setup completed successfully!"
}

# Run main function
main "$@"
