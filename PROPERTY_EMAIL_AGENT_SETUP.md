# Property Email Agent Setup

This document explains how to deploy the **Property Email Agent** - an automated workflow that monitors Gmail hourly, detects property-related questions, and drafts intelligent replies using RAG (Ragie.ai) and conversation history (Supabase).

## Overview

The Property Email Agent orchestrates three OpenClaw skills:

1. **Ragie** (`/skills/ragie/`) - RAG search through property documents in Google Drive
2. **Supabase** (`/skills/supabase/`) - Store and query conversation history, client memory
3. **Property Email Agent** (`/skills/property-email-agent/`) - Workflow orchestrator

## Workflow

```
Hourly Cron Job
    ↓
Check Gmail (unread emails, last 1 hour)
    ↓
Classify: Property question? (LLM)
    ↓
Gather Context (parallel):
    ├─ Ragie: Search property knowledge base
    └─ Supabase: Get client history
    ↓
Generate Draft (LLM, 300-450 words)
    ↓
Deliver to Slack/WhatsApp for review
```

## Quick Start (15 minutes)

### 1. Prerequisites

Install all required skills and dependencies:

```bash
# 1. Google Workspace (Gmail API)
cd skills/google-workspace
pip3 install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client

# Follow SKILL.md OAuth2 setup (requires Google Cloud Console)
python3 scripts/google_auth.py authenticate

cd ../..

# 2. Ragie.ai (RAG)
cd skills/ragie
pip3 install requests

# Sign up at https://ragie.ai and get API key
export RAGIE_API_KEY="ragie_sk_..."

# Test connection
python3 scripts/test_connection.py

cd ../..

# 3. Supabase (Database)
cd skills/supabase
pip3 install supabase

# Create project at https://supabase.com and get credentials
export SUPABASE_URL="https://your-project.supabase.co"
export SUPABASE_SERVICE_KEY="eyJ..."

# Test connection
python3 scripts/test_connection.py

cd../..

# 4. LLM API (for classification + drafting)
export OPENAI_API_KEY="sk-..."  # Or ANTHROPIC_API_KEY

# 5. Install OpenAI/Anthropic client
pip3 install openai  # Or: pip3 install anthropic
```

### 2. Setup Supabase Database Schema

Go to Supabase Dashboard → SQL Editor, run:

```sql
-- Conversation history
CREATE TABLE conversations (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  client_email TEXT NOT NULL,
  client_name TEXT,
  subject TEXT,
  message_body TEXT,
  direction TEXT CHECK (direction IN ('inbound', 'outbound')),
  channel TEXT DEFAULT 'email',
  agent_id TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  metadata JSONB
);

CREATE INDEX idx_conversations_email ON conversations(client_email);
CREATE INDEX idx_conversations_created ON conversations(created_at DESC);

-- Client memory/preferences
CREATE TABLE client_memory (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  client_email TEXT NOT NULL UNIQUE,
  client_name TEXT,
  preferences JSONB,
  requirements JSONB,
  budget_range JSONB,
  preferred_districts TEXT[],
  property_type TEXT[],
  last_interaction TIMESTAMPTZ,
  notes TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Meeting notes
CREATE TABLE meeting_notes (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  client_email TEXT NOT NULL,
  meeting_date TIMESTAMPTZ NOT NULL,
  meeting_type TEXT,
  notes TEXT NOT NULL,
  action_items JSONB,
  follow_up_date TIMESTAMPTZ,
  properties_discussed TEXT[],
  created_by TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_meeting_notes_email ON meeting_notes(client_email);
CREATE INDEX idx_meeting_notes_date ON meeting_notes(meeting_date DESC);

-- Property interactions
CREATE TABLE property_interactions (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  client_email TEXT NOT NULL,
  property_id TEXT,
  property_address TEXT,
  interaction_type TEXT CHECK (interaction_type IN ('viewing', 'inquiry', 'offer', 'callback')),
  interaction_date TIMESTAMPTZ DEFAULT NOW(),
  notes TEXT,
  status TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_property_interactions_email ON property_interactions(client_email);
```

### 3. Index Property Documents in Ragie

1. Go to [https://ragie.ai/dashboard](https://ragie.ai/dashboard)
2. Connect your Google Drive (or upload documents manually)
3. Wait for indexing to complete (~5-30 minutes depending on document count)
4. Test search:

```bash
cd skills/ragie
python3 scripts/search.py \
  --query "Singapore property cooling measures ABSD" \
  --max-results 3
```

### 4. Test the Workflow Manually

```bash
cd skills/property-email-agent/scripts

# Test classification
python3 classify_email.py \
  --subject "Property inquiry" \
  --body "Is it a good time to buy property in District 9?" \
  --debug

# Test draft generation
python3 draft_reply.py \
  --client-email "prospect@example.com" \
  --original-subject "Property inquiry" \
  --original-body "Is it a good time to buy in District 9?" \
  --query "District 9 property investment timing Singapore" \
  --debug
```

### 5. Deploy Cron Job

```bash
# Add hourly workflow (runs at start of every hour)
openclaw cron add \
  --name "Property Email Agent" \
  --cron "0 * * * *" \
  --tz "Asia/Singapore" \
  --session isolated \
  --message "Run property email workflow: check Gmail, draft replies" \
  --announce \
  --channel slack \
  --to "channel:C1234567890"

# List jobs to verify
openclaw cron list

# Manually trigger for testing
openclaw cron run <job-id> --force

# Watch logs
openclaw cron runs --id <job-id> --limit 10
```

### 6. Monitor & Iterate

```bash
# Check recent runs
openclaw cron runs --id <job-id> --limit 20

# View emails processed
python3 skills/supabase/scripts/query.py \
  --table conversations \
  --order "created_at.desc" \
  --limit 10

# Check draft quality
# (Drafts delivered to your Slack/WhatsApp)
```

---

## Configuration

### Adjust Workflow Frequency

```bash
# Every 30 minutes (higher frequency)
--cron "*/30 * * * *"

# Every 2 hours
--cron "0 */2 * * *"

# Business hours only (9 AM - 6 PM, Mon-Fri)
--cron "0 9-18 * * 1-5"
```

### Change Delivery Channel

```bash
# WhatsApp
--announce --channel whatsapp --to "+6591234567"

# Telegram
--announce --channel telegram --to "-1001234567890"

# Webhook (POST to your backend)
--webhook --to "https://your-api.com/email-drafts"
```

### Customize Classification

Edit `skills/property-email-agent/scripts/classify_email.py`:

```python
# Adjust confidence threshold
CLASSIFICATION_THRESHOLD = 0.7  # 0.0-1.0

# Add custom keywords
PROPERTY_KEYWORDS = [
    "buy", "sell", "invest", "HDB", "condo",
    # Add more...
]
```

### Customize Draft Template

Edit `skills/property-email-agent/scripts/draft_reply.py`:

```python
DRAFT_PROMPT_TEMPLATE = """
You are a professional Singapore property agent...
[Modify tone, structure, constraints]
"""
```

---

## Architecture

### Skills

1. **Ragie (`/skills/ragie/`)**
   - `search.py` - Semantic search across property documents
   - `list_documents.py` - List indexed files
   - `test_connection.py` - Verify API credentials

2. **Supabase (`/skills/supabase/`)**
   - `query.py` - Query database tables
   - `insert.py` - Insert new rows
   - `upsert.py` - Update or insert
   - `get_client_context.py` - **Fetch all client data** (conversations, memory, notes)
   - `test_connection.py` - Verify database connection

3. **Property Email Agent (`/skills/property-email-agent/`)**
   - `check_gmail.py` - List unread emails in time range
   - `classify_email.py` - LLM-based property question detector
   - `draft_reply.py` - **Orchestrator**: context gathering + draft generation

### Data Flow

```
Gmail API → check_gmail.py → classify_email.py (LLM) →
  ├─ Ragie API (search.py) → property knowledge chunks
  └─ Supabase (get_client_context.py) → client history
    → draft_reply.py (LLM) → structured email draft
      → Slack/WhatsApp/Webhook (for review)
```

---

## Troubleshooting

### "Gmail API quota exceeded"

- Free tier: 1 billion quota units/day (reading = 5 units each)
- Solution: Reduce cron frequency or upgrade to Google Workspace

### "Ragie API rate limit"

- Free tier: 1000 requests/month
- Solution: Cache results or upgrade plan

### "Supabase connection timeout"

- Free tier pauses after 1 week inactivity
- Solution: Wake project in dashboard or upgrade

### "No LLM API key found"

- Ensure `OPENAI_API_KEY` or `ANTHROPIC_API_KEY` is set
- Add to `~/.zshrc` or `~/.bashrc` and reload shell

### "Empty Ragie results"

- Check documents are indexed: `python3 skills/ragie/scripts/list_documents.py`
- Try broader search queries
- Verify document formats (PDF, DOCX, TXT supported)

### "Classification not working"

- Enable `--debug` to see LLM prompts
- Adjust confidence threshold in `classify_email.py`
- Try different LLM provider (GPT-4 vs Claude)

---

## Cost Estimation

Monthly cost for moderate usage (~100 emails/day):

| Service       | Usage                | Cost           |
| ------------- | -------------------- | -------------- |
| Gmail API     | Free tier            | $0             |
| Ragie.ai Pro  | 3,000 searches/month | $29/month      |
| Supabase Free | Queries + storage    | $0             |
| OpenAI GPT-4  | ~200K tokens/month   | ~$6/month      |
| **Total**     |                      | **~$35/month** |

**Cost optimization:**

- Use GPT-3.5-turbo for classification (10x cheaper)
- Cache Ragie results for common queries
- Batch process emails (reduce API calls)

---

## Security & Privacy

- **Gmail**: OAuth2 scoped access (tokens stored at `~/.openclaw/credentials/`)
- **Ragie**: Property documents stored on Ragie servers (encrypted at rest + in transit)
- **Supabase**: Your database (full control, RLS optional)
- **LLM**: Email content sent to OpenAI/Anthropic for processing

⚠️ **GDPR/PDPA Compliance:**

- Client emails may contain PII (personal identifiable information)
- Ensure LLM provider terms allow customer data processing
- Implement data retention policies in Supabase
- Inform clients about automated email processing

**See individual SECURITY.md files in each skill folder for comprehensive threat models.**

---

## Examples

### Example Email Flow

**1. Prospect sends email:**

```
From: john.tan@gmail.com
Subject: Property inquiry
Body: Hi, is it a good time to buy property in District 9?
What are the latest cooling measures affecting condo buyers?
```

**2. Workflow detects property question (classification = 95% confidence)**

**3. Context gathering:**

- **Ragie**: Finds 3 relevant documents:
  - "Q1 2026 Property Market Report" (District 9 trends)
  - "ABSD Cooling Measures Guide 2025"
  - "District 9 Investment Analysis"
- **Supabase**: Finds client history:
  - 2 previous conversations (last: 3 weeks ago)
  - Client preferences: 3-bedroom condos, budget $2-2.5M
  - Meeting note from Feb 15: interested in Newton area

**4. Draft generated (412 words):**

```
Subject: Re: Property inquiry

Dear John,

Thank you for your inquiry about investing in District 9.
Based on our latest market data and your previous preferences,
here's what you need to know:

## Current Market Conditions (Q1 2026)

District 9 remains one of Singapore's prime investment districts...
[Data-driven analysis with bullet points]

## Cooling Measures Impact

The latest ABSD adjustments affect condo buyers...
[Specific calculations based on client profile]

## Next Steps

I recommend we schedule a viewing for the Newton area properties
we discussed in our February meeting...

Best regards,
[Agent Name]

---
Sources:
• Q1 2026 Property Market Report (Ragie)
• Meeting notes from 2026-02-15 (Supabase)
```

**5. Draft posted to Slack for agent review → Manual send**

---

## Roadmap

- [ ] Multi-language support (English, Mandarin, Malay)
- [ ] Calendar integration (auto-schedule viewings)
- [ ] WhatsApp Business API (move beyond email)
- [ ] Auto-send for high-confidence drafts (with approval workflow)
- [ ] A/B testing for draft templates
- [ ] Sentiment analysis for client priority scoring

---

## Support & References

- OpenClaw Cron Jobs: [docs/automation/cron-jobs.md](docs/automation/cron-jobs.md)
- Gmail API: [developers.google.com/gmail/api](https://developers.google.com/gmail/api)
- Ragie.ai: [docs.ragie.ai](https://docs.ragie.ai)
- Supabase: [supabase.com/docs](https://supabase.com/docs)

---

**Built with ❤️ for property agents using OpenClaw**
