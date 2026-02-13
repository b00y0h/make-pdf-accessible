# Phase: Security Hardening

**Scope**: Fix critical and high security issues identified in CONCERNS.md
**Source**: `.planning/codebase/CONCERNS.md`

---

## Overview

This phase addresses the security vulnerabilities in the PDF accessibility API that could expose the system to attacks or credential leaks in production deployments.

### Issues to Fix

1. **Critical: Hardcoded AWS Credentials** - `config.py` lines 19-20
2. **Critical: Hardcoded JWT Secret** - `config.py` line 136
3. **High: Hardcoded LocalStack Endpoints** - `config.py` line 21, `documents.py` line 949
4. **High: Hardcoded S3 Credentials in Demo Endpoint** - `documents.py` lines 950-951

---

## Prompt 1: Remove Default AWS Credentials

**File**: `services/api/app/config.py`

### Context
AWS access key and secret have insecure defaults of "test" which could accidentally be used in production if environment variables are not set.

### Task
1. Change `aws_access_key_id` field to have NO default value (required in production)
2. Change `aws_secret_access_key` field to have NO default value (required in production)
3. Keep `Optional` type annotation but change Field to require explicit setting
4. Add a validator that raises an error if these are not set when `app_env != "development"`

### Expected Changes
```python
# Before
aws_access_key_id: str = Field("test", env="AWS_ACCESS_KEY_ID")
aws_secret_access_key: str = Field("test", env="AWS_SECRET_ACCESS_KEY")

# After
aws_access_key_id: Optional[str] = Field(None, env="AWS_ACCESS_KEY_ID")
aws_secret_access_key: Optional[str] = Field(None, env="AWS_SECRET_ACCESS_KEY")

# Plus validator
@field_validator("aws_access_key_id", "aws_secret_access_key", mode="after")
@classmethod
def validate_aws_credentials(cls, v, info):
    # Allow None only in development
    if v is None:
        # Check app_env from environment directly since we're in validation
        import os
        if os.getenv("APP_ENV", "development") != "development":
            raise ValueError(f"{info.field_name} is required in non-development environments")
    return v
```

### Verification
- [ ] Running `APP_ENV=production python -c "from services.api.app.config import settings"` without AWS creds fails
- [ ] Running with `APP_ENV=development` succeeds (LocalStack uses defaults)
- [ ] Running with proper AWS creds set succeeds

---

## Prompt 2: Secure JWT Secret Configuration

**File**: `services/api/app/config.py`

### Context
JWT secret has an obvious placeholder default that could be used in production, enabling token forgery.

### Task
1. Remove the default value from `api_jwt_secret`
2. Add a validator that rejects placeholder values like "change-in-production", "your-secret", etc.
3. Require minimum 32-character secret length in non-development environments

### Expected Changes
```python
# Before
api_jwt_secret: str = Field(
    "your-secret-key-here-change-in-production", env="API_JWT_SECRET"
)

# After
api_jwt_secret: Optional[str] = Field(None, env="API_JWT_SECRET")

# Plus validator
@field_validator("api_jwt_secret", mode="after")
@classmethod
def validate_jwt_secret(cls, v):
    import os
    app_env = os.getenv("APP_ENV", "development")

    if app_env != "development":
        if v is None:
            raise ValueError("API_JWT_SECRET is required in non-development environments")

        # Reject obvious placeholder values
        insecure_patterns = ["change-in-production", "your-secret", "changeme", "secret"]
        if any(pattern in v.lower() for pattern in insecure_patterns):
            raise ValueError("API_JWT_SECRET contains insecure placeholder value")

        # Require minimum length
        if len(v) < 32:
            raise ValueError("API_JWT_SECRET must be at least 32 characters in production")

    return v
```

### Verification
- [ ] Placeholder secret rejected in production mode
- [ ] Short secrets rejected in production mode
- [ ] Valid secrets accepted
- [ ] Development mode allows any/no value

---

## Prompt 3: Environment-Based Endpoint Configuration

**Files**: `services/api/app/config.py`, `services/api/app/routes/documents.py`

### Context
LocalStack endpoint hardcoded in multiple places. Should use config-driven endpoint that defaults to None (use real AWS) in production.

### Task

#### Part A: config.py
1. Change `aws_endpoint_url` default from `"http://localstack:4566"` to `None`
2. Add validator to only allow endpoint URL in development environment

```python
# Before
aws_endpoint_url: Optional[str] = Field("http://localstack:4566", env="AWS_ENDPOINT_URL")

# After
aws_endpoint_url: Optional[str] = Field(None, env="AWS_ENDPOINT_URL")

@field_validator("aws_endpoint_url", mode="after")
@classmethod
def validate_endpoint_url(cls, v):
    import os
    app_env = os.getenv("APP_ENV", "development")

    if v is not None and app_env != "development":
        if "localhost" in v or "localstack" in v:
            raise ValueError("LocalStack/localhost endpoint not allowed in non-development environments")
    return v
```

#### Part B: documents.py (around line 947-954)
1. Ensure `settings` import exists at module level (add if missing: `from ..config import settings`)
2. Replace hardcoded S3 client creation with settings-based configuration
3. Remove hardcoded `'test'/'test'` credentials

```python
# Before
s3_client = boto3.client(
    's3',
    endpoint_url='http://localhost:4566',
    aws_access_key_id='test',
    aws_secret_access_key='test',
    region_name='us-east-1',
    config=s3_config
)

# After
from ..config import settings

s3_client_kwargs = {
    'region_name': settings.aws_region,
    'config': s3_config
}
if settings.aws_endpoint_url:
    s3_client_kwargs['endpoint_url'] = settings.aws_endpoint_url
if settings.aws_access_key_id:
    s3_client_kwargs['aws_access_key_id'] = settings.aws_access_key_id
if settings.aws_secret_access_key:
    s3_client_kwargs['aws_secret_access_key'] = settings.aws_secret_access_key

s3_client = boto3.client('s3', **s3_client_kwargs)
```

Also update hardcoded bucket name on line 960:
```python
# Before
'Bucket': 'pdf-accessibility-dev-pdf-originals',

# After
'Bucket': settings.pdf_originals_bucket,
```

### Verification
- [ ] Production mode doesn't use LocalStack endpoint
- [ ] Development mode works with LocalStack
- [ ] No hardcoded credentials in documents.py

---

## Prompt 4: Add Startup Validation

**File**: `services/api/app/main.py`

### Context
The application should fail fast at startup if critical security configuration is missing, rather than failing at runtime when a request comes in.

### Task
1. Add configuration validation in the `lifespan` context manager
2. Check all security-critical settings at startup
3. Log what's being validated and provide clear error messages

### Expected Changes
```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context manager"""
    # Startup
    logger.info("Starting PDF Accessibility API")

    # Validate critical configuration
    _validate_startup_configuration()

    yield
    # Shutdown
    logger.info("Shutting down PDF Accessibility API")


def _validate_startup_configuration():
    """Validate critical configuration at startup"""
    import os

    app_env = settings.app_env
    logger.info(f"Validating configuration for environment: {app_env}")

    if app_env != "development":
        errors = []

        # AWS credentials
        if not settings.aws_access_key_id:
            errors.append("AWS_ACCESS_KEY_ID is required")
        if not settings.aws_secret_access_key:
            errors.append("AWS_SECRET_ACCESS_KEY is required")

        # JWT secret
        if not settings.api_jwt_secret:
            errors.append("API_JWT_SECRET is required")
        elif len(settings.api_jwt_secret) < 32:
            errors.append("API_JWT_SECRET must be at least 32 characters")

        # Endpoint URL
        if settings.aws_endpoint_url and ("localhost" in settings.aws_endpoint_url or "localstack" in settings.aws_endpoint_url):
            errors.append("LocalStack endpoint not allowed in production")

        if errors:
            error_msg = "Configuration validation failed:\n" + "\n".join(f"  - {e}" for e in errors)
            logger.error(error_msg)
            raise RuntimeError(error_msg)

    logger.info("Configuration validation passed")
```

### Verification
- [ ] App fails to start in production mode with missing config
- [ ] App starts successfully in development mode
- [ ] Clear error messages identify which config is missing

---

## Prompt 5: Add Tests for Security Configuration

**File**: `tests/unit/test_config_security.py` (new file)

### Context
Ensure security validation behavior is tested and doesn't regress.

### Task
Create unit tests for:
1. AWS credential validation
2. JWT secret validation
3. Endpoint URL validation
4. Startup configuration validation

### Expected Test Structure
```python
"""Tests for security configuration validation"""
import os
import pytest
from unittest.mock import patch


class TestAWSCredentialValidation:
    """Test AWS credential security validation"""

    def test_production_requires_aws_credentials(self):
        """Production environment should require AWS credentials"""
        # ...

    def test_development_allows_missing_credentials(self):
        """Development environment should allow missing credentials"""
        # ...


class TestJWTSecretValidation:
    """Test JWT secret security validation"""

    def test_rejects_placeholder_secrets(self):
        """Should reject obvious placeholder secrets"""
        # ...

    def test_requires_minimum_length(self):
        """Should require minimum 32 character secret"""
        # ...


class TestEndpointValidation:
    """Test endpoint URL security validation"""

    def test_rejects_localstack_in_production(self):
        """Should reject LocalStack endpoint in production"""
        # ...


class TestStartupValidation:
    """Test startup configuration validation"""

    def test_fails_fast_with_invalid_config(self):
        """Should fail at startup with invalid production config"""
        # ...
```

### Verification
- [ ] All tests pass
- [ ] Tests cover all security validators
- [ ] Tests verify both positive and negative cases

---

## Execution Order

1. **Prompt 1** - AWS credentials (foundational change)
2. **Prompt 2** - JWT secret (independent change)
3. **Prompt 3** - Endpoint configuration (depends on Prompt 1 for credential handling)
4. **Prompt 4** - Startup validation (depends on all previous changes)
5. **Prompt 5** - Tests (verifies all changes)

## Rollback Plan

If issues occur:
1. Revert config.py changes first (most impactful)
2. Keep tests even if reverting implementation (documents expected behavior)
3. For partial rollback, can set `APP_ENV=development` as temporary workaround

## Definition of Done

- [ ] All security validators implemented
- [ ] No hardcoded credentials in codebase (run `grep -r "test.*test" services/` to verify)
- [ ] Startup validation catches misconfigurations
- [ ] Tests pass for all security features
- [ ] Manual verification in development mode
- [ ] Security audit: no passwords, secrets, or credentials in code
- [ ] Code review completed
