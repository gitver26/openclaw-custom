---
name: property-email-agent
description: "Automated property agent workflow: hourly Gmail monitoring, intelligent question detection, context-aware email drafting with RAG and conversation history"
tags: ["automation", "workflow", "email", "property-agent", "cron", "rag"]
version: 1.0.0
author: "openclaw"
requires:
  - python3
  - google-workspace skill
  - ragie skill
  - supabase skill
environment:
  - OPENAI_API_KEY (or ANTHROPIC_API_KEY for Claude)
  - All dependencies from google-workspace, ragie, supabase skills
---

# Property Email Agent Workflow

This skill orchestrates an **automated property agent workflow** that:

1. **Monitors Gmail hourly** for new prospect/client emails
2. **Classifies property-related questions** using pattern matching + LLM
3. **Searches Ragie.ai** for relevant property knowledge (market data, reports, etc.)
4. **Queries Supabase** for conversation history and client memory
5. **Drafts structured email replies** (300-450 words with headings/subheadings)
6. **Delivers draft to you** for review before sending (safe by default)

**Deployment model:** Runs as an OpenClaw cron job (hourly isolated agent turn).

---

## Overview

```
┌─────────────────────────────────────────────────────────────┐
│  HOURLY CRON JOB (OpenClaw Gateway Scheduler)              │
└─────────┬───────────────────────────────────────────────────┘
          │
          v
┌─────────────────────────────────────────────────────────────┐
│  1. Gmail Check                                             │
│     • List unread messages (last 1 hour)                    │
│     • Filter: from prospects/leads                          │
│     • Skip: autoresponders, newsletters                     │
└─────────┬───────────────────────────────────────────────────┘
          │
          v
┌─────────────────────────────────────────────────────────────┐
│  2. Property Question Detection                             │
│     • LLM classifier: Is this a property-related question?  │
│     • Examples: "good time to buy?", "hottest district?",   │
│       "cooling measures affect my HDB flat?"                │
│     • Skip: Non-property emails, invoices, spam             │
└─────────┬───────────────────────────────────────────────────┘
          │
          v
┌─────────────────────────────────────────────────────────────┐
│  3. Context Gathering (Parallel)                            │
│     ├─ Ragie.ai: Search property knowledge base             │
│     │  (market reports, cooling measures, district data)    │
│     └─ Supabase: Get client history                         │
│        (past conversations, preferences, meeting notes)     │
└─────────┬───────────────────────────────────────────────────┘
          │
          v
┌─────────────────────────────────────────────────────────────┐
│  4. Email Draft Generation                                  │
│     • LLM generates structured reply (300-450 words)        │
│     • Includes: headings, bullet points, source links       │
│     • Tone: Professional, helpful, data-driven              │
└─────────┬───────────────────────────────────────────────────┘
          │
          v
┌─────────────────────────────────────────────────────────────┐
│  5. Delivery for Review (Safe by Default)                   │
│     • Post draft to Slack/WhatsApp/Telegram for approval    │
│     • OR: Save as Gmail draft (no send)                     │
│     • Manual send after review                              │
└─────────────────────────────────────────────────────────────┘
```

---

## Prerequisites

### Required Skills

Install and configure these skills first:

1. **google-workspace** - Gmail API access
   - Follow setup in `/skills/google-workspace/SKILL.md`
   - Must have OAuth2 credentials configured
   - Required scopes: `gmail.readonly`, `gmail.send`, `gmail.modify`

2. **ragie** - Property knowledge base RAG
   - Follow setup in `/skills/ragie/SKILL.md`
   - Must have `RAGIE_API_KEY` in environment
   - Must have property documents indexed in Ragie

3. **supabase** - Conversation history database
   - Follow setup in `/skills/supabase/SKILL.md`
   - Must have `SUPABASE_URL` and `SUPABASE_SERVICE_KEY` in environment
   - Must have database schema created (see supabase skill docs)

### LLM API Key

For email classification and draft generation:

```bash
# Option 1: OpenAI
export OPENAI_API_KEY="sk-..."

# Option 2: Anthropic (Claude)
export ANTHROPIC_API_KEY="sk-ant-..."
```

### OpenClaw Gateway

This workflow runs as a cron job, so the Gateway must be running 24/7:

```bash
# Start Gateway (if not already running)
openclaw gateway run
```

---

## Setup

### Step 1: Test Individual Skills

Before orchestrating, verify each skill works:

```bash
# Test Gmail access
python3 ../google-workspace/scripts/gmail.py list --max-results 5

# Test Ragie search
python3 ../ragie/scripts/search.py \
  --query "property cooling measures Singapore" \
  --max-results 3

# Test Supabase connection
python3 ../supabase/scripts/test_connection.py

# Test contextgathering
python3 ../supabase/scripts/get_client_context.py \
  --email prospect@example.com
```

### Step 2: Configure Prospect Filter

Edit `config/prospect_domains.txt` to list email domains/addresses to monitor:

```text
# Prospect email patterns (one per line)
*@gmail.com
*@hotmail.com
prospect@example.com
client@company.com
# Add your client/prospect domains here
```

Or use the default: monitor all emails (filter by subject/content instead).

### Step 3: Deploy the Cron Job

```bash
# Add hourly cron job
openclaw cron add \
  --name "Property Email Agent" \
  --cron "0 * * * *" \
  --tz "Asia/Singapore" \
  --session isolated \
  --message "Check Gmail for property questions and draft replies" \
  --announce \
  --channel slack \
  --to "channel:C1234567890"

# Or webhook delivery:
openclaw cron add \
  --name "Property Email Agent" \
  --cron "0 * * * *" \
  --tz "Asia/Singapore" \
  --session isolated \
  --message "Check Gmail for property questions and draft replies" \
  --webhook \
  --to "https://your-webhook.example.com/drafts"
```

**Customization:**

- Change `--cron "0 * * * *"` to adjust frequency (hourly by default)
- Use `--announce` to post drafts to chat (Slack/WhatsApp/Telegram)
- Use `--webhook` to POST drafts to your backend
- Set `--tz` to your local timezone

### Step 4: Monitor the Workflow

```bash
# List cron jobs
openclaw cron list

# See job runs
openclaw cron runs --id <job-id> --limit 10

# Manually trigger (for testing)
openclaw cron run <job-id> --force
```

---

## Usage Examples

### Manual Workflow Run (Testing)

Before deploying the cron job, test the workflow manually:

```bash
# Process a specific email
python3 scripts/process_email.py \
  --email-id "msg_abc123xyz" \
  --debug

# Dry run (no database writes, no email sends)
python3 scripts/process_email.py \
  --email-id "msg_abc123xyz" \
  --dry-run
```

### Process Unread Emails

```bash
# Check last hour of unread emails
python3 scripts/check_gmail.py \
  --since "1h" \
  --unread-only

# Check specific time range
python3 scripts/check_gmail.py \
  --since "2026-03-03T10:00:00Z" \
  --until "2026-03-03T11:00:00Z"
```

### Classify Email as Property Question

```bash
# Test classifier on an email
python3 scripts/classify_email.py \
  --subject "Property inquiry" \
  --body "Is it a good time to buy property in District 9?" \
  --debug
```

### Generate Email Draft

```bash
# Full workflow: context gathering + draft generation
python3 scripts/draft_reply.py \
  --client-email "prospect@example.com" \
  --original-subject "Property inquiry" \
  --original-body "Is it a good time to buy in District 9?" \
  --query "District 9 Singapore property investment timing" \
  --debug
```

---

## Script Reference

### `check_gmail.py` - Gmail Monitoring

Lists unread emails within a time range.

**Parameters:**

- `--since` (default: "1h"): Time range start (duration or ISO timestamp)
- `--until` (optional): Time range end (ISO timestamp)
- `--unread-only` (flag): Only fetch unread messages
- `--debug`: Enable debug output

**Output (JSON):**

```json
{
  "emails": [
    {
      "id": "msg_abc123",
      "thread_id": "thread_xyz789",
      "from": "prospect@example.com",
      "subject": "Property inquiry",
      "snippet": "Is it a good time to buy...",
      "date": "2026-03-03T10:30:00Z"
    }
  ],
  "count": 1
}
```

### `classify_email.py` - Property Question Detection

Uses LLM to classify if email contains property-related questions.

**Parameters:**

- `--subject` (required): Email subject
- `--body` (required): Email body text
- `--from-email` (optional): Sender email (for context)
- `--debug`: Enable debug output

**Output (JSON):**

```json
{
  "is_property_question": true,
  "confidence": 0.95,
  "detected_topics": ["buying timing", "district analysis"],
  "reasoning": "Email asks about property investment timing in a specific district"
}
```

### `draft_reply.py` - Email Draft Generation

Orchestrates context gathering + draft generation.

**Parameters:**

- `--client-email` (required): Prospect/client email address
- `--original-subject` (required): Original email subject
- `--original-body` (required): Original email body
- `--query` (required): Search query for Ragie (extracted from email)
- `--thread-id` (optional): Gmail thread ID (for threading)
- `--dry-run`: Don't save draft or write to database
- `--debug`: Enable debug output

**Output (JSON):**

```json
{
  "draft": {
    "subject": "Re: Property inquiry",
    "body": "Dear John,\n\nThank you for your inquiry...",
    "word_count": 387
  },
  "context_used": {
    "ragie_chunks": 3,
    "supabase_conversations": 2,
    "supabase_memory": true
  },
  "saved_to": "gmail_draft"
}
```

### `process_email.py` - End-to-End Workflow

Full workflow: classify → gather context → draft reply → save.

**Parameters:**

- `--email-id` (required): Gmail message ID
- `--dry-run`: Don't save draft or write to database
- `--debug`: Enable debug output

---

## Email Draft Format

Generated email drafts follow this structure:

```
Subject: Re: [Original Subject]

Dear [Client Name],

Thank you for your inquiry about [topic]. Here's what you need to know:

## [Main Heading 1]

[2-3 paragraphs with data-driven insights from Ragie knowledge base]

Key points:
• [Bullet point 1]
• [Bullet point 2]
• [Bullet point 3]

## [Main Heading 2]

[Additional context based on client history from Supabase]

## Next Steps

[Clear call-to-action or offer for follow-up meeting]

Best regards,
[Your Name]
[Your Title]

---
📚 Sources:
• [Document 1 name] (via Ragie)
• [Meeting notes from [date]] (internal)
```

**Constraints:**

- 300-450 words (enforced by LLM prompt)
- 2-3 main headings (H2 level)
- Professional tone, data-driven
- Always include sources/attribution

---

## Cron Job Configuration

### Recommended Setup

```bash
# Production: Hourly monitoring with Slack delivery
openclaw cron add \
  --name "Property Email Agent" \
  --cron "0 * * * *" \
  --tz "Asia/Singapore" \
  --session isolated \
  --message "Run property email workflow (check Gmail, draft replies)" \
  --announce \
  --channel slack \
  --to "channel:C_PROPERTY_DRAFTS"
```

### Alternative: Business Hours Only

```bash
# Run only during business hours (9 AM - 6 PM, Mon-Fri)
openclaw cron add \
  --name "Property Email Agent (Business Hours)" \
  --cron "0 9-18 * * 1-5" \
  --tz "Asia/Singapore" \
  --session isolated \
  --message "Run property email workflow" \
  --announce \
  --channel WhatsApp \
  --to "+6591234567"
```

### High Frequency (Every 15 Minutes)

```bash
# For high-volume agents: check every 15 minutes
openclaw cron add \
  --name "Property Email Agent (15min)" \
  --cron "*/15 * * * *" \
  --tz "Asia/Singapore" \
  --session isolated \
  --message "Run property email workflow" \
  --announce
```

---

## Customization

### Adjust Email Classification

Edit `scripts/classify_email.py` to customize the LLM prompt:

```python
# Add domain-specific keywords
PROPERTY_KEYWORDS = [
    "buy", "sell", "invest", "property", "condo", "HDB",
    "district", "cooling measures", "ABSD", "resale", "BTO",
    "rental yield", "capital appreciation", "mortgage",
]

# Adjust confidence threshold
CLASSIFICATION_THRESHOLD = 0.7  # Default: 0.7 (70% confidence)
```

### Customize Draft Template

Edit `scripts/draft_reply.py` to adjust the LLM prompt for email generation:

```python
DRAFT_PROMPT_TEMPLATE = """
You are a professional Singapore property agent...
[Customize tone, structure, constraints here]
"""
```

### Add Custom Delivery Channels

The cron job can deliver to multiple channels:

```bash
# Multiple announcements (Slack + WhatsApp)
# (Not directly supported - use webhook + custom fanout)

# Webhook to your backend for custom processing
openclaw cron add \
  --name "Property Email Agent" \
  --cron "0 * * * *" \
  --session isolated \
  --message "Run workflow" \
  --webhook \
  --to "https://your-backend.com/api/email-drafts"
```

---

## Error Handling

### Common Issues

**"Gmail API quota exceeded"**

- Gmail API: 1 billion quota units/day (free tier)
- Reading emails: 5 units each
- Sending emails: 100 units each
- Solution: Reduce cron frequency or upgrade to Google Workspace

**"Ragie API rate limit"**

- Free tier: 1000 requests/month
- Solution: Cache frequent queries or upgrade Ragie plan

**"Supabase connection timeout"**

- Free tier pauses after 1 week inactivity
- Solution: Wake project in Supabase dashboard or upgrade

**"LLM classification errors"**

- Increase temperature for less strict matching
- Adjust confidence threshold in `classify_email.py`

### Debug Mode

```bash
# Enable full debug logging
python3 scripts/check_gmail.py --debug
python3 scripts/classify_email.py --debug
python3 scripts/draft_reply.py --debug
```

### Dry Run Mode

Test workflow without side effects:

```bash
# No writes to database, no email sends, no drafts saved
python3 scripts/process_email.py \
  --email-id "msg_abc123" \
  --dry-run
```

---

## Security & Privacy

### Data Handling

- **Gmail**: Only accesses your Gmail (OAuth scoped access)
- **Ragie**: Searches your property documents (stored on Ragie servers)
- **Supabase**: Stores conversation history in your database
- **LLM providers**: Email content sent to OpenAI/Anthropic for classification & drafting

⚠️ **GDPR/PDPA Compliance:**

- Client emails may contain personal data (PII)
- Ensure your LLM provider terms allow processing customer data
- Consider data retention policies in Supabase
- Inform clients about automated email processing (transparency)

### OAuth Token Security

- Gmail tokens stored at `~/.openclaw/credentials/` (chmod 600)
- Never commit tokens to git
- Revoke tokens via Google Account settings if compromised

### API Key Security

All API keys must be in environment variables, never hardcoded:

```bash
# ✅ GOOD
export RAGIE_API_KEY="..."
export SUPABASE_SERVICE_KEY="..."

# ❌ BAD (never do this)
# API_KEY = "sk-12345"  # in source code
```

**See SECURITY.md for comprehensive threat model and incident response procedures.**

---

## Cost Estimation

Monthly cost for moderate usage (100 emails/day processed):

| Service      | Usage                | Cost                 |
| ------------ | -------------------- | -------------------- |
| Gmail API    | 100 reads/day        | Free (within quota)  |
| Ragie.ai     | 3,000 searches/month | $29/month (Pro plan) |
| Supabase     | Queries + storage    | Free (within limits) |
| OpenAI GPT-4 | ~200K tokens/month   | ~$6/month            |
| **Total**    |                      | **~$35/month**       |

**Cost optimization:**

- Use GPT-3.5-turbo for classification (10x cheaper)
- Cache Ragie results for frequent queries
- Batch process emails (reduce API calls)

---

## Monitoring & Analytics

### Cron Job Logs

```bash
# View last 20 runs
openclaw cron runs --id <job-id> --limit 20

# Filter by status
openclaw cron runs --id <job-id> --status success
openclaw cron runs --id <job-id> --status error
```

### Database Analytics

```bash
# Count total conversations
python3 ../supabase/scripts/query.py \
  --table conversations \
  --select "count"

# Get daily email volume
python3 scripts/analytics/daily_volume.py --days 30
```

### Success Metrics

Track these in Supabase or your analytics platform:

- Emails processed per hour
- Property questions detected (vs false positives)
- Drafts generated vs sent (conversion rate)
- Average response time (email received → draft ready)

---

## Troubleshooting

### Workflow Not Running

```bash
# Check Gateway is running
openclaw gateway status

# Verify cron job is enabled
openclaw cron list

# Check job's last run
openclaw cron runs --id <job-id> --limit 1

# Manually trigger
openclaw cron run <job-id> --force
```

### No Emails Detected

```bash
# Test Gmail access
python3 ../google-workspace/scripts/gmail.py list

# Check time range
python3 scripts/check_gmail.py --since "24h" --debug

# Verify OAuth scopes
python3 ../google-workspace/scripts/google_auth.py check-status
```

### Classification Not Working

```bash
# Test classifier directly
python3 scripts/classify_email.py \
  --subject "Test" \
  --body "Is it a good time to buy property?" \
  --debug

# Check LLM API key
env | grep -E "OPENAI|ANTHROPIC"
```

### Draft Quality Issues

- Adjust LLM temperature (higher = more creative, lower = more focused)
- Improve Ragie document quality (better source data = better drafts)
- Add more client context in Supabase (preferences, past conversations)
- Customize the draft template prompt

---

## Related Skills

- **google-workspace**: Gmail, Calendar, Docs integration
- **ragie**: RAG search for property knowledge base
- **supabase**: Conversation history and client memory
- **scrapling**: Web scraping for property listings (complementary)

---

## Roadmap

Future enhancements (not yet implemented):

- [ ] Multi-language support (English, Mandarin, Malay)
- [ ] Calendar integration (auto-schedule viewings)
- [ ] WhatsApp Business API integration (move beyond email)
- [ ] A/B testing for draft templates
- [ ] Sentiment analysis for client priority scoring
- [ ] Auto-send for high-confidence drafts (with approval workflow)

---

## References

- [OpenClaw Cron Jobs](../../docs/automation/cron-jobs.md)
- [Gmail API Quotas](https://developers.google.com/gmail/api/reference/quota)
- [Ragie.ai Best Practices](https://docs.ragie.ai/guides/rag-best-practices)
- [Supabase Row Level Security](https://supabase.com/docs/guides/auth/row-level-security)

---

## Changelog

### v1.0.0 (2026-03-03)

- Initial release
- Hourly Gmail monitoring via cron
- Property question classification
- Ragie + Supabase context gathering
- Email draft generation (300-450 words)
- Multi-channel delivery (Slack, WhatsApp, webhook)
