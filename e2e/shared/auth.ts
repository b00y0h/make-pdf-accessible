import { Page, expect } from '@playwright/test';

/**
 * Shared authentication utilities for E2E tests
 */

export interface TestUser {
  email: string;
  password: string;
  name: string;
  role: 'user' | 'admin';
}

export const TEST_USERS: Record<string, TestUser> = {
  user: {
    email: 'e2e.user@example.com',
    password: 'E2ETestPass123!',
    name: 'E2E Test User',
    role: 'user',
  },
  admin: {
    email: 'e2e.admin@example.com',
    password: 'E2EAdminPass123!',
    name: 'E2E Admin User',
    role: 'admin',
  },
};

/**
 * Sign in a user via the web interface
 */
export async function signInWebUser(
  page: Page,
  user: TestUser,
  baseUrl: string = 'http://localhost:3000'
) {
  // Go to sign in page
  await page.goto(`${baseUrl}/sign-in`);

  // Fill in credentials
  await page.fill('[name="email"]', user.email);
  await page.fill('[name="password"]', user.password);

  // Submit form
  await page.click('button[type="submit"]');

  // Wait for redirect to dashboard/home
  await page.waitForURL(/\/(dashboard|home|\/)$/);

  // Verify user is signed in
  await expect(page.locator('text="Welcome"')).toBeVisible({ timeout: 10000 });
}

/**
 * Sign in a user via the dashboard interface
 */
export async function signInDashboardUser(page: Page, user: TestUser) {
  // Go to dashboard sign in page
  await page.goto('http://localhost:3001/sign-in');

  // Fill in credentials
  await page.fill('[name="email"]', user.email);
  await page.fill('[name="password"]', user.password);

  // Submit form
  await page.click('button[type="submit"]');

  // Wait for redirect to dashboard
  await page.waitForURL(/\/dashboard|\/admin/);

  // Verify user is signed in - look for user info in header
  await expect(page.locator(`text="${user.name}"`)).toBeVisible({
    timeout: 10000,
  });
}

/**
 * Sign out a user
 */
export async function signOut(page: Page) {
  // Look for sign out button/link - could be in dropdown or direct button
  const signOutSelectors = [
    'button:has-text("Sign Out")',
    'a:has-text("Sign Out")',
    '[data-testid="sign-out"]',
    'button:has-text("Logout")',
    'a:has-text("Logout")',
  ];

  for (const selector of signOutSelectors) {
    try {
      const element = page.locator(selector).first();
      if (await element.isVisible({ timeout: 2000 })) {
        await element.click();
        break;
      }
    } catch {
      // Try next selector
    }
  }

  // Wait for redirect to sign in page or home
  await page.waitForURL(/\/(sign-in|login|\/)$/, { timeout: 10000 });

  // Verify user is signed out
  await expect(page.locator('text="Sign In"')).toBeVisible({ timeout: 5000 });
}

/**
 * Get authentication token for API requests
 */
export async function getAuthToken(user: TestUser): Promise<string> {
  const response = await fetch('http://localhost:3001/api/auth/sign-in/email', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      email: user.email,
      password: user.password,
    }),
  });

  if (!response.ok) {
    throw new Error(
      `Failed to authenticate user ${user.email}: ${response.status}`
    );
  }

  const data = await response.json();
  return data.token;
}

/**
 * Create authenticated API request headers
 */
export async function getAuthHeaders(
  user: TestUser
): Promise<Record<string, string>> {
  const token = await getAuthToken(user);

  return {
    Authorization: `Bearer ${token}`,
    'Content-Type': 'application/json',
  };
}

/**
 * Wait for authentication state to be ready
 */
export async function waitForAuthState(
  page: Page,
  isAuthenticated: boolean = true
) {
  if (isAuthenticated) {
    // Wait for authenticated indicators
    await Promise.race([
      page.waitForSelector('text="Welcome"', { timeout: 10000 }),
      page.waitForSelector('[data-testid="user-menu"]', { timeout: 10000 }),
      page.waitForSelector('text="Dashboard"', { timeout: 10000 }),
    ]);
  } else {
    // Wait for unauthenticated indicators
    await Promise.race([
      page.waitForSelector('text="Sign In"', { timeout: 10000 }),
      page.waitForSelector('button:has-text("Sign In")', { timeout: 10000 }),
      page.waitForSelector('a:has-text("Sign In")', { timeout: 10000 }),
    ]);
  }
}

/**
 * Ensure user is authenticated before test
 */
export async function ensureAuthenticated(
  page: Page,
  user: TestUser,
  appType: 'web' | 'dashboard' = 'web'
) {
  // Check if already authenticated
  const isAuthenticated = await checkAuthenticationStatus(page);

  if (!isAuthenticated) {
    if (appType === 'web') {
      await signInWebUser(page, user);
    } else {
      await signInDashboardUser(page, user);
    }
  }

  // Double check authentication worked
  await waitForAuthState(page, true);
}

/**
 * Check current authentication status
 */
export async function checkAuthenticationStatus(page: Page): Promise<boolean> {
  try {
    // Look for authenticated indicators
    const authIndicators = [
      'text="Welcome"',
      '[data-testid="user-menu"]',
      'text="Dashboard"',
      'button:has-text("Sign Out")',
    ];

    for (const indicator of authIndicators) {
      if (await page.locator(indicator).isVisible({ timeout: 2000 })) {
        return true;
      }
    }

    return false;
  } catch {
    return false;
  }
}

/**
 * Clear authentication state (cookies, localStorage, etc.)
 */
export async function clearAuthState(page: Page) {
  // Clear cookies
  await page.context().clearCookies();

  // Clear localStorage and sessionStorage
  await page.evaluate(() => {
    localStorage.clear();
    sessionStorage.clear();
  });
}
