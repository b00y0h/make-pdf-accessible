/**
 * Offline mode: maps a WordPress version such as "7.1" to the newest matching release
 * in WP_SOURCES_DIR (as filled by `npm run fetch-wordpress`), e.g. ".../7.1.2".
 */
import { existsSync, readdirSync } from 'node:fs';
import path from 'node:path';

export function compareVersions(a, b) {
  const pa = a.split('.').map(Number);
  const pb = b.split('.').map(Number);
  for (let i = 0; i < Math.max(pa.length, pb.length); i++) {
    const diff = (pa[i] || 0) - (pb[i] || 0);
    if (diff) {
      return diff;
    }
  }
  return 0;
}

/** @returns {string|null} Path to the unpacked release, or null when none matches. */
export function localWordPress(sourcesDir, version) {
  if (!sourcesDir || !existsSync(sourcesDir)) {
    return null;
  }
  const releases = readdirSync(sourcesDir)
    .filter((name) => /^\d+\.\d+(\.\d+)?$/.test(name))
    .filter(
      (name) =>
        version === 'latest' ||
        name === version ||
        name.startsWith(`${version}.`)
    )
    .sort(compareVersions);
  return releases.length
    ? path.join(sourcesDir, releases[releases.length - 1])
    : null;
}
