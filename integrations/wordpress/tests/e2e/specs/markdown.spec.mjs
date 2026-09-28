import { test, expect } from '@playwright/test';
import {
  AGENT_ACCEPT,
  BROWSER_ACCEPT,
  hasVaryAccept,
  headerValues,
  seededIds,
  session,
  setOption,
} from './helpers.mjs';

test.describe.configure({ mode: 'serial' });

let visitor;
let ids;

test.beforeAll(async ({ baseURL }) => {
  visitor = await session(baseURL);
  ids = await seededIds(visitor);
});

test.afterAll(async () => {
  // Leave the site as the other specs expect it, even if a test failed midway.
  await setOption(visitor, 'make_pdf_accessible_serve_markdown', '1');
  await setOption(visitor, 'permalink_structure', '/%postname%/');
  await visitor.dispose();
});

test('browsers get HTML that advertises the Markdown version', async ({
  baseURL,
}) => {
  const response = await visitor.get('/admissions/', {
    headers: { Accept: BROWSER_ACCEPT },
  });
  expect(response.status()).toBe(200);
  expect(response.headers()['content-type']).toContain('text/html');
  expect(hasVaryAccept(response)).toBe(true);
  expect(headerValues(response, 'link').join(', ')).toContain(
    'admissions.md>; rel="alternate"; type="text/markdown"'
  );
  expect(await response.text()).toContain(
    `<link rel="alternate" type="text/markdown" href="${baseURL}/admissions.md" />`
  );
});

test('.md address returns Markdown converted from the page', async ({
  baseURL,
}) => {
  const response = await visitor.get('/admissions.md', {
    headers: { Accept: BROWSER_ACCEPT },
  });
  expect(response.status()).toBe(200);
  expect(response.headers()['content-type']).toBe(
    'text/markdown; charset=utf-8'
  );
  expect(headerValues(response, 'link').join(', ')).toContain(
    `<${baseURL}/admissions/>; rel="canonical"`
  );
  expect(response.headers()['last-modified']).toMatch(/GMT$/);
  expect(response.headers()['cache-control'] || '').not.toContain('no-store');

  const body = await response.text();
  for (const expected of [
    'title: "Admissions & “Deadlines”"',
    `url: "${baseURL}/admissions/"`,
    '# Admissions & “Deadlines”',
    '## Application deadlines',
    `Apply by **March 1**. See the [financial aid page](${baseURL}/financial-aid/).`,
    '- Two recommendation letters',
    '| Program | Tuition |',
    '| Nursing | $12,000 |',
    `![Students on the quad](${baseURL}/wp-content/uploads/quad.jpg)`,
    'Rendered by a shortcode.',
  ]) {
    expect(body).toContain(expected);
  }
  expect(body).not.toContain('<!-- wp:');
  expect(body).not.toContain('<p>');
});

test('agents asking for text/markdown get Markdown from the normal address', async () => {
  const response = await visitor.get('/admissions/', {
    headers: { Accept: AGENT_ACCEPT },
  });
  expect(response.headers()['content-type']).toContain('text/markdown');
  expect(response.headers()['cache-control']).toContain('no-store');
  expect(hasVaryAccept(response)).toBe(true);

  const htmlFirst = await visitor.get('/admissions/', {
    headers: { Accept: 'text/html, text/markdown' },
  });
  expect(htmlFirst.headers()['content-type']).toContain('text/html');

  const head = await visitor.fetch('/admissions.md', { method: 'HEAD' });
  expect(head.headers()['content-type']).toContain('text/markdown');
});

test('child pages, posts and the front page have .md addresses', async ({
  baseURL,
}) => {
  expect(await (await visitor.get('/admissions/transfer.md')).text()).toContain(
    '# Transfer'
  );
  expect(await (await visitor.get('/campus-news.md')).text()).toContain(
    'News body.'
  );
  expect(await (await visitor.get('/index.md')).text()).toContain(
    'Front page body.'
  );
  expect(
    await (
      await visitor.get('/', { headers: { Accept: BROWSER_ACCEPT } })
    ).text()
  ).toContain(`href="${baseURL}/index.md"`);
});

test('drafts, private, password-protected and unknown content is never served', async () => {
  for (const slug of [
    'secret-draft',
    'private-post',
    'protected-post',
    'nope',
  ]) {
    const response = await visitor.get(`/${slug}.md`);
    expect(response.status(), slug).toBe(404);
    expect(await response.text(), slug).not.toContain('SECRET');
  }
  const draft = await visitor.get(`/?p=${ids.draft}&make_pdf_accessible_md=1`);
  expect(draft.status()).toBe(404);
  expect(await draft.text()).not.toContain('SECRET');

  const protectedPost = await visitor.get('/protected-post/', {
    headers: { Accept: AGENT_ACCEPT },
  });
  expect(protectedPost.headers()['content-type']).toContain('text/html');
  expect(await protectedPost.text()).not.toContain('type="text/markdown"');
});

test('turning the setting off stops Markdown everywhere', async () => {
  await setOption(visitor, 'make_pdf_accessible_serve_markdown', '0');
  expect((await visitor.get('/admissions.md')).status()).toBe(404);
  const negotiated = await visitor.get('/admissions/', {
    headers: { Accept: AGENT_ACCEPT },
  });
  expect(negotiated.headers()['content-type']).toContain('text/html');
  expect(await negotiated.text()).not.toContain('type="text/markdown"');
  await setOption(visitor, 'make_pdf_accessible_serve_markdown', '1');
});

test('sites without pretty permalinks use ?make_pdf_accessible_md=1', async () => {
  await setOption(visitor, 'permalink_structure', '');
  const html = await (
    await visitor.get(`/?page_id=${ids.admissions}`, {
      headers: { Accept: BROWSER_ACCEPT },
    })
  ).text();
  expect(html).toContain(
    `?page_id=${ids.admissions}&#038;make_pdf_accessible_md=1`
  );
  const markdown = await visitor.get(
    `/?page_id=${ids.admissions}&make_pdf_accessible_md=1`
  );
  expect(markdown.headers()['content-type']).toContain('text/markdown');

  await setOption(visitor, 'permalink_structure', '/%postname%/');
  expect((await visitor.get('/admissions.md')).status()).toBe(200);
});

test('the settings form saves through wp-admin', async ({ baseURL }) => {
  const admin = await session(baseURL, 'admin', 'password');
  const page = await (
    await admin.get(
      '/wp-admin/options-general.php?page=make-pdf-accessible-settings'
    )
  ).text();
  expect(page).toContain('id="make_pdf_accessible_serve_markdown"');
  expect(page).toContain(`${baseURL}/about.md`);
  expect(page).not.toContain('embeddings');

  const nonce = page.match(/name="_wpnonce" value="([^"]+)"/)[1];
  const saved = await admin.post('/wp-admin/options.php', {
    form: {
      option_page: 'make_pdf_accessible_settings',
      action: 'update',
      _wpnonce: nonce,
      make_pdf_accessible_api_key: 'test-key',
      make_pdf_accessible_auto_process: '1',
    },
    maxRedirects: 0,
  });
  expect(saved.headers()['location']).toContain('settings-updated=true');
  // The Markdown box was left unchecked, so it saved as off.
  expect((await visitor.get('/admissions.md')).status()).toBe(404);
  expect(
    await (
      await admin.get(
        '/wp-admin/options-general.php?page=make-pdf-accessible-settings'
      )
    ).text()
  ).toContain('value="test-key"');

  await setOption(visitor, 'make_pdf_accessible_serve_markdown', '1');
  await setOption(visitor, 'make_pdf_accessible_api_key', '');
  await admin.dispose();
});
