import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

const WCAG_TAGS = ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa'];

test.beforeEach(async ({ page, baseURL }) => {
  // Keep the run hermetic: nothing outside the test site is needed.
  const host = new URL(baseURL).host;
  await page.route('**/*', (route) =>
    new URL(route.request().url()).host === host
      ? route.continue()
      : route.abort()
  );

  await page.goto(
    `/wp-login.php?redirect_to=${encodeURIComponent(`${baseURL}/wp-admin/upload.php?page=make-pdf-accessible-inventory`)}`
  );
  await page.fill('#user_login', 'admin');
  await page.fill('#user_pass', 'password');
  await Promise.all([
    page.waitForURL(/make-pdf-accessible-inventory/),
    page.click('#wp-submit'),
  ]);
});

async function expectNoViolations(page) {
  const results = await new AxeBuilder({ page })
    .include('#wpbody-content .wrap')
    .withTags(WCAG_TAGS)
    .analyze();
  const summary = results.violations.map(
    (v) =>
      `${v.id}: ${v.help} (${v.nodes.map((n) => n.target.join(' ')).join(', ')})`
  );
  expect(summary).toEqual([]);
}

test('the Media menu opens the inventory, and Scan runs to completion', async ({
  page,
}) => {
  const errors = [];
  page.on('pageerror', (error) => errors.push(error.message));

  // Media → Library expands the Media menu, as it does for a person navigating there.
  await page.goto('/wp-admin/upload.php?mode=list');
  const menuLink = page.locator('#menu-media a', { hasText: 'PDF Inventory' });
  await expect(menuLink).toHaveCount(1);
  await Promise.all([
    page.waitForURL(/make-pdf-accessible-inventory/),
    menuLink.click(),
  ]);

  // The button is enabled only once the scan script has loaded.
  const button = page.locator('#make-pdf-accessible-scan');
  await expect(button).toBeEnabled();
  await button.click();
  await expect(page.locator('#make-pdf-accessible-scan-status')).toContainText(
    'Last full scan',
    { timeout: 60_000 }
  );
  await expect(page.locator('#make-pdf-accessible-scan-progress')).toBeHidden();
  await expect(page.locator('#the-list tr')).toHaveCount(8);
  expect(errors).toEqual([]);
});

test('the inventory page has no WCAG 2.2 A/AA violations', async ({ page }) => {
  await expectNoViolations(page);
  await page.goto(
    '/wp-admin/upload.php?page=make-pdf-accessible-inventory&view=needs_work'
  );
  await expectNoViolations(page);
});

test('the settings page has no WCAG 2.2 A/AA violations', async ({ page }) => {
  await page.goto(
    '/wp-admin/options-general.php?page=make-pdf-accessible-settings'
  );
  await expectNoViolations(page);
});
