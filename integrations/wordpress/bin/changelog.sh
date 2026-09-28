#!/usr/bin/env bash
# Prints the readme.txt Changelog entry for a version, for release notes.
# Usage: bin/changelog.sh <version>
set -euo pipefail

cd "$(dirname "$0")/.."
tr -d '\r' < readme.txt | awk -v heading="= $1 =" '
  /^== / { in_changelog = ($0 == "== Changelog ==") }
  in_changelog && $0 == heading { found = 1; next }
  found && /^=/ { exit }
  found && NF { print }
'
