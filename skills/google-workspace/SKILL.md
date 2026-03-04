---
name: google-workspace
description: Connect to Gmail, Google Calendar, Google Docs, and Google Sheets via OAuth2. Use for email management, calendar scheduling, document creation/editing, and spreadsheet operations. Requires Google Cloud project with API credentials.
metadata:
  {
    "openclaw":
      {
        "emoji": "🔵",
        "requires":
          {
            "bins": ["python3"],
            "packages": ["google-auth", "google-auth-oauthlib", "google-api-python-client"],
          },
        "primaryEnv": "GOOGLE_OAUTH_CLIENT_ID",
        "install":
          [
            {
              "id": "pip",
              "kind": "pip",
              "package": "google-auth google-auth-oauthlib google-api-python-client",
              "label": "Install Google API libraries",
            },
          ],
      },
  }
---

# Google Workspace Integration Skill

Connect OpenClaw to Gmail, Google Calendar, Google Docs, and Google Sheets using OAuth2 authentication. This skill provides secure, API-based access to your Google Workspace data.

## ⚠️ Security Warning

**This skill accesses highly sensitive personal data: emails, calendar, documents, and spreadsheets.**

**Critical requirements:**

- **OAuth2 credentials must be kept secure** (never commit to git)
- **Run in sandboxed environment** with minimal tool access
- **Enable audit logging** for all API operations
- **Review OAuth scopes** - request minimum necessary permissions
- **Token rotation** - refresh tokens expire, require re-authentication
- **Incident response plan** - know how to revoke compromised tokens

**Read [SECURITY.md](SECURITY.md) before first use.**

**Minimum safe config:**

```json5
{
  agents: {
    list: [
      {
        id: "google-workspace",
        sandbox: { mode: "all", scope: "session" },
        tools: {
          allow: ["read", "write"],
          deny: ["exec", "process", "browser"],
        },
      },
    ],
  },
}
```

## Prerequisites

### 1. Google Cloud Project Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing one
3. Enable APIs:
   - Gmail API
   - Google Calendar API
   - Google Docs API
   - Google Sheets API
4. Configure OAuth consent screen (Internal or External)
5. Create OAuth 2.0 credentials (Desktop app type)
6. Download credentials JSON

### 2. Install Dependencies

```bash
pip3 install google-auth google-auth-oauthlib google-api-python-client
```

### 3. Configure Credentials

Store credentials securely:

```bash
# Store in OpenClaw config
openclaw config set skills.entries.google-workspace.env.GOOGLE_OAUTH_CLIENT_ID "your-client-id"
openclaw config set skills.entries.google-workspace.env.GOOGLE_OAUTH_CLIENT_SECRET "your-client-secret"

# Or use credentials file (more secure)
mkdir -p ~/.openclaw/google-workspace
mv ~/Downloads/credentials.json ~/.openclaw/google-workspace/credentials.json
chmod 600 ~/.openclaw/google-workspace/credentials.json
```

### 4. Initial Authentication

```bash
# Run authentication flow (opens browser)
python3 scripts/google_auth.py --auth

# This creates token.json with refresh token
# Token is stored at: ~/.openclaw/google-workspace/token.json
```

## Quick Start

### Gmail Operations

```bash
# List recent emails
python3 scripts/gmail.py list --max-results 10

# Search emails
python3 scripts/gmail.py search --query "from:example@gmail.com after:2026/03/01"

# Get specific email
python3 scripts/gmail.py get --message-id "18d8f1234567890a"

# Send email
python3 scripts/gmail.py send \
  --to "recipient@example.com" \
  --subject "Hello from OpenClaw" \
  --body "This is a test email"

# Send with attachment
python3 scripts/gmail.py send \
  --to "user@example.com" \
  --subject "Report" \
  --body "Please find attached" \
  --attachments "/path/to/file.pdf"
```

### Google Calendar Operations

```bash
# List upcoming events
python3 scripts/calendar.py list --max-results 10

# Get events for specific date range
python3 scripts/calendar.py list \
  --start "2026-03-01T00:00:00Z" \
  --end "2026-03-31T23:59:59Z"

# Create event
python3 scripts/calendar.py create \
  --summary "Team Meeting" \
  --start "2026-03-10T14:00:00Z" \
  --end "2026-03-10T15:00:00Z" \
  --description "Weekly sync" \
  --attendees "alice@example.com,bob@example.com"

# Update event
python3 scripts/calendar.py update \
  --event-id "abc123xyz" \
  --summary "Updated Meeting Title"

# Delete event
python3 scripts/calendar.py delete --event-id "abc123xyz"
```

### Google Docs Operations

```bash
# Create new document
python3 scripts/docs.py create \
  --title "Project Plan" \
  --content "# Project Overview\n\nThis is the plan..."

# Read document
python3 scripts/docs.py read --doc-id "1ABC-def_GHI"

# Append to document
python3 scripts/docs.py append \
  --doc-id "1ABC-def_GHI" \
  --content "\n\n## New Section\n\nAdditional content..."

# Replace text
python3 scripts/docs.py replace \
  --doc-id "1ABC-def_GHI" \
  --find "old text" \
  --replace "new text"

# Export as PDF
python3 scripts/docs.py export \
  --doc-id "1ABC-def_GHI" \
  --format pdf \
  --output "/path/to/output.pdf"
```

### Google Sheets Operations

```bash
# Create new spreadsheet
python3 scripts/sheets.py create \
  --title "Sales Data Q1 2026"

# Read values
python3 scripts/sheets.py read \
  --sheet-id "1XYZ-abc_DEF" \
  --range "Sheet1!A1:D10"

# Write values (single cell)
python3 scripts/sheets.py write \
  --sheet-id "1XYZ-abc_DEF" \
  --range "Sheet1!A1" \
  --values "[[\"Header 1\", \"Header 2\", \"Header 3\"]]"

# Write values (multiple rows)
python3 scripts/sheets.py write \
  --sheet-id "1XYZ-abc_DEF" \
  --range "Sheet1!A1" \
  --values '[["Name","Email","Phone"],["Alice","alice@example.com","555-1234"]]'

# Append row
python3 scripts/sheets.py append \
  --sheet-id "1XYZ-abc_DEF" \
  --range "Sheet1!A:C" \
  --values '[["Bob","bob@example.com","555-5678"]]'

# Clear range
python3 scripts/sheets.py clear \
  --sheet-id "1XYZ-abc_DEF" \
  --range "Sheet1!A1:Z100"
```

## OAuth Scopes

Default scopes (can be customized):

```python
SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',        # Read email
    'https://www.googleapis.com/auth/gmail.send',            # Send email
    'https://www.googleapis.com/auth/calendar',              # Full calendar access
    'https://www.googleapis.com/auth/documents',             # Full docs access
    'https://www.googleapis.com/auth/spreadsheets',          # Full sheets access
]
```

**Principle of least privilege:** Only request scopes you need.

### Scope Reduction Examples

```python
# Read-only email
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

# Calendar read-only
SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']

# Docs read-only
SCOPES = ['https://www.googleapis.com/auth/documents.readonly']

# Sheets read-only
SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']
```

## Common Patterns

### Email Processing Workflow

```bash
# 1. Search for unread emails with specific label
python3 scripts/gmail.py search --query "is:unread label:important" --max-results 5

# 2. Get full content of each email
python3 scripts/gmail.py get --message-id "MSG_ID" --format full

# 3. Process content (agent extracts info)

# 4. Mark as read
python3 scripts/gmail.py modify --message-id "MSG_ID" --remove-labels "UNREAD"

# 5. Send reply
python3 scripts/gmail.py reply \
  --message-id "MSG_ID" \
  --body "Thanks for your email..."
```

### Calendar + Email Integration

```bash
# 1. Get upcoming meetings
python3 scripts/calendar.py list --max-results 5

# 2. For each meeting, send reminder emails to attendees
python3 scripts/gmail.py send \
  --to "attendee@example.com" \
  --subject "Reminder: Meeting in 1 hour" \
  --body "Don't forget our meeting at 2pm"
```

### Document Generation Workflow

```bash
# 1. Create doc from template
python3 scripts/docs.py create --title "Monthly Report - March 2026"

# 2. Agent generates content

# 3. Write sections to doc
python3 scripts/docs.py append --doc-id "DOC_ID" --content "## Sales Summary..."

# 4. Export as PDF
python3 scripts/docs.py export --doc-id "DOC_ID" --format pdf --output "report.pdf"

# 5. Email the PDF
python3 scripts/gmail.py send \
  --to "manager@example.com" \
  --subject "March Report" \
  --attachments "report.pdf"
```

### Sheets Data Analysis

```bash
# 1. Read data from sheet
python3 scripts/sheets.py read --sheet-id "SHEET_ID" --range "Sheet1!A1:E100"

# 2. Agent processes/analyzes data

# 3. Write results back
python3 scripts/sheets.py write \
  --sheet-id "SHEET_ID" \
  --range "Summary!A1" \
  --values '[["Total Sales","$125,000"]]'
```

## Error Handling

All scripts return JSON with consistent error format:

```json
{
  "success": false,
  "error": "Authentication failed: invalid_grant",
  "error_type": "AuthError",
  "retry_possible": true,
  "action": "Run: python3 scripts/google_auth.py --auth"
}
```

Common errors:

- **`invalid_grant`** - Token expired, run re-authentication
- **`quotaExceeded`** - API rate limit hit, wait and retry
- **`notFound`** - Resource doesn't exist (wrong ID)
- **`permissionDenied`** - Insufficient OAuth scopes

## Rate Limits

Google API quotas (default free tier):

| API      | Quota            | Reset Interval |
| -------- | ---------------- | -------------- |
| Gmail    | 250 sends/day    | Daily          |
| Gmail    | 1B queries/day   | Daily          |
| Calendar | 1M requests/day  | Daily          |
| Docs     | 300 requests/min | Per minute     |
| Sheets   | 300 requests/min | Per minute     |

**Mitigation strategies:**

- Batch operations where possible
- Cache responses
- Implement exponential backoff
- Monitor quota usage in Google Cloud Console

## Troubleshooting

### "Token has been expired or revoked"

```bash
# Re-authenticate
python3 scripts/google_auth.py --auth

# Check token status
python3 scripts/google_auth.py --check
```

### "Scope changed, re-consent required"

If you add new scopes, delete existing token and re-auth:

```bash
rm ~/.openclaw/google-workspace/token.json
python3 scripts/google_auth.py --auth
```

### "API not enabled"

Enable the required API in Google Cloud Console:

1. Go to https://console.cloud.google.com/apis/library
2. Search for the API (Gmail, Calendar, Docs, Sheets)
3. Click "Enable"

### Permission Issues

Check OAuth consent screen configuration:

- Internal apps: Only org users can use
- External apps: Requires Google verification for sensitive scopes

## Security Best Practices

1. **Never commit credentials** - Add to `.gitignore`:

   ```
   **/credentials.json
   **/token.json
   ~/.openclaw/google-workspace/
   ```

2. **Use service accounts for automation** - For production, prefer service accounts over user OAuth

3. **Rotate credentials regularly** - Generate new OAuth credentials quarterly

4. **Monitor OAuth grants** - Review at https://myaccount.google.com/permissions

5. **Enable 2FA** - Protect Google account with two-factor authentication

6. **Audit logs** - Enable Google Workspace audit logging for compliance

## See Also

- [SECURITY.md](SECURITY.md) - Complete threat model and hardening guide
- [Google API Python Client](https://github.com/googleapis/google-api-python-client)
- [Gmail API Documentation](https://developers.google.com/gmail/api)
- [Calendar API Documentation](https://developers.google.com/calendar/api)
- [Docs API Documentation](https://developers.google.com/docs/api)
- [Sheets API Documentation](https://developers.google.com/sheets/api)
- [OAuth 2.0 Scopes](https://developers.google.com/identity/protocols/oauth2/scopes)
