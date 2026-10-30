#!/usr/bin/env bash
# Runs the Bondstone stopgap with a command and its arguments, and exits with its exit code.
set -u
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
stopgap="$here/../python/bondstone_stopgap.py"
py="$(command -v python3 || command -v python || true)"
if [ -z "$py" ]; then
  echo "internal error: python3 is required" >&2
  exit 3
fi
"$py" "$stopgap" "$@"
exit $?
