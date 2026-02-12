# Concerns & Technical Debt

## Security Issues

### Critical: Hardcoded Credentials

**Location**: `services/api/app/config.py`

1. **AWS Access Keys** (lines 19-20): Default to "test" - vulnerable in production
2. **JWT Secret** (line 136): "your-secret-key-here-change-in-production"
   - Should be a required environment variable with no default
   - Production deployments could accidentally use insecure default

### High: Hardcoded Endpoints

**Location**: `services/api/app/config.py`, `services/api/app/routes/documents.py`

- LocalStack endpoint hardcoded as `http://localhost:4566` and `http://localstack:4566`
- Breaks production deployments if not overridden
- Should use environment-based configuration with no development defaults

### Medium: Demo Endpoints Bypass Authentication

**Location**: `services/api/app/routes/documents.py` (lines 145-233)

- Unauthenticated demo endpoints exist
- Session-based rate limiting (5/hour) is weak
- Potential abuse vector for resource consumption
- Hardcoded S3 credentials in demo endpoint (line 950)

## Technical Debt

### Repeated Resource Creation

**Location**: `services/api/app/routes/documents.py`

- 15+ instances of creating new boto3/S3 clients per request
- Should use dependency injection with shared clients
- Impacts performance and resource usage

### Overly Broad Exception Handling

**Locations**: Multiple files

- 21+ bare `except Exception` blocks
- Masks specific errors and makes debugging difficult
- Should catch specific exception types

### Unimplemented TODOs

| Location | Issue |
|----------|-------|
| `documents.py:395` | Missing document stats from MongoDB |
| `admin.py:49` | Document stats placeholder returns zeros |
| `admin.py:310` | User deletion doesn't clean up MongoDB documents |

### Disabled Code

**Location**: `services/api/app/routes/documents.py` (lines 779-898)

- Large block of commented-out demo download functionality
- Should be removed or properly feature-flagged

## Configuration Issues

### Environment-Specific Hardcoding

- Multiple hardcoded bucket names with "dev" prefix
- CORS origins default to localhost addresses
- No validation that required secrets are set before app start

### Missing Startup Validation

- App should fail fast if critical environment variables are missing
- Currently relies on insecure defaults

## Test Coverage Gaps

### Missing Tests

- Admin user deletion doesn't delete MongoDB documents (no test coverage)
- Document stats placeholder behavior untested
- Exception handlers lack comprehensive tests
- Demo endpoints rate limiting untested

## Scalability Concerns

### Database Architecture

- SQLite used for auth database in Docker
- Shared volume dependency creates bottleneck
- Should migrate to PostgreSQL for auth in production

### Rate Limiting

- Rate limiting config exists but appears unenforced on main endpoints
- Demo endpoints could enable abuse without infrastructure-level rate limiting

## Code Quality

### Inconsistencies

- Error response formats vary across endpoints
- Multiple inline imports within route handlers
- No connection pooling for S3/boto3 clients

### Import Organization

- `aws_lambda_powertools` and `boto3` imported inline in handlers
- Should be module-level imports

## Recommendations

### Immediate Actions

1. **Remove hardcoded credentials** - Use required environment variables
2. **Add startup validation** - Fail if critical config missing
3. **Review demo endpoints** - Consider removing or adding proper auth

### Short-term Improvements

1. **Implement dependency injection** for boto3 clients
2. **Replace broad exception handlers** with specific catches
3. **Clean up commented code** - Remove or feature-flag

### Long-term Refactoring

1. **Migrate auth to PostgreSQL** for production scalability
2. **Add infrastructure rate limiting** at load balancer level
3. **Implement proper connection pooling**
4. **Complete TODO items** or create tracking issues
