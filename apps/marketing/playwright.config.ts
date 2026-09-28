import { defineConfig, devices } from '@playwright/test';

// Serves the static export from out/ and runs axe against every route in src/content/routes.ts.
// PLAYWRIGHT_CHROMIUM_EXECUTABLE lets environments with a preinstalled Chromium reuse it.
const executablePath = process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE;

export default defineConfig({
  testDir: './tests',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? [['list'], ['html', { open: 'never' }]] : 'list',
  use: {
    baseURL: 'http://127.0.0.1:3100',
    trace: 'retain-on-failure',
    ...(executablePath ? { launchOptions: { executablePath } } : {}),
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
  webServer: {
    command: 'pnpm exec serve out -l 3100 --no-clipboard --no-request-logging',
    url: 'http://127.0.0.1:3100/',
    reuseExistingServer: !process.env.CI,
    timeout: 60_000,
  },
});
