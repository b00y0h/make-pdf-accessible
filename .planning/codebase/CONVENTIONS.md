# Code Conventions

## Python Style Standards

### Formatter: Black
- Line length: 88 characters
- Configured in `pyproject.toml`
- Pre-commit hook enforces formatting

### Linter: Ruff
- Target: Python 3.9+
- Rules enabled: E, W, F, I, B, C4, UP
- Per-file ignores: `__init__.py` allows F401 (unused imports for re-exports)

### Type Checker: MyPy
- Strict mode enabled
- `disallow_untyped_defs = true`
- `disallow_any_generics = true`
- All functions require type annotations

## TypeScript Style Standards

### ESLint
- TypeScript-ESLint recommended ruleset
- Prettier integration for formatting conflicts
- Next.js specific rules where applicable

### Prettier
- Print width: 80 characters
- Tab width: 2 spaces
- Trailing commas: es5
- Single quotes: true

## File Organization Patterns

### Python Modules
```
app/
├── routes/           # API endpoint handlers
│   ├── documents.py
│   ├── api_keys.py
│   └── admin.py
├── middleware/       # Request processing
├── services/         # Business logic
├── models.py         # Data models
└── main.py           # Application entry
```

### Test Files
- Python: `test_*.py` prefix
- TypeScript: `*.test.ts` or `*.test.tsx` suffix
- Located in `tests/` directory or `__tests__/` subdirectories

## Naming Conventions

### Python
- Variables/functions: `snake_case`
- Classes: `PascalCase`
- Constants: `UPPER_SNAKE_CASE`
- Files: `snake_case.py`

### TypeScript
- Variables/functions: `camelCase`
- Components/Classes: `PascalCase`
- Constants: `UPPER_SNAKE_CASE`
- Files: `kebab-case.ts` or `PascalCase.tsx` for components

## Import Conventions

### Python
```python
# Standard library
import os
from datetime import datetime

# Third-party packages
from fastapi import APIRouter
import sqlalchemy as sa

# Local imports (relative)
from .models import Document
from ..shared.auth import verify_token
```

### TypeScript
```typescript
// External packages
import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';

// Path aliases
import { Button } from '@/components/ui';
import { formatDate } from '@/lib/utils';
```

## Pre-commit Hooks

Configured in `.pre-commit-config.yaml`:

| Hook | Version | Purpose |
|------|---------|---------|
| Black | 23.7.0 | Python formatting |
| Ruff | 0.0.287 | Python linting |
| ESLint | 8.47.0 | TypeScript linting |
| Prettier | 3.0.3 | Code formatting |

## Documentation Standards

### Docstrings
- Required for public functions and classes
- Triple quotes for multi-line
- Type hints preferred over docstring types

### Comments
- Explain "why" not "what"
- Use TODO/FIXME for tracked issues
- Keep inline comments minimal

## Configuration Files

### pyproject.toml
Central Python configuration:
- Project metadata
- Black settings
- Ruff rules
- MyPy configuration

### pytest.ini
Test configuration:
- Markers: unit, integration, feature, skip_in_dev
- Test paths: `tests/`
- Async mode: auto

## Error Handling

- Use specific exception types
- HTTPException for API errors with appropriate status codes
- Log errors before re-raising
- Avoid bare `except Exception` blocks
