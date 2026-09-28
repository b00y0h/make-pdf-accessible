#!/usr/bin/env node
/**
 * Runs the end-to-end suite against every WordPress/PHP combination in matrix.json,
 * several at once on separate ports, and prints a pass/fail table.
 *
 *   npm run matrix                      # required combinations
 *   npm run matrix -- --all             # also the experimental ones
 *   npm run matrix -- 7.1:8.3 6.5:7.4   # specific combinations
 *
 * MATRIX_CONCURRENCY sets how many run at once (default 3). With WP_SOURCES_DIR set,
 * WordPress comes from local copies instead of wordpress.org.
 */
import { spawn } from 'node:child_process';
import { createWriteStream, mkdirSync, readFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { localWordPress } from './wordpress-source.mjs';

const e2eDir = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const matrix = JSON.parse(
  readFileSync(path.join(e2eDir, 'matrix.json'), 'utf8')
).include;
const args = process.argv.slice(2);
const picked = args.filter((arg) => arg.includes(':'));

let runs = picked.length
  ? picked.map((pair) => {
      const [wp, php] = pair.split(':');
      return { wp, php, experimental: false };
    })
  : matrix.filter((entry) => args.includes('--all') || !entry.experimental);

const sourcesDir = process.env.WP_SOURCES_DIR;
runs = runs.filter((run) => {
  if (sourcesDir && !localWordPress(sourcesDir, run.wp)) {
    console.log(
      `skip  WP ${run.wp} / PHP ${run.php}: no local copy in ${sourcesDir}`
    );
    return false;
  }
  return true;
});

const logDir = path.join(e2eDir, 'test-results');
mkdirSync(logDir, { recursive: true });
const concurrency = Number(process.env.MATRIX_CONCURRENCY || 3);
const results = [];

function execute(run, index) {
  const name = `wp-${run.wp}-php-${run.php}`;
  const log = path.join(logDir, `${name}.log`);
  const env = {
    ...process.env,
    WP_VERSION: run.wp,
    PHP_VERSION: run.php,
    PORT: String(9410 + index),
    REUSE_SERVER: '0',
  };
  if (sourcesDir) {
    env.WP_SOURCE = localWordPress(sourcesDir, run.wp);
  }
  const started = Date.now();
  console.log(
    `start WP ${run.wp} / PHP ${run.php} (log: ${path.relative(process.cwd(), log)})`
  );
  return new Promise((resolve) => {
    const out = createWriteStream(log);
    const child = spawn(
      path.join(e2eDir, 'node_modules/.bin/playwright'),
      ['test'],
      { cwd: e2eDir, env }
    );
    child.stdout.pipe(out);
    child.stderr.pipe(out);
    child.on('exit', (code) => {
      const seconds = Math.round((Date.now() - started) / 1000);
      results.push({ ...run, passed: code === 0, seconds });
      console.log(
        `${code === 0 ? 'pass ' : 'FAIL '} WP ${run.wp} / PHP ${run.php} in ${seconds}s`
      );
      resolve();
    });
  });
}

const queue = runs.map((run, index) => () => execute(run, index));
await Promise.all(
  Array.from({ length: Math.min(concurrency, queue.length) }, async () => {
    while (queue.length) {
      await queue.shift()();
    }
  })
);

console.log('\nWordPress  PHP   Result');
for (const r of results.sort((a, b) =>
  `${a.wp}${a.php}`.localeCompare(`${b.wp}${b.php}`)
)) {
  const result = r.passed
    ? 'pass'
    : r.experimental
      ? 'fail (experimental)'
      : 'FAIL';
  console.log(
    `${r.wp.padEnd(10)} ${r.php.padEnd(5)} ${result} (${r.seconds}s)`
  );
}
process.exit(results.some((r) => !r.passed && !r.experimental) ? 1 : 0);
