import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import { ROUTES } from '../src/content/routes';

// Every exported route must pass axe-core (WCAG 2.x A/AA rules plus best practices) with zero
// violations. Adding a route to src/content/routes.ts adds it here and to the sitemap.
for (const route of ROUTES) {
  test(`axe: ${route}`, async ({ page }) => {
    const response = await page.goto(route);
    expect(response?.status(), `GET ${route}`).toBe(200);

    const results = await new AxeBuilder({ page })
      .withTags([
        'wcag2a',
        'wcag2aa',
        'wcag21a',
        'wcag21aa',
        'wcag22aa',
        'best-practice',
      ])
      .analyze();

    const summary = results.violations.map(
      (v) => `${v.id}: ${v.help} (${v.nodes.length} nodes)`
    );
    expect(summary, `violations on ${route}`).toEqual([]);
  });
}

test('404 page is served for unknown routes', async ({ page }) => {
  // `serve` returns the exported 404.html; CloudFront does the same in production.
  const response = await page.goto('/this-page-does-not-exist/');
  expect(response?.status()).toBe(404);
  await expect(page.getByRole('heading', { level: 1 })).toHaveText(
    'Page not found'
  );
});

test('skip link moves focus to main content', async ({ page }) => {
  await page.goto('/');
  await page.keyboard.press('Tab');
  await expect(
    page.getByRole('link', { name: 'Skip to main content' })
  ).toBeFocused();
  await page.keyboard.press('Enter');
  await expect(page.locator('#main')).toBeFocused();
});
