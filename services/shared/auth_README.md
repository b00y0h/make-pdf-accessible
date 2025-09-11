# Unified JWT Authentication for PDF Accessibility Platform

This module provides unified BetterAuth JWT validation that can be shared across all FastAPI microservices in the PDF accessibility platform.

## Overview

The authentication system uses BetterAuth JWT tokens with a shared secret for validation. All microservices use the same authentication logic to ensure consistency and security across the platform.

## Architecture

- **Dashboard**: Generates BetterAuth JWT tokens for authenticated users
- **API Service**: Validates session cookies from BetterAuth
- **Worker Service**: Validates JWT tokens for background job authentication
- **Microservices**: Use shared authentication module for endpoint protection

## Usage

### Setup

1. **Install Dependencies**: Add to your service's `requirements.txt`:

   ```
   python-jose[cryptography]>=3.3.0
   fastapi>=0.100.0
   ```

2. **Environment Variables**: Configure these environment variables:

   ```bash
   API_JWT_SECRET=your-secret-key-here
   JWT_ALGORITHM=HS256
   JWT_ISSUER=accesspdf-dashboard
   JWT_AUDIENCE=accesspdf-api
   ```

3. **Import the Module**: Add shared services to your Python path:
   ```python
   import sys
   import os
   sys.path.append(os.path.join(os.path.dirname(__file__), '../../shared'))
   from auth import get_current_user, require_admin, UserInfo
   ```

### Basic Authentication

Protect endpoints with authentication:

```python
from fastapi import FastAPI, Depends
from auth import UserInfo, get_current_user

@app.get("/protected")
def protected_endpoint(current_user: UserInfo = Depends(get_current_user)):
    return {
        "message": "This is protected",
        "user_id": current_user.sub,
        "user_role": current_user.role
    }
```

### Role-Based Access Control

Require specific roles:

```python
from auth import require_admin, require_user_or_admin

@app.delete("/admin-only")
def admin_only_endpoint(current_user: UserInfo = Depends(require_admin)):
    return {"message": "Admin action completed"}

@app.get("/user-or-admin")
def user_admin_endpoint(current_user: UserInfo = Depends(require_user_or_admin)):
    return {"data": "sensitive information"}
```

### Optional Authentication

For endpoints that work with or without authentication:

```python
from auth import optional_auth

@app.get("/public-with-optional-auth")
def optional_auth_endpoint(current_user: UserInfo = Depends(optional_auth)):
    if current_user:
        return {"message": f"Hello {current_user.name}!"}
    return {"message": "Hello anonymous user!"}
```

### Custom Role Requirements

Create custom role dependencies:

```python
from auth import require_roles

# Require either editor or admin role
require_editor_or_admin = require_roles(["editor", "admin"])

@app.put("/edit")
def edit_endpoint(current_user: UserInfo = Depends(require_editor_or_admin)):
    return {"message": "Edit operation completed"}
```

## Available Dependencies

### Core Dependencies

- `get_current_user`: Requires valid JWT token, returns UserInfo
- `get_admin_user`: Requires valid JWT token + admin role, returns UserInfo
- `optional_auth`: Optional authentication, returns UserInfo or None

### Role-Based Dependencies

- `require_admin`: Requires admin role
- `require_viewer_or_admin`: Requires viewer or admin role
- `require_user_or_admin`: Requires user or admin role
- `require_roles(roles)`: Factory for custom role requirements

## UserInfo Object

The `UserInfo` object contains user information extracted from the JWT token:

```python
class UserInfo:
    sub: str              # User ID
    email: str | None     # User email
    name: str | None      # User display name
    role: str             # User role (default: "viewer")
    org_id: str | None    # Organization/tenant ID
    token_type: str       # Always "better_auth"

    # Helper methods
    def has_role(self, role: str) -> bool
    def is_admin(self) -> bool
    def can_access_resource(self, resource_user_id: str) -> bool
```

## Error Handling

The authentication module raises FastAPI HTTPExceptions:

- **401 Unauthorized**: Invalid or missing JWT token
- **403 Forbidden**: Valid token but insufficient permissions

These are automatically handled by FastAPI and return appropriate HTTP responses.

## Security Features

1. **JWT Signature Validation**: All tokens are cryptographically verified
2. **Expiration Checking**: Expired tokens are rejected
3. **Audience/Issuer Validation**: Tokens must be issued for this platform
4. **Role-Based Access**: Fine-grained permission control
5. **Shared Secret**: Consistent validation across all services

## Migration from Cognito

This unified authentication system replaces the previous AWS Cognito implementation:

- **Before**: Each service had its own Cognito JWT validation
- **After**: All services use the same BetterAuth JWT validation
- **Benefits**: Simplified authentication, consistent user experience, reduced complexity

## Example Implementation

See the following services for complete implementation examples:

- `services/functions/validator/main.py`: Basic authentication with admin endpoints
- `services/functions/tagger/main.py`: Mixed public/private endpoints with optional auth
- `services/functions/exporter/main.py`: Document ownership and role-based downloads

## Testing

When testing authenticated endpoints, include a valid JWT token in the Authorization header:

```bash
curl -H "Authorization: Bearer YOUR_JWT_TOKEN" \
     -X GET http://localhost:8000/protected
```

## Troubleshooting

### Common Issues

1. **"JWT secret not configured"**: Set the `API_JWT_SECRET` environment variable
2. **"Token validation failed"**: Check that the JWT was issued by the correct service
3. **"403 Forbidden"**: User has valid token but lacks required role
4. **Import errors**: Ensure the shared services directory is in your Python path

### Debug Mode

Enable detailed logging by setting log level to DEBUG in your service configuration.
