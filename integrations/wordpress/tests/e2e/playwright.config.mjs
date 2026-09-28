import { defineConfig } from '@playwright/test';
import { localWordPress } from './scripts/wordpress-source.mjs';

const wp = process.env.WP_VERSION || 'latest';
const php = process.env.PHP_VERSION || '8.3';
const port = process.env.PORT || '9400';
const baseURL = `http://127.0.0.1:${port}`;
const run = `wp-${wp}-php-${php}`;
// Offline mode: use a local copy of WordPress instead of downloading it.
const wpSource =
  process.env.WP_SOURCE || localWordPress(process.env.WP_SOURCES_DIR, wp);

export default defineConfig({
  testDir: './specs',
  // Specs change shared site state (options, scan results), so run them one at a time.
  workers: 1,
  fullyParallel: false,
  retries: process.env.CI ? 1 : 0,
  timeout: 60_000,
  outputDir: `test-results/${run}`,
  reporter: process.env.CI
    ? [
        ['list'],
        ['github'],
        ['html', { outputFolder: `playwright-report/${run}`, open: 'never' }],
      ]
    : [['list']],
  use: {
    baseURL,
    trace: 'retain-on-failure',
    launchOptions: process.env.CHROMIUM_EXECUTABLE
      ? { executablePath: process.env.CHROMIUM_EXECUTABLE }
      : {},
  },
  webServer: {
    command: 'node scripts/start-wordpress.mjs',
    url: `${baseURL}/wp-login.php`,
    env: {
      WP_VERSION: wp,
      PHP_VERSION: php,
      PORT: port,
      ...(wpSource ? { WP_SOURCE: wpSource } : {}),
    },
    // Downloading WordPress and PHP on a cold cache can take a few minutes.
    timeout: 300_000,
    // Locally, `npm run wp` in another terminal keeps a site running between test runs.
    reuseExistingServer: !process.env.CI && process.env.REUSE_SERVER !== '0',
    stdout: 'pipe',
  },
});
