import { test, expect } from '@playwright/test';
import {
  TEST_USERS,
  signInDashboardUser,
  signOut,
  clearAuthState,
} from '../../shared/auth';

test.describe('Dashboard - Authentication', () => {
  test.beforeEach(async ({ page }) => {
    // Clear any existing auth state
    await clearAuthState(page);
  });

  test('admin can sign in to dashboard', async ({ page }) => {
    const admin = TEST_USERS.admin;

    // Go to dashboard sign in
    await page.goto('http://localhost:3001/sign-in');

    // Verify sign in form
    await expect(page.locator('h1:has-text("Sign In")')).toBeVisible();

    // Fill credentials
    await page.fill('[name="email"]', admin.email);
    await page.fill('[name="password"]', admin.password);

    // Submit
    await page.click('button[type="submit"]');

    // Should redirect to dashboard
    await page.waitForURL(/\/(dashboard|admin)/);

    // Verify admin interface elements
    await expect(page.locator('text="Admin Dashboard"')).toBeVisible();
    await expect(page.locator(`text="${admin.name}"`)).toBeVisible();

    // Should have admin navigation
    const adminNavItems = [
      'text="Users"',
      'text="Documents"',
      'text="Settings"',
      'text="Analytics"',
    ];

    let foundNavItems = 0;
    for (const item of adminNavItems) {
      if (await page.locator(item).isVisible({ timeout: 2000 })) {
        foundNavItems++;
      }
    }
    expect(foundNavItems).toBeGreaterThan(0);
  });

  test('regular user cannot access admin dashboard', async ({ page }) => {
    const user = TEST_USERS.user;

    // Try to sign in to dashboard with regular user
    await page.goto('http://localhost:3001/sign-in');

    await page.fill('[name="email"]', user.email);
    await page.fill('[name="password"]', user.password);
    await page.click('button[type="submit"]');

    // Should either:
    // 1. Show access denied message
    // 2. Redirect to limited user dashboard
    // 3. Redirect back to web app

    const possibleOutcomes = [
      page.locator('text="Access denied"').isVisible(),
      page.locator('text="Insufficient permissions"').isVisible(),
      page.waitForURL(/localhost:3000/), // Redirect to main app
    ];

    const result = await Promise.race(possibleOutcomes);
    expect(result).toBeTruthy();
  });

  test('dashboard handles session expiration', async ({ page }) => {
    const admin = TEST_USERS.admin;

    // Sign in
    await signInDashboardUser(page, admin);

    // Clear session cookies to simulate expiration
    await page.context().clearCookies();

    // Try to access protected dashboard page
    await page.goto('http://localhost:3001/admin/users');

    // Should redirect to sign in
    await page.waitForURL(/\/sign-in/);
    await expect(page.locator('text="Sign In"')).toBeVisible();
  });

  test('dashboard sign out works correctly', async ({ page }) => {
    const admin = TEST_USERS.admin;

    // Sign in
    await signInDashboardUser(page, admin);

    // Sign out
    await signOut(page);

    // Should be signed out
    await expect(page.locator('text="Sign In"')).toBeVisible();

    // Trying to access protected page should redirect to sign in
    await page.goto('http://localhost:3001/admin');
    await page.waitForURL(/\/sign-in/);
  });

  test('dashboard remembers last visited page', async ({ page }) => {
    const admin = TEST_USERS.admin;

    // Try to access specific admin page
    await page.goto('http://localhost:3001/admin/users');

    // Should redirect to sign in with callback
    await page.waitForURL(/\/sign-in.*callback/);

    // Sign in
    await page.fill('[name="email"]', admin.email);
    await page.fill('[name="password"]', admin.password);
    await page.click('button[type="submit"]');

    // Should redirect back to users page
    await page.waitForURL(/\/admin\/users/);
    await expect(page.locator('text="User Management"')).toBeVisible();
  });

  test('dashboard shows appropriate role-based content', async ({ page }) => {
    const admin = TEST_USERS.admin;

    // Sign in as admin
    await signInDashboardUser(page, admin);

    // Should see admin-specific elements
    await expect(page.locator('[data-testid="admin-sidebar"]')).toBeVisible();

    // Check for admin role indicator
    await expect(page.locator('text="Administrator"')).toBeVisible();

    // Should have access to user management
    await page.click('text="Users"');
    await expect(page.locator('text="User Management"')).toBeVisible();

    // Should see user list
    await expect(page.locator('[data-testid="users-table"]')).toBeVisible();
  });

  test('dashboard form validation works', async ({ page }) => {
    await page.goto('http://localhost:3001/sign-in');

    // Submit empty form
    await page.click('button[type="submit"]');

    // Should show validation errors
    await expect(page.locator('text="Email is required"')).toBeVisible();
    await expect(page.locator('text="Password is required"')).toBeVisible();

    // Test invalid email
    await page.fill('[name="email"]', 'invalid-email');
    await page.click('button[type="submit"]');

    await expect(page.locator('text="Invalid email"')).toBeVisible();
  });

  test('dashboard handles authentication errors', async ({ page }) => {
    await page.goto('http://localhost:3001/sign-in');

    // Try with wrong credentials
    await page.fill('[name="email"]', 'wrong@example.com');
    await page.fill('[name="password"]', 'wrongpassword');
    await page.click('button[type="submit"]');

    // Should show error message
    await expect(page.locator('text="Invalid credentials"')).toBeVisible();

    // Should stay on sign in page
    await expect(page).toHaveURL(/\/sign-in/);

    // Form should be cleared or allow retry
    await expect(page.locator('[name="email"]')).toBeVisible();
  });
});
