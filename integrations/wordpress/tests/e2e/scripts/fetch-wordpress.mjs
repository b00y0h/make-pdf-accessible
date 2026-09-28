#!/usr/bin/env node
/**
 * Downloads WordPress releases for offline test runs, from the official GitHub mirror
 * (useful where wordpress.org is unreachable). Each version resolves to its newest patch.
 *
 *   npm run fetch-wordpress                # every version in matrix.json
 *   npm run fetch-wordpress -- 7.1 6.8     # specific versions
 *
 * Then run tests with WP_SOURCES_DIR pointing at the printed directory.
 */
import { execFileSync } from 'node:child_process';
import { existsSync, mkdirSync, readFileSync, rmSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { compareVersions } from './wordpress-source.mjs';

const e2eDir = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const dest = path.resolve(
  process.env.WP_SOURCES_DIR || path.join(e2eDir, '.cache/wordpress')
);
const MIRROR = 'https://github.com/WordPress/WordPress';

let versions = process.argv.slice(2);
if (!versions.length) {
  const matrix = JSON.parse(
    readFileSync(path.join(e2eDir, 'matrix.json'), 'utf8')
  );
  versions = [
    ...new Set(
      matrix.include.map((entry) => entry.wp).filter((wp) => /^\d/.test(wp))
    ),
  ];
}

const tags = execFileSync('git', ['ls-remote', '--tags', MIRROR], {
  encoding: 'utf8',
})
  .split('\n')
  .map((line) => line.split('refs/tags/')[1])
  .filter((tag) => tag && /^\d+\.\d+(\.\d+)?$/.test(tag));

mkdirSync(dest, { recursive: true });
for (const version of versions) {
  const matches = tags
    .filter((tag) => tag === version || tag.startsWith(`${version}.`))
    .sort(compareVersions);
  const tag = matches[matches.length - 1];
  if (!tag) {
    console.error(`No WordPress release matches ${version}`);
    process.exitCode = 1;
    continue;
  }
  const target = path.join(dest, tag);
  if (existsSync(path.join(target, 'wp-includes/version.php'))) {
    console.log(`${tag}: already downloaded`);
    continue;
  }
  console.log(`${tag}: cloning…`);
  execFileSync(
    'git',
    ['clone', '--quiet', '--depth', '1', '--branch', tag, MIRROR, target],
    { stdio: 'inherit' }
  );
  rmSync(path.join(target, '.git'), { recursive: true, force: true });
}
console.log(
  `\nWordPress releases are in ${dest}\nRun tests offline with: WP_SOURCES_DIR=${dest}`
);
