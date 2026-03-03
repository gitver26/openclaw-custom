# OpenClaw on Samsung A51 — What I did

Date: 2026-02-23

## Goal

Get OpenClaw running on your Samsung A51 over USB from this Mac.

## What I completed

1. Confirmed your phone is visible over USB with ADB
   - Device detected: `SM_A515F` (A51)
   - USB authorization was active (`device` state, not `unauthorized`)

2. Prepared Android build toolchain
   - Installed Java 21 (`temurin@21`) because Android Gradle failed on Java 8
   - Installed Android SDK components and accepted licenses:
     - `platform-tools`
     - `platforms;android-35` (and Gradle auto-fetched platform 36 as needed)
     - `build-tools;35.0.0`

3. Built and installed OpenClaw on your phone
   - Ran Gradle install from `apps/android`
   - Command: `./gradlew installDebug`
   - Result: `BUILD SUCCESSFUL`
   - APK installed on device successfully

4. Verified app package on phone
   - Package found: `ai.openclaw.android`

## Why you saw the OpenClaw interface

The Android app was compiled from this repo and installed directly onto your A51 via USB. That UI is OpenClaw’s native Android interface from this codebase.

## Follow-up fixes completed

1. Installed workspace dependencies
   - Ran `pnpm install` at repo root.

2. Upgraded runtime to supported Node version
   - OpenClaw requires Node `>=22.12.0`.
   - Installed and switched to Node 22 via NVM.

3. Configured Z.AI onboarding (GLM-4.7)
   - Ran onboarding in local mode with risk acknowledgement.
   - Config file was updated successfully: `~/.openclaw/openclaw.json`.

4. Started local Gateway and USB tunnel
   - Started gateway on loopback port `18789`.
   - Verified listener: `127.0.0.1:18789`.
   - Enabled USB reverse tunnel:
     - `adb reverse tcp:18789 tcp:18789`
     - `adb reverse --list` shows the mapping.

5. Verified gateway health
   - Authenticated health check returned `Gateway Health OK`.

6. Rotated gateway auth token (security hardening)
   - Generated a fresh random token and saved it to config.
   - Restarted gateway to apply the new token.
   - Re-validated gateway health with the new token.

## Remaining user action on phone

In the Android app:

- Settings → Advanced → Use Manual Gateway
- Host: `127.0.0.1`
- Port: `18789`
- Gateway Token: use your configured gateway auth token from `~/.openclaw/openclaw.json` (`gateway.auth.token`)
- Connect (Manual)

### Quick token copy helper

From repo root, run:

`./scripts/show-gateway-token.sh`

This prints only the current gateway token so you can paste it into the phone app.

To copy directly to clipboard on macOS:

`./scripts/copy-gateway-token.sh`

## Notes

- App install + runtime infrastructure are complete and verified from this Mac.
- If the app still says not connected, it is usually missing/incorrect manual token on phone settings.
- Current running gateway terminal ID: `4654cdeb-e02f-479e-8768-288fad833032`.

## Daily usage model (important)

- The **OpenClaw gateway on Mac** can keep running even when USB is unplugged.
- **Telegram continues to work** without USB, as long as Mac gateway + internet stay up.
- The Android **OpenClaw node app** needs USB tunnel (`adb reverse`) in your current setup.

## What happens when USB disconnects

- `adb reverse` mapping is removed.
- OpenClaw node on phone shows disconnected.
- Telegram channel still works from the Mac gateway.

## Reconnect runbook (when plugging phone back in)

1. Recreate USB tunnel:
   - `adb reverse tcp:18789 tcp:18789`

2. Run full status check:
   - `./scripts/status-all.sh`

3. Open or relaunch app:
   - `adb shell monkey -p ai.openclaw.android -c android.intent.category.LAUNCHER 1`

4. If still disconnected in app, reconnect manually:
   - Settings → Advanced → Use Manual Gateway
   - Host: `127.0.0.1`
   - Port: `18789`
   - Token: run `./scripts/copy-gateway-token.sh`, then paste
   - Tap **Connect (Manual)**

### Exact commands (run on Mac terminal)

From repo root:

```bash
cd /Users/terence/openclaw/openclaw
adb reverse tcp:18789 tcp:18789
./scripts/status-all.sh
```

Optional helpers:

```bash
# Open OpenClaw node app on phone
adb shell monkey -p ai.openclaw.android -c android.intent.category.LAUNCHER 1

# Copy current gateway token for manual reconnect paste
./scripts/copy-gateway-token.sh
```

## Fast commands you now have

- Show token: `./scripts/show-gateway-token.sh`
- Copy token to clipboard: `./scripts/copy-gateway-token.sh`
- Full system status (gateway + Telegram + USB + reverse): `./scripts/status-all.sh`

## Integrations configured in this session

- Telegram bot token configured and pairing approved.
- Brave Search API key configured (`tools.web.search.apiKey`).
- Notion API key saved (`env.NOTION_API_KEY`).

## Gmail status (current)

- `gogcli` installed.
- Gateway no longer fails on missing `gog`; next blocker is Gmail watcher setup/auth (Google `gcloud`/PubSub flow).
- This does **not** block Telegram or OpenClaw node connectivity.
