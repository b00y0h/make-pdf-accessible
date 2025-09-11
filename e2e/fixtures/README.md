# Test Fixtures

This directory contains test files and data used in E2E tests.

## Files

- `test-document.pdf` - Sample PDF document for upload tests
- `test-document-2.pdf` - Second PDF for multiple upload tests
- `test-image.jpg` - Invalid file type for negative testing
- `large-file.pdf` - Large file for size validation testing
- `corrupted.pdf` - Corrupted PDF for error handling tests

## Usage

These files are referenced in Playwright tests for:

- File upload testing
- File validation testing
- Error handling scenarios
- Multiple file selection tests

## Creating Test Files

To generate test files:

```bash
# Create sample PDFs (requires pandoc or similar)
echo "# Test Document 1" | pandoc -o test-document.pdf

# Create test image
convert -size 100x100 xc:red test-image.jpg

# Create large file (for size testing)
dd if=/dev/zero of=large-file.pdf bs=1M count=101
```

## Security Note

Test files should be safe, non-malicious samples. Never include:

- Real user data
- Sensitive information
- Actual malicious files
- Production documents
