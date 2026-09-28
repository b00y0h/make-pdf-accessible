import { test, expect } from '@playwright/test';
import { parseCsv, restNonce, session, summaryRows } from './helpers.mjs';

test.describe.configure({ mode: 'serial' });

const PAGE = '/wp-admin/upload.php?page=make-pdf-accessible-inventory';
const SCAN = '/wp-json/make-pdf-accessible/v1/inventory/scan';

let admin;
let subscriber;
let visitor;

test.beforeAll(async ({ baseURL }) => {
  admin = await session(baseURL, 'admin', 'password');
  subscriber = await session(baseURL, 'sub', 'subpass');
  visitor = await session(baseURL);
  // Start from "never scanned", keeping the checks made when the PDFs were uploaded.
  expect((await visitor.get('/?e2e_reset_inventory=1')).ok()).toBeTruthy();
});

test.afterAll(async () => {
  await Promise.all([admin.dispose(), subscriber.dispose(), visitor.dispose()]);
});

async function scan(nonce) {
  let body = { phase: 'files', offset: 0 };
  for (let calls = 1; calls <= 50; calls++) {
    const response = await admin.post(SCAN, {
      headers: { 'X-WP-Nonce': nonce },
      data: body,
    });
    expect(response.status(), await response.text()).toBe(200);
    const data = await response.json();
    if (data.done) {
      return calls;
    }
    body = { phase: data.phase, offset: data.offset };
  }
  throw new Error('scan did not finish');
}

test('only administrators can scan or view the inventory', async () => {
  const anonymous = await visitor.post(SCAN, {
    data: { phase: 'files', offset: 0 },
  });
  expect(anonymous.status()).toBe(401);

  const refused = await subscriber.post(SCAN, {
    headers: { 'X-WP-Nonce': await restNonce(subscriber) },
    data: { phase: 'files', offset: 0 },
  });
  expect(refused.status()).toBe(403);
  expect((await refused.json()).code).toBe('rest_forbidden');

  expect((await subscriber.get(PAGE)).status()).toBe(403);
});

test('uploads are checked automatically before any full scan', async () => {
  const html = await (await admin.get(PAGE)).text();
  expect(html).toContain('New uploads are checked automatically');
  expect(summaryRows(html)['PDFs found']).toBe(
    '6 (18 pages, plus 1 with an unknown page count)'
  );
  expect(html).toContain('assets/inventory.js');
});

test('a full scan checks files, maps links and totals the backlog', async () => {
  const before = await (await admin.get(PAGE)).text();
  const nonce = before.match(
    /var makePdfAccessibleInventory = [^;]*"nonce":"([a-f0-9]+)"/
  )[1];
  expect(await scan(nonce)).toBeLessThan(10);

  const html = await (await admin.get(PAGE)).text();
  expect(summaryRows(html)).toMatchObject({
    'PDFs found': '8 (22 pages, plus 2 with an unknown page count)',
    Tagged: '2',
    Untagged: '2',
    'No text layer (likely scanned)': '2',
    'Couldn’t check': '2',
    'Linked from published content': '5',
    'Not linked from published content': '3',
    'Fillable forms': '1',
    'Links to PDFs on other sites (not checked)': '1',
  });
  expect(html).toContain('4 PDFs with 20 pages need tagging or a text layer');
  expect(html).toContain('that’s about $50 to $240');
  expect(html).toContain(
    '1 of those pages are in PDFs that no published content links to'
  );
  expect(html).toContain('about $48 to $228');
  expect(html).not.toContain('New uploads are checked automatically');

  expect(html).toContain(
    'old-catalog.pdf</a></strong><br />Not in the media library'
  );
  expect(html).toContain('Linked file not found');
  expect(html).toContain('Needs work <span class="count">(4)</span>');
  expect(html).toContain('Not linked <span class="count">(3)</span>');
  expect(html).toContain('<strong>Untagged</strong>');
  expect(html).toContain('Forms and documents</a>');
});

test('views and sorting', async () => {
  const unlinked = await (await admin.get(`${PAGE}&view=unlinked`)).text();
  expect(unlinked).toContain('>aid-form</a>'); // linked only from a draft
  expect(unlinked).toContain('aria-current="page">Not linked');
  expect(unlinked).not.toContain('>research-paper</a>');

  const sorted = await (
    await admin.get(`${PAGE}&orderby=pages&order=desc`)
  ).text();
  const names = [
    ...sorted
      .split('<tbody id="the-list"')[1]
      .matchAll(/<strong><a href="[^"]*">([^<]+)<\/a><\/strong>/g),
  ].map((m) => m[1]);
  expect(names[0]).toBe('research-paper');
  expect(names[1]).toBe('old-catalog.pdf');
});

test('CSV export', async () => {
  const html = await (await admin.get(PAGE)).text();
  const nonce = [...html.matchAll(/name="_wpnonce" value="([^"]+)"/g)].pop()[1];
  const response = await admin.post('/wp-admin/admin-post.php', {
    form: { action: 'make_pdf_accessible_inventory_csv', _wpnonce: nonce },
  });
  expect(response.status()).toBe(200);
  expect(response.headers()['content-type']).toContain('text/csv');

  const rows = Object.fromEntries(
    parseCsv(await response.text()).map((row) => [row.File, row])
  );
  expect(Object.keys(rows).sort()).toEqual([
    'aid-form',
    'encrypted-report',
    'missing.pdf',
    'old-catalog.pdf',
    'old-memo',
    'research-paper',
    'scanned-flyer',
    'structure-guide',
  ]);
  expect(rows['research-paper']).toMatchObject({
    Status: 'Untagged',
    Pages: '14',
    'Linked from (count)': '1',
  });
  expect(rows['research-paper']['Linked from']).toContain(
    '/forms-and-documents/'
  );
  expect(rows['old-catalog.pdf']).toMatchObject({
    Location: 'Outside media library',
    Status: 'No text layer (likely scanned)',
    Pages: '4',
  });
  expect(rows['aid-form']).toMatchObject({
    'Fillable form': 'Yes',
    Language: 'FR',
    'Linked from (count)': '0',
  });
  expect(rows['encrypted-report']).toMatchObject({
    Status: 'Encrypted, couldn’t check',
    Pages: '',
  });

  const refused = await admin.post('/wp-admin/admin-post.php', {
    form: { action: 'make_pdf_accessible_inventory_csv', _wpnonce: 'bad' },
  });
  expect(refused.status()).not.toBe(200);
});
