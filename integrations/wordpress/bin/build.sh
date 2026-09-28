#!/usr/bin/env bash
# Builds the plugin as it ships to WordPress.org: dist/<slug>/ and dist/<slug>.zip.
set -euo pipefail

cd "$(dirname "$0")/.."
SLUG="${SLUG:-accesspdf}"

rm -rf dist
mkdir -p "dist/$SLUG"
# Copy everything except the .distignore entries (paths relative to the plugin root).
excludes=()
while IFS= read -r line; do
  [[ -z "$line" || "$line" == \#* ]] && continue
  excludes+=("--exclude=.${line}")
done < .distignore
tar -cf - "${excludes[@]}" . | tar -xf - -C "dist/$SLUG"
(cd dist && zip -qr "$SLUG.zip" "$SLUG")

echo "Built dist/$SLUG/ and dist/$SLUG.zip:"
(cd dist && find "$SLUG" -type f | sort)
