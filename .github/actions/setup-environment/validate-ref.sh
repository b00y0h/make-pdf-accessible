#!/usr/bin/env bash
# Checks the ref a run deploys from against an environment's allowed branches or tags.
#
# Usage: validate-ref.sh <environment> <ref-type> <ref-name> <allowed-branches-json> <allowed-tags-json>
#
# action.yml runs this as its "Validate branch and tag permissions" step, and
# test-environment-config.yml runs it against a table of expected results. Exits 0 when the
# ref is allowed and 1 when it is not.

# The flags GitHub runs a `shell: bash` step with
set -eo pipefail

if [ "$#" -ne 5 ]; then
  echo "Usage: $0 <environment> <ref-type> <ref-name> <allowed-branches-json> <allowed-tags-json>" >&2
  exit 2
fi

ENVIRONMENT="$1"
REF_TYPE="$2"
REF_NAME="$3"
ALLOWED_BRANCHES="$4"
ALLOWED_TAGS="$5"

# A tag ref (a release tag push, or a dispatch run from a tag) is checked against
# allowed_tags; any other ref against allowed_branches
if [ "$REF_TYPE" = "tag" ]; then
  REF_KIND="Tag"
  REF_KINDS="tags"
  ALLOWED="$ALLOWED_TAGS"
else
  REF_KIND="Branch"
  REF_KINDS="branches"
  ALLOWED="$ALLOWED_BRANCHES"
fi

echo "🔍 Validating $REF_KIND permissions..."
echo "Current $REF_KIND: $REF_NAME"
echo "Allowed $REF_KINDS: $ALLOWED"

# Each pattern is a glob matched against the whole name ('feature/*' also matches
# 'feature/a/b'). The loop reads from process substitution so it runs in this shell
# and exit ends the script, and [[ ]] never expands a pattern against checkout files.
while read -r pattern; do
  # shellcheck disable=SC2053 # unquoted on purpose: the pattern is a glob
  if [[ "$REF_NAME" == $pattern ]]; then
    echo "✅ $REF_KIND '$REF_NAME' matches pattern '$pattern'"
    exit 0
  fi
done < <(echo "$ALLOWED" | jq -r '.[]')

echo "❌ $REF_KIND '$REF_NAME' is not allowed to deploy to $ENVIRONMENT"
echo "Allowed $REF_KINDS: $ALLOWED"
exit 1
