#!/usr/bin/env bash
# Bondstone pre-commit hook. Install with:
#   ln -s ../../.specify/extensions/bondstone/scripts/bash/pre-commit.sh .git/hooks/pre-commit
# Refuses the commit when the staged files have errors and, in an agent's shell, when the
# commit adds or removes an approval: `status: stable` or `status: deprecated`, a `verified:`
# entry, a `Verified:` line, or a roadmap version's `Status: shipped`.
set -u
here="$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")" && pwd)"

if [ -n "${CLAUDE_CODE_CHILD_SESSION:-}" ]; then
  changed="$(git diff --cached -U0 -- '*.md' | grep -E '^[+-](status: *(stable|deprecated)|verified:)|^[+-].*\b(Verified:|Status: *shipped)' | grep -vE '^(\+\+\+|---)' || true)"
  if [ -n "$changed" ]; then
    echo "bondstone: refused. This commit changes an approval:" >&2
    echo "$changed" | sed 's/^/  /' >&2
    echo "Approvals and manual verifications are for people. Ask the person to make this change." >&2
    exit 1
  fi
fi

bash "$here/bondstone.sh" check --staged
code=$?
if [ "$code" -ne 0 ]; then
  echo "bondstone: commit refused; fix the errors above (exit $code)." >&2
fi
exit "$code"
