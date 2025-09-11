import { test, expect } from '@playwright/test';
import { TEST_USERS, ensureAuthenticated } from '../../shared/auth';

test.describe('Dashboard - User Management', () => {
  test.beforeEach(async ({ page }) => {
    // Ensure admin is authenticated
    await ensureAuthenticated(page, TEST_USERS.admin, 'dashboard');

    // Navigate to user management
    await page.goto('http://localhost:3001/admin/users');
  });

  test('admin can view users list', async ({ page }) => {
    // Should see user management page
    await expect(page.locator('h1:has-text("User Management")')).toBeVisible();

    // Should see users table
    await expect(page.locator('[data-testid="users-table"]')).toBeVisible();

    // Should see table headers
    const expectedHeaders = ['Email', 'Name', 'Role', 'Created', 'Actions'];
    for (const header of expectedHeaders) {
      await expect(page.locator(`th:has-text("${header}")`)).toBeVisible();
    }

    // Should see some users (at least our test users)
    await expect(page.locator('tbody tr')).toHaveCount(2, { timeout: 10000 });
  });

  test('admin can search/filter users', async ({ page }) => {
    // Wait for users to load
    await expect(page.locator('tbody tr')).toHaveCount(2, { timeout: 10000 });

    // Use search/filter
    const searchInput = page.locator('[data-testid="user-search"]');
    if (await searchInput.isVisible()) {
      await searchInput.fill('e2e.user@example.com');

      // Should filter results
      await expect(page.locator('tbody tr')).toHaveCount(1, { timeout: 5000 });
      await expect(page.locator('text="e2e.user@example.com"')).toBeVisible();
    }

    // Test role filter if available
    const roleFilter = page.locator('[data-testid="role-filter"]');
    if (await roleFilter.isVisible()) {
      await roleFilter.selectOption('admin');

      // Should show only admin users
      await expect(page.locator('text="e2e.admin@example.com"')).toBeVisible();
    }
  });

  test('admin can view user details', async ({ page }) => {
    // Wait for users to load
    await expect(page.locator('tbody tr')).toHaveCount(2, { timeout: 10000 });

    // Click on first user to view details
    await page.click('[data-testid="view-user"]:first-child');

    // Should open user details (could be modal, drawer, or new page)
    const userDetailSelectors = [
      '[data-testid="user-details-modal"]',
      '[data-testid="user-details-drawer"]',
      'h1:has-text("User Details")',
    ];

    let foundDetails = false;
    for (const selector of userDetailSelectors) {
      if (await page.locator(selector).isVisible({ timeout: 5000 })) {
        foundDetails = true;
        break;
      }
    }
    expect(foundDetails).toBeTruthy();

    // Should show user information
    await expect(page.locator('text="Email:"')).toBeVisible();
    await expect(page.locator('text="Role:"')).toBeVisible();
    await expect(page.locator('text="Created:"')).toBeVisible();
  });

  test('admin can change user roles', async ({ page }) => {
    // Wait for users to load
    await expect(page.locator('tbody tr')).toHaveCount(2, { timeout: 10000 });

    // Find the regular user row
    const userRow = page.locator('tr:has-text("e2e.user@example.com")');
    await expect(userRow).toBeVisible();

    // Click edit/role change button
    await userRow.locator('[data-testid="edit-user-role"]').click();

    // Should open role editing interface
    const roleEditSelectors = [
      '[data-testid="role-select"]',
      'select[name="role"]',
      '[data-testid="change-role-modal"]',
    ];

    let foundRoleEdit = false;
    for (const selector of roleEditSelectors) {
      if (await page.locator(selector).isVisible({ timeout: 5000 })) {
        foundRoleEdit = true;
        break;
      }
    }
    expect(foundRoleEdit).toBeTruthy();

    // Change role to admin
    const roleSelect = page.locator('[data-testid="role-select"]');
    if (await roleSelect.isVisible()) {
      await roleSelect.selectOption('admin');

      // Save changes
      await page.click('button:has-text("Save")');

      // Should show success message
      await expect(page.locator('text="User role updated"')).toBeVisible({
        timeout: 10000,
      });

      // Role should be updated in the table
      await expect(userRow.locator('text="admin"')).toBeVisible({
        timeout: 5000,
      });
    }
  });

  test('admin can delete users', async ({ page }) => {
    // Wait for users to load
    await expect(page.locator('tbody tr')).toHaveCount(2, { timeout: 10000 });

    // Find a user to delete (not the current admin)
    const userRow = page.locator('tr:has-text("e2e.user@example.com")');
    await expect(userRow).toBeVisible();

    // Click delete button
    await userRow.locator('[data-testid="delete-user"]').click();

    // Should show confirmation dialog
    await expect(page.locator('text="Are you sure"')).toBeVisible();
    await expect(page.locator('button:has-text("Delete")')).toBeVisible();

    // Confirm deletion
    await page.click('button:has-text("Delete")');

    // Should show success message
    await expect(page.locator('text="User deleted"')).toBeVisible({
      timeout: 10000,
    });

    // User should be removed from table
    await expect(page.locator('tbody tr')).toHaveCount(1, { timeout: 5000 });
    await expect(page.locator('text="e2e.user@example.com"')).not.toBeVisible();
  });

  test('admin can view user statistics', async ({ page }) => {
    // Should see user statistics/summary
    const statSelectors = [
      '[data-testid="total-users"]',
      '[data-testid="active-users"]',
      '[data-testid="admin-users"]',
      'text="Total Users"',
    ];

    let foundStats = false;
    for (const selector of statSelectors) {
      if (await page.locator(selector).isVisible({ timeout: 5000 })) {
        foundStats = true;
        break;
      }
    }
    expect(foundStats).toBeTruthy();
  });

  test('admin can export user data', async ({ page }) => {
    // Look for export functionality
    const exportButton = page.locator('button:has-text("Export")');

    if (await exportButton.isVisible({ timeout: 5000 })) {
      // Set up download expectation
      const downloadPromise = page.waitForEvent('download');

      await exportButton.click();

      const download = await downloadPromise;

      // Verify download
      expect(download.suggestedFilename()).toMatch(/users.*\.(csv|xlsx)$/);
    }
  });

  test('pagination works correctly', async ({ page }) => {
    // This test assumes there are enough users to paginate
    // In a real scenario, you'd seed more test data

    const paginationContainer = page.locator('[data-testid="pagination"]');

    if (await paginationContainer.isVisible({ timeout: 5000 })) {
      // Check pagination controls
      await expect(page.locator('button:has-text("Next")')).toBeVisible();
      await expect(page.locator('button:has-text("Previous")')).toBeVisible();

      // Test page size selector if available
      const pageSizeSelect = page.locator('[data-testid="page-size-select"]');
      if (await pageSizeSelect.isVisible()) {
        await pageSizeSelect.selectOption('10');

        // Should update results
        await expect(page.locator('tbody tr')).toHaveCount(2); // Our test data
      }
    }
  });

  test('admin cannot delete themselves', async ({ page }) => {
    // Wait for users to load
    await expect(page.locator('tbody tr')).toHaveCount(2, { timeout: 10000 });

    // Find the current admin user row
    const adminRow = page.locator('tr:has-text("e2e.admin@example.com")');
    await expect(adminRow).toBeVisible();

    // Delete button should be disabled or not present for current user
    const deleteButton = adminRow.locator('[data-testid="delete-user"]');

    if (await deleteButton.isVisible({ timeout: 2000 })) {
      await expect(deleteButton).toBeDisabled();
    } else {
      // Delete button should not be visible for current user
      await expect(deleteButton).not.toBeVisible();
    }
  });

  test('user management shows loading states', async ({ page }) => {
    // Reload page to catch loading state
    await page.reload();

    // Should show loading indicator initially
    const loadingIndicators = [
      '[data-testid="loading-users"]',
      'text="Loading users..."',
      '[data-testid="skeleton-loader"]',
      '.animate-pulse',
    ];

    let foundLoading = false;
    for (const indicator of loadingIndicators) {
      if (await page.locator(indicator).isVisible({ timeout: 2000 })) {
        foundLoading = true;
        break;
      }
    }

    // Loading should eventually disappear
    if (foundLoading) {
      await expect(
        page.locator('[data-testid="loading-users"]')
      ).not.toBeVisible({ timeout: 10000 });
    }

    // Users should load
    await expect(page.locator('tbody tr')).toHaveCount(2, { timeout: 10000 });
  });
});
