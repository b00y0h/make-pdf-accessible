#!/usr/bin/env node
// Fails the build when marketing copy contains a phrase from src/content/banned-phrases.json.
// Scans source files and, when present, the exported site in out/.
import { readFileSync, readdirSync, statSync, existsSync } from 'node:fs';
import { join, relative, extname } from 'node:path';

const root = new URL('..', import.meta.url).pathname;
const config = JSON.parse(
  readFileSync(join(root, 'src/content/banned-phrases.json'), 'utf8')
);
const phrases = config.phrases.map((phrase) => phrase.toLowerCase());
const SOURCE_EXT = new Set(['.ts', '.tsx', '.md', '.mdx', '.html']);
const SKIP_DIRS = new Set([
  'node_modules',
  '.next',
  'test-results',
  'playwright-report',
]);

function walk(dir, out) {
  for (const entry of readdirSync(dir)) {
    if (SKIP_DIRS.has(entry)) continue;
    const full = join(dir, entry);
    const stats = statSync(full);
    if (stats.isDirectory()) walk(full, out);
    else if (SOURCE_EXT.has(extname(entry))) out.push(full);
  }
  return out;
}

const targets = [join(root, 'src')];
if (existsSync(join(root, 'out'))) targets.push(join(root, 'out'));
const files = targets.flatMap((dir) => walk(dir, []));

const findings = [];
for (const file of files) {
  if (file.endsWith('banned-phrases.json')) continue;
  const text = readFileSync(file, 'utf8');
  const lower = text.toLowerCase();
  for (const phrase of phrases) {
    let index = lower.indexOf(phrase);
    while (index !== -1) {
      const line = text.slice(0, index).split('\n').length;
      findings.push(`${relative(root, file)}:${line}: "${phrase}"`);
      index = lower.indexOf(phrase, index + phrase.length);
    }
  }
}

if (findings.length > 0) {
  console.error('Banned phrases found (see src/content/banned-phrases.json):');
  for (const finding of findings) console.error(`  ${finding}`);
  process.exit(1);
}
console.log(`Checked ${files.length} files: no banned phrases.`);
