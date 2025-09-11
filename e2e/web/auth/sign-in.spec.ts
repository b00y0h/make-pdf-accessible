import { test, expect } from '@playwright/test';
import {
  TEST_USERS,
  signInWebUser,
  signOut,
  clearAuthState,
} from '../../shared/auth';

test.describe('Web App - Authentication', () => {
  test.beforeEach(async ({ page }) => {
    // Clear any existing auth state
    await clearAuthState(page);
  });

  test('user can sign in with valid credentials', async ({ page }) => {
    const user = TEST_USERS.user;

    // Go to sign in page
    await page.goto('/sign-in');

    // Verify sign in form is visible
    await expect(page.locator('h1:has-text("Sign In")')).toBeVisible();
    await expect(page.locator('[name="email"]')).toBeVisible();
    await expect(page.locator('[name="password"]')).toBeVisible();

    // Fill in credentials
    await page.fill('[name="email"]', user.email);
    await page.fill('[name="password"]', user.password);

    // Submit form
    await page.click('button[type="submit"]');

    // Should redirect to home/dashboard
    await page.waitForURL(/\/(dashboard|home|\/)$/);

    // Verify user is signed in
    await expect(page.locator('text="Welcome"')).toBeVisible();

    // Check for user-specific content
    const userIndicators = [
      `text="${user.name}"`,
      'button:has-text("Sign Out")',
      '[data-testid="user-menu"]',
    ];

    let foundIndicator = false;
    for (const indicator of userIndicators) {
      if (await page.locator(indicator).isVisible({ timeout: 2000 })) {
        foundIndicator = true;
        break;
      }
    }
    expect(foundIndicator).toBeTruthy();
  });

  test('user cannot sign in with invalid credentials', async ({ page }) => {
    await page.goto('/sign-in');

    // Try with invalid email
    await page.fill('[name="email"]', 'invalid@example.com');
    await page.fill('[name="password"]', 'wrongpassword');

    await page.click('button[type="submit"]');

    // Should show error and stay on sign in page
    await expect(page.locator('text="Invalid credentials"')).toBeVisible({
      timeout: 5000,
    });
    await expect(page).toHaveURL(/\/sign-in/);
  });

  test('user can sign out', async ({ page }) => {
    const user = TEST_USERS.user;

    // First sign in
    await signInWebUser(page, user);

    // Then sign out
    await signOut(page);

    // Should be redirected to sign in page
    await expect(page.locator('text="Sign In"')).toBeVisible();
    await expect(page).toHaveURL(/\/(sign-in|\/)$/);
  });

  test('redirects to sign in when accessing protected routes while unauthenticated', async ({
    page,
  }) => {
    // Try to access a protected route
    await page.goto('/dashboard');

    // Should redirect to sign in
    await page.waitForURL(/\/sign-in/);
    await expect(page.locator('text="Sign In"')).toBeVisible();
  });

  test('remembers intended destination after sign in', async ({ page }) => {
    const user = TEST_USERS.user;

    // Try to access protected route
    await page.goto('/upload');

    // Should redirect to sign in with callback URL
    await page.waitForURL(/\/sign-in.*callbackUrl/);

    // Sign in
    await page.fill('[name="email"]', user.email);
    await page.fill('[name="password"]', user.password);
    await page.click('button[type="submit"]');

    // Should redirect back to intended page
    await page.waitForURL(/\/upload/);
    await expect(page.locator('h1:has-text("Upload")')).toBeVisible();
  });

  test('form validation works correctly', async ({ page }) => {
    await page.goto('/sign-in');

    // Try submitting empty form
    await page.click('button[type="submit"]');

    // Should show validation errors
    await expect(page.locator('text="Email is required"')).toBeVisible();
    await expect(page.locator('text="Password is required"')).toBeVisible();

    // Try invalid email format
    await page.fill('[name="email"]', 'invalid-email');
    await page.click('button[type="submit"]');

    await expect(page.locator('text="Invalid email format"')).toBeVisible();
  });

  test('handles loading states correctly', async ({ page }) => {
    await page.goto('/sign-in');

    // Fill in credentials
    await page.fill('[name="email"]', TEST_USERS.user.email);
    await page.fill('[name="password"]', TEST_USERS.user.password);

    // Click submit and check for loading state
    await page.click('button[type="submit"]');

    // Should show loading indicator briefly
    await expect(page.locator('button:has-text("Signing in...")')).toBeVisible({
      timeout: 2000,
    });
  });
});
