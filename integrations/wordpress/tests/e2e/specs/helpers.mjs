import { request, expect } from '@playwright/test';

export const BROWSER_ACCEPT =
  'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8';
export const AGENT_ACCEPT = 'text/markdown, text/html;q=0.9, */*;q=0.8';

/** An HTTP client with its own cookies, logged in when a user is given. */
export async function session(baseURL, user, password) {
  const client = await request.newContext({ baseURL });
  if (user) {
    await client.get('/wp-login.php'); // sets the test cookie wp-login.php requires
    const response = await client.post('/wp-login.php', {
      form: {
        log: user,
        pwd: password,
        testcookie: '1',
        redirect_to: `${baseURL}/wp-admin/profile.php`,
      },
      maxRedirects: 0,
    });
    expect(response.status(), `log in as ${user}`).toBe(302);
  }
  return client;
}

/** Changes an option through the test-only helper plugin. */
export async function setOption(client, name, value) {
  const response = await client.get(
    `/?e2e_set=${encodeURIComponent(name)}&value=${encodeURIComponent(value)}`
  );
  expect(response.ok(), `set ${name}`).toBeTruthy();
}

export async function seededIds(client) {
  return (await client.get('/?e2e_ids=1')).json();
}

/** A REST API nonce for the logged-in user, from WordPress's own endpoint. */
export async function restNonce(client) {
  return (
    await (
      await client.get('/wp-admin/admin-ajax.php?action=rest-nonce')
    ).text()
  ).trim();
}

/** Every value of a header, including repeated headers. */
export function headerValues(response, name) {
  return response
    .headersArray()
    .filter((header) => header.name.toLowerCase() === name)
    .map((header) => header.value);
}

export function hasVaryAccept(response) {
  return headerValues(response, 'vary').some((value) =>
    /(^|,)\s*accept\s*(,|$)/i.test(value)
  );
}

/** Rows of the summary table on the PDF Inventory page, as { label: value }. */
export function summaryRows(html) {
  const rows = {};
  for (const [, label, value] of html.matchAll(
    /<th scope="row">(.*?)<\/th>\s*<td>(.*?)<\/td>/g
  )) {
    rows[decode(label)] = decode(value);
  }
  return rows;
}

function decode(text) {
  return text
    .replace(/&#(\d+);/g, (_, code) => String.fromCharCode(Number(code)))
    .replace(/&amp;/g, '&')
    .replace(/&quot;/g, '"')
    .replace(/&#039;/g, "'");
}

/** Minimal CSV parser: quoted fields, doubled quotes, commas and newlines inside quotes. */
export function parseCsv(text) {
  const rows = [];
  let row = [];
  let field = '';
  let quoted = false;
  const input = text.replace(/^﻿/, '');
  for (let i = 0; i < input.length; i++) {
    const char = input[i];
    if (quoted) {
      if (char === '"' && input[i + 1] === '"') {
        field += '"';
        i++;
      } else if (char === '"') {
        quoted = false;
      } else {
        field += char;
      }
    } else if (char === '"') {
      quoted = true;
    } else if (char === ',') {
      row.push(field);
      field = '';
    } else if (char === '\n') {
      row.push(field);
      rows.push(row);
      row = [];
      field = '';
    } else if (char !== '\r') {
      field += char;
    }
  }
  if (field !== '' || row.length) {
    row.push(field);
    rows.push(row);
  }
  const [header, ...body] = rows;
  return body.map((cells) =>
    Object.fromEntries(header.map((name, i) => [name, cells[i] ?? '']))
  );
}
