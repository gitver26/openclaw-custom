#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "$script_dir/.." && pwd)"

if ! command -v pbcopy >/dev/null 2>&1; then
  echo "pbcopy not found (macOS clipboard tool)." >&2
  exit 1
fi

token="$($repo_root/scripts/show-gateway-token.sh)"
printf '%s' "$token" | pbcopy

echo "Gateway token copied to clipboard."
