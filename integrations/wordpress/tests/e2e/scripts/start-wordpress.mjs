#!/usr/bin/env node
/**
 * Starts WordPress Playground with the plugin mounted and the test content seeded.
 *
 * Environment:
 *   WP_VERSION  WordPress version: "7.1", "6.8", "latest", "nightly"... (default "latest")
 *   PHP_VERSION PHP version: "8.3", "7.4"... (default "8.3")
 *   PORT        Port to listen on (default 9400)
 *   WP_SOURCE   Optional path to an unpacked WordPress, used instead of downloading from
 *               wordpress.org (for offline use). It is copied, so the source stays clean.
 */
import { spawn } from 'node:child_process';
import { cpSync, mkdtempSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const e2eDir = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const pluginDir = path.resolve(e2eDir, '../..');
const {
  WP_VERSION = 'latest',
  PHP_VERSION = '8.3',
  PORT = '9400',
  WP_SOURCE,
} = process.env;

const args = [
  'server',
  `--php=${PHP_VERSION}`,
  `--port=${PORT}`,
  `--mount=${pluginDir}:/wordpress/wp-content/plugins/make-pdf-accessible`,
  `--mount=${path.join(e2eDir, 'fixtures/mu-plugins')}:/wordpress/wp-content/mu-plugins`,
  `--blueprint=${path.join(e2eDir, 'fixtures/blueprint.json')}`,
];

let copy = null;
if (WP_SOURCE) {
  copy = mkdtempSync(path.join(tmpdir(), 'make-pdf-accessible-wp-'));
  cpSync(WP_SOURCE, copy, { recursive: true });
  args.push(
    '--wordpress-install-mode=install-from-existing-files',
    `--mount-before-install=${copy}:/wordpress`
  );
} else {
  args.push(`--wp=${WP_VERSION}`);
}

const cli = path.join(e2eDir, 'node_modules/.bin/wp-playground-cli');
const child = spawn(cli, args, { stdio: 'inherit' });

const cleanup = () => {
  if (copy) {
    rmSync(copy, { recursive: true, force: true });
    copy = null;
  }
};
for (const signal of ['SIGINT', 'SIGTERM']) {
  process.on(signal, () => {
    child.kill(signal);
  });
}
child.on('exit', (code) => {
  cleanup();
  process.exit(code ?? 1);
});
