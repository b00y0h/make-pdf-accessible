import { defineConfig, devices } from '@playwright/test';

/**
 * @see https://playwright.dev/docs/test-configuration
 */
export default defineConfig({
  testDir: './e2e',

  /* Run tests in files in parallel */
  fullyParallel: true,

  /* Fail the build on CI if you accidentally left test.only in the source code. */
  forbidOnly: !!process.env.CI,

  /* Retry on CI only */
  retries: process.env.CI ? 2 : 0,

  /* Opt out of parallel tests on CI. */
  workers: process.env.CI ? 1 : undefined,

  /* Reporter to use. See https://playwright.dev/docs/test-reporters */
  reporter: [
    ['html', { outputFolder: 'test-results/playwright-report' }],
    ['json', { outputFile: 'test-results/playwright-results.json' }],
    ['junit', { outputFile: 'test-results/playwright-junit.xml' }],
  ],

  /* Shared settings for all the projects below. See https://playwright.dev/docs/api/class-testoptions. */
  use: {
    /* Base URL to use in actions like `await page.goto('/')`. */
    baseURL: process.env.PLAYWRIGHT_BASE_URL || 'http://localhost:3000',

    /* Collect trace when retrying the failed test. See https://playwright.dev/docs/trace-viewer */
    trace: 'on-first-retry',

    /* Take screenshot on failure */
    screenshot: 'only-on-failure',

    /* Record video on failure */
    video: 'retain-on-failure',

    /* Global timeout for all actions */
    actionTimeout: 30 * 1000,

    /* Global timeout for navigation actions */
    navigationTimeout: 30 * 1000,
  },

  /* Configure projects for major browsers */
  projects: [
    {
      name: 'setup',
      testMatch: /.*\.setup\.ts/,
      teardown: 'cleanup',
    },

    {
      name: 'cleanup',
      testMatch: /.*\.teardown\.ts/,
    },

    // Web Application Tests
    {
      name: 'web-chromium',
      use: {
        ...devices['Desktop Chrome'],
        baseURL: 'http://localhost:3000',
      },
      dependencies: ['setup'],
      testDir: './e2e/web',
    },

    {
      name: 'web-firefox',
      use: {
        ...devices['Desktop Firefox'],
        baseURL: 'http://localhost:3000',
      },
      dependencies: ['setup'],
      testDir: './e2e/web',
    },

    {
      name: 'web-webkit',
      use: {
        ...devices['Desktop Safari'],
        baseURL: 'http://localhost:3000',
      },
      dependencies: ['setup'],
      testDir: './e2e/web',
    },

    // Dashboard Application Tests
    {
      name: 'dashboard-chromium',
      use: {
        ...devices['Desktop Chrome'],
        baseURL: 'http://localhost:3001',
      },
      dependencies: ['setup'],
      testDir: './e2e/dashboard',
    },

    {
      name: 'dashboard-firefox',
      use: {
        ...devices['Desktop Firefox'],
        baseURL: 'http://localhost:3001',
      },
      dependencies: ['setup'],
      testDir: './e2e/dashboard',
    },

    {
      name: 'dashboard-webkit',
      use: {
        ...devices['Desktop Safari'],
        baseURL: 'http://localhost:3001',
      },
      dependencies: ['setup'],
      testDir: './e2e/dashboard',
    },

    // Mobile Tests
    {
      name: 'web-mobile-chrome',
      use: {
        ...devices['Pixel 5'],
        baseURL: 'http://localhost:3000',
      },
      dependencies: ['setup'],
      testDir: './e2e/web',
      testMatch: '**/mobile/**/*.spec.ts',
    },

    {
      name: 'web-mobile-safari',
      use: {
        ...devices['iPhone 12'],
        baseURL: 'http://localhost:3000',
      },
      dependencies: ['setup'],
      testDir: './e2e/web',
      testMatch: '**/mobile/**/*.spec.ts',
    },

    // API Tests
    {
      name: 'api-tests',
      use: {
        baseURL: 'http://localhost:8000',
      },
      dependencies: ['setup'],
      testDir: './e2e/api',
    },
  ],

  /* Run your local dev server before starting the tests */
  webServer: [
    {
      command: 'pnpm --filter web dev',
      url: 'http://localhost:3000',
      reuseExistingServer: !process.env.CI,
      timeout: 120 * 1000,
    },
    {
      command: 'pnpm --filter accesspdf-dashboard dev',
      url: 'http://localhost:3001',
      reuseExistingServer: !process.env.CI,
      timeout: 120 * 1000,
    },
    {
      command: 'make dev-services',
      url: 'http://localhost:8000/health',
      reuseExistingServer: !process.env.CI,
      timeout: 180 * 1000,
    },
  ],

  /* Global test configuration */
  timeout: 60 * 1000,
  expect: {
    timeout: 10 * 1000,
  },

  /* Test output directories */
  outputDir: 'test-results/playwright-output',
});
