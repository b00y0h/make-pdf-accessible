# Testing Strategy

## Test Frameworks

### Python
- **pytest**: 7.4.0+ - Primary test framework
- **pytest-asyncio**: 0.21.0+ - Async test support
- **pytest-cov**: 4.1.0+ - Coverage reporting

### TypeScript
- **Jest**: Next.js integration testing
- **Vitest**: Frontend unit testing
- **Playwright**: End-to-end testing

## Test Organization

```
tests/
├── unit/              # Fast, isolated tests (always run)
├── integration/       # Database/service tests (may skip in dev)
├── api/               # HTTP endpoint tests
└── conftest.py        # Shared fixtures and config
```

## Test Markers

Configured in `pytest.ini`:

| Marker | Description | When to use |
|--------|-------------|-------------|
| `unit` | Fast, isolated tests | Always run |
| `integration` | Requires services | CI, full test runs |
| `feature` | Feature-specific tests | Feature development |
| `skip_in_dev` | Skip during local dev | Slow/flaky tests |

## Running Tests

### All Tests
```bash
make test                    # Full test suite via docker-compose
make test-dev               # Development subset
```

### Python Tests
```bash
pytest tests/               # All Python tests
pytest tests/unit/ -v       # Unit tests only
pytest tests/integration/   # Integration tests
pytest -m "not integration" # Skip integration tests
```

### Coverage
```bash
pytest --cov=app --cov-fail-under=80  # With 80% threshold
```

### TypeScript Tests
```bash
pnpm -r test               # All workspace tests
pnpm --filter web test     # Web app only
pnpm --filter dashboard test  # Dashboard only
```

## Coverage Requirements

### Python
- Minimum: 80% for unit tests
- CI enforces threshold (build fails if below)
- Coverage XML reports uploaded as artifacts

### TypeScript (Dashboard)
- Lines/Functions: 90%
- Branches: 85%
- Utility modules (mom.ts, topn.ts): 95%

## Test File Naming

### Python
- Files: `test_*.py`
- Classes: `class Test*`
- Functions: `def test_*`

### TypeScript
- Files: `*.test.ts` or `*.test.tsx`
- Describe blocks for grouping
- `it()` or `test()` for assertions

## Test Patterns

### Unit Tests
```python
class TestDocumentModel:
    def test_create_document_with_valid_data(self):
        """Documents can be created with valid input."""
        doc = Document(name="test.pdf", size=1024)
        assert doc.name == "test.pdf"
```

### Integration Tests
```python
@pytest.mark.integration
class TestDocumentAPI:
    async def test_upload_document(self, client, auth_headers):
        """Documents can be uploaded via API."""
        response = await client.post("/documents", headers=auth_headers)
        assert response.status_code == 201
```

### Async Tests
```python
@pytest.mark.asyncio
async def test_async_processing():
    """Async operations complete successfully."""
    result = await process_document(doc_id)
    assert result.status == "completed"
```

## CI/CD Testing

### GitHub Actions (`api-ci.yml`)

Pipeline stages:
1. **Security scans** - Vulnerability detection
2. **Linting** - Code quality checks
3. **Unit tests** - Fast tests with coverage
4. **Integration tests** - Service tests with PostgreSQL + Redis
5. **API tests** - Endpoint validation

### Test Services in CI
- PostgreSQL 15 container
- Redis 7 container
- LocalStack for AWS services

### Test Results
- JUnit XML format output
- dorny/test-reporter for GitHub UI
- Coverage reports as artifacts

## Fixtures (conftest.py)

Common fixtures:
- `db_session` - Database session
- `client` - Test HTTP client
- `auth_headers` - Authenticated request headers
- `sample_document` - Test document fixture

## Best Practices

1. **Test behavior, not implementation**
2. **One assertion per test when possible**
3. **Use descriptive test names**
4. **Keep tests independent**
5. **Mock external services in unit tests**
6. **Use real services in integration tests**
