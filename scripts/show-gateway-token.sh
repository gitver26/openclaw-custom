#!/usr/bin/env bash
set -euo pipefail

config_path="${OPENCLAW_CONFIG_PATH:-$HOME/.openclaw/openclaw.json}"

if [[ ! -f "$config_path" ]]; then
  echo "OpenClaw config not found: $config_path" >&2
  exit 1
fi

node -e '
const fs = require("fs");
const path = process.argv[1];
const raw = fs.readFileSync(path, "utf8");
const json = JSON.parse(raw);
const token = json?.gateway?.auth?.token;
if (!token || typeof token !== "string" || token.trim() === "") {
  console.error("gateway.auth.token not found in config");
  process.exit(1);
}
process.stdout.write(token.trim() + "\n");
' "$config_path"
