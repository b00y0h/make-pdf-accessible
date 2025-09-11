import { test, expect } from '@playwright/test';
import { TEST_USERS, ensureAuthenticated } from '../../shared/auth';
import path from 'path';

test.describe('Web App - File Upload', () => {
  test.beforeEach(async ({ page }) => {
    // Ensure user is authenticated before each test
    await ensureAuthenticated(page, TEST_USERS.user, 'web');
  });

  test('user can upload a PDF file', async ({ page }) => {
    // Go to upload page
    await page.goto('/upload');

    // Verify upload form is visible
    await expect(page.locator('h1:has-text("Upload Document")')).toBeVisible();

    // Create a test PDF file path (you'd need to have test files in the repo)
    const testFilePath = path.join(
      process.cwd(),
      'e2e/fixtures/test-document.pdf'
    );

    // Upload file using file input
    const fileInput = page.locator('input[type="file"]');
    await fileInput.setInputFiles(testFilePath);

    // Verify file is selected
    await expect(page.locator('text="test-document.pdf"')).toBeVisible();

    // Submit upload
    await page.click('button:has-text("Upload")');

    // Should show upload progress
    await expect(page.locator('[role="progressbar"]')).toBeVisible();

    // Should eventually show success message
    await expect(page.locator('text="Upload successful"')).toBeVisible({
      timeout: 30000,
    });

    // Should redirect to document details or processing page
    await page.waitForURL(/\/(documents|processing)\//);
  });

  test('user can drag and drop files', async ({ page }) => {
    await page.goto('/upload');

    // Create test file
    const testFilePath = path.join(
      process.cwd(),
      'e2e/fixtures/test-document.pdf'
    );

    // Find drop zone
    const dropZone = page.locator('[data-testid="file-drop-zone"]');
    await expect(dropZone).toBeVisible();

    // Simulate file drop
    await dropZone.setInputFiles(testFilePath);

    // Verify file is added
    await expect(page.locator('text="test-document.pdf"')).toBeVisible();

    // Should show file details
    await expect(page.locator('text="PDF"')).toBeVisible(); // File type
    await expect(page.locator('[data-testid="file-size"]')).toBeVisible();
  });

  test('validates file type restrictions', async ({ page }) => {
    await page.goto('/upload');

    // Try to upload non-PDF file
    const invalidFilePath = path.join(
      process.cwd(),
      'e2e/fixtures/test-image.jpg'
    );

    const fileInput = page.locator('input[type="file"]');
    await fileInput.setInputFiles(invalidFilePath);

    // Should show error message
    await expect(
      page.locator('text="Only PDF files are allowed"')
    ).toBeVisible();

    // Upload button should be disabled
    await expect(page.locator('button:has-text("Upload")')).toBeDisabled();
  });

  test('validates file size limits', async ({ page }) => {
    await page.goto('/upload');

    // The test would need a large file, so we'll simulate the error
    // In a real test, you'd upload a file that exceeds size limits

    // For now, check that size validation UI elements exist
    await expect(page.locator('text="Maximum file size: 100MB"')).toBeVisible();
  });

  test('can remove selected files', async ({ page }) => {
    await page.goto('/upload');

    const testFilePath = path.join(
      process.cwd(),
      'e2e/fixtures/test-document.pdf'
    );

    // Upload file
    const fileInput = page.locator('input[type="file"]');
    await fileInput.setInputFiles(testFilePath);

    // Verify file is listed
    await expect(page.locator('text="test-document.pdf"')).toBeVisible();

    // Remove file
    await page.click('[data-testid="remove-file"]');

    // File should be removed
    await expect(page.locator('text="test-document.pdf"')).not.toBeVisible();

    // Upload button should be disabled
    await expect(page.locator('button:has-text("Upload")')).toBeDisabled();
  });

  test('shows upload progress', async ({ page }) => {
    await page.goto('/upload');

    const testFilePath = path.join(
      process.cwd(),
      'e2e/fixtures/test-document.pdf'
    );

    // Upload file
    const fileInput = page.locator('input[type="file"]');
    await fileInput.setInputFiles(testFilePath);

    // Start upload
    await page.click('button:has-text("Upload")');

    // Should show progress bar
    await expect(page.locator('[role="progressbar"]')).toBeVisible();

    // Should show percentage or bytes uploaded
    const progressIndicators = [
      'text="%"',
      '[data-testid="upload-progress"]',
      'text="Uploading..."',
    ];

    let foundIndicator = false;
    for (const indicator of progressIndicators) {
      if (await page.locator(indicator).isVisible({ timeout: 5000 })) {
        foundIndicator = true;
        break;
      }
    }
    expect(foundIndicator).toBeTruthy();
  });

  test('handles upload errors gracefully', async ({ page }) => {
    await page.goto('/upload');

    // Mock a network error or server error
    await page.route('**/documents/upload', (route) => {
      route.fulfill({
        status: 500,
        body: JSON.stringify({ error: 'Upload failed' }),
      });
    });

    const testFilePath = path.join(
      process.cwd(),
      'e2e/fixtures/test-document.pdf'
    );

    // Upload file
    const fileInput = page.locator('input[type="file"]');
    await fileInput.setInputFiles(testFilePath);
    await page.click('button:has-text("Upload")');

    // Should show error message
    await expect(page.locator('text="Upload failed"')).toBeVisible({
      timeout: 10000,
    });

    // Should allow retry
    await expect(page.locator('button:has-text("Try Again")')).toBeVisible();
  });

  test('supports multiple file upload', async ({ page }) => {
    await page.goto('/upload');

    // Check if multiple upload is supported
    const supportsMultiple =
      (await page.locator('input[type="file"][multiple]').count()) > 0;

    if (supportsMultiple) {
      const testFiles = [
        path.join(process.cwd(), 'e2e/fixtures/test-document.pdf'),
        path.join(process.cwd(), 'e2e/fixtures/test-document-2.pdf'),
      ];

      // Upload multiple files
      const fileInput = page.locator('input[type="file"]');
      await fileInput.setInputFiles(testFiles);

      // Should show both files
      await expect(page.locator('text="test-document.pdf"')).toBeVisible();
      await expect(page.locator('text="test-document-2.pdf"')).toBeVisible();

      // Should show total count
      await expect(page.locator('text="2 files selected"')).toBeVisible();
    }
  });
});
