#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "$script_dir/.." && pwd)"

export PATH="/opt/homebrew/share/google-cloud-sdk/bin:$PATH"

if [[ -f "$HOME/.nvm/nvm.sh" ]]; then
  source "$HOME/.nvm/nvm.sh"
  nvm use 22 >/dev/null || true
fi

echo "== OpenClaw status =="

echo "[1/4] Gateway listener"
if lsof -nP -iTCP:18789 -sTCP:LISTEN >/dev/null 2>&1; then
  echo "OK: gateway listening on 18789"
else
  echo "FAIL: gateway not listening on 18789"
fi

echo "[2/4] Gateway health + Telegram"
if command -v pnpm >/dev/null 2>&1; then
  token="$($repo_root/scripts/show-gateway-token.sh 2>/dev/null || true)"
  if [[ -n "$token" ]]; then
    if (cd "$repo_root" && pnpm openclaw gateway health --url ws://127.0.0.1:18789 --token "$token") >/tmp/openclaw-status-health.log 2>&1; then
      echo "OK: gateway health passed"
      grep -E "Telegram:" /tmp/openclaw-status-health.log || true
    else
      echo "FAIL: gateway health failed"
      tail -n 20 /tmp/openclaw-status-health.log || true
    fi
  else
    echo "FAIL: could not read gateway token"
  fi
else
  echo "FAIL: pnpm not found"
fi

echo "[3/4] Phone USB (adb)"
if command -v adb >/dev/null 2>&1; then
  adb_out="$(adb devices -l | sed '1d' | sed '/^$/d' || true)"
  if [[ -n "$adb_out" ]]; then
    echo "OK: adb device detected"
    echo "$adb_out"
  else
    echo "WARN: no adb device detected"
  fi
else
  echo "FAIL: adb not found"
fi

echo "[4/4] USB reverse tunnel"
if command -v adb >/dev/null 2>&1; then
  rev="$(adb reverse --list 2>/dev/null || true)"
  if echo "$rev" | grep -q "tcp:18789 tcp:18789"; then
    echo "OK: adb reverse active (18789)"
  else
    echo "WARN: adb reverse missing (run: adb reverse tcp:18789 tcp:18789)"
  fi
else
  echo "SKIP: adb unavailable"
fi
