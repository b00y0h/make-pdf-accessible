#!/usr/bin/env bash
# Checks that a release is consistent before it ships:
#   - the plugin header Version, ACCESSPDF_VERSION and readme.txt Stable tag agree,
#   - they match the expected version (from the release tag), when one is given,
#   - readme.txt has a Changelog entry for the version,
#   - "Tested up to" covers the newest WordPress in the test matrix,
#   - readme.txt has no placeholders left (skipped with --allow-placeholders, for CI
#     runs before the WordPress.org listing exists).
# Usage: bin/check-release.sh [--allow-placeholders] [expected-version]
set -euo pipefail

allow_placeholders=0
if [ "${1:-}" = "--allow-placeholders" ]; then
  allow_placeholders=1
  shift
fi

cd "$(dirname "$0")/.."
fail=0
error() {
  echo "::error::$1"
  fail=1
}

header=$(sed -n 's/^ \* Version: *//p' accesspdf-plugin.php | tr -d '\r')
constant=$(sed -n "s/^define('ACCESSPDF_VERSION', '\(.*\)');/\1/p" accesspdf-plugin.php)
stable=$(sed -n 's/^Stable tag: *//p' readme.txt | tr -d '\r')
tested=$(sed -n 's/^Tested up to: *//p' readme.txt | tr -d '\r')

echo "Plugin header Version: $header"
echo "ACCESSPDF_VERSION:     $constant"
echo "readme Stable tag:     $stable"
[ "$header" = "$constant" ] || error "Plugin header Version ($header) and ACCESSPDF_VERSION ($constant) differ."
[ "$header" = "$stable" ] || error "Plugin header Version ($header) and readme.txt Stable tag ($stable) differ."
if [ -n "${1:-}" ]; then
  [ "$header" = "$1" ] || error "Release tag version ($1) doesn't match the plugin version ($header)."
fi

if ! bin/changelog.sh "$header" | grep -q .; then
  error "readme.txt Changelog has no entry for $header."
fi

newest=$(grep -o '"wp": "[0-9][0-9.]*"' tests/e2e/matrix.json | grep -o '[0-9][0-9.]*' | sort -V | tail -1)
echo "readme Tested up to:   $tested (newest WordPress in matrix: $newest)"
[ "$(printf '%s\n%s\n' "$newest" "$tested" | sort -V | tail -1)" = "$tested" ] || error "readme.txt 'Tested up to' ($tested) is older than the newest tested WordPress ($newest)."

if grep -n 'REPLACE-WITH' readme.txt; then
  if [ "$allow_placeholders" = 1 ]; then
    echo "::warning::readme.txt still has placeholders (see above). Replace them before releasing."
  else
    error "readme.txt still has placeholders (see above)."
  fi
fi

exit $fail
