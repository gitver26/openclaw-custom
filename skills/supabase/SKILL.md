---
name: supabase
description: "Supabase database integration for storing and querying conversation history, memory, meeting notes, and client interactions"
tags: ["database", "memory", "conversation-history", "crm"]
version: 1.0.0
author: "openclaw"
requires:
  - python3
  - supabase-py
environment:
  - SUPABASE_URL
  - SUPABASE_SERVICE_KEY
---

# Supabase Database Integration Skill

This skill provides database operations through [Supabase](https://supabase.com), enabling storage and retrieval of conversation history, client memory, meeting notes, and structured data for property agent workflows.

## Overview

Supabase is an open-source Firebase alternative that provides:

- PostgreSQL database with full SQL support
- RESTful API with automatic CRUD endpoints
- Real-time subscriptions
- Row-level security (RLS)
- Vector storage for embeddings (pgvector extension)

**Use this skill when you need to:**

- Query conversation history with prospects/clients
- Store and retrieve client preferences and requirements
- Search through meeting notes and follow-up tasks
- Track property viewings, offers, and deal pipeline
- Maintain memory across agent sessions

---

## Prerequisites

### 1. Supabase Project Setup

1. Sign up at [https://supabase.com](https://supabase.com)
2. Create a new project (note: initial provisioning takes ~2 minutes)
3. Get your project URL and service key:
   - Go to Settings → API
   - Copy "Project URL" (e.g., `https://xyz.supabase.co`)
   - Copy "service_role secret" key (starts with `eyJ...`)

⚠️ **Security:** Use `service_role` key only in secure server environments. For browser/client access, use `anon` key with Row Level Security (RLS).

### 2. Environment Configuration

Store credentials securely:

```bash
# Add to your environment
export SUPABASE_URL="https://your-project.supabase.co"
export SUPABASE_SERVICE_KEY="eyJ..."

# Or use OpenClaw config
openclaw config set env.SUPABASE_URL "https://your-project.supabase.co"
openclaw config set env.SUPABASE_SERVICE_KEY "eyJ..."
```

### 3. Install Dependencies

```bash
pip3 install supabase
```

### 4. Database Schema Setup

Create tables for property agent data:

```sql
-- Conversation history table
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

-- Create index for fast email lookups
CREATE INDEX idx_conversations_email ON conversations(client_email);
CREATE INDEX idx_conversations_created ON conversations(created_at DESC);

-- Client memory/preferences table
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

-- Meeting notes table
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

-- Property viewings/interactions table
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

Run this SQL in Supabase Dashboard → SQL Editor → New Query.

---

## Usage Examples

### Query Conversation History

```bash
# Get recent conversations with a client
python3 scripts/query.py \
  --table conversations \
  --filter "client_email=eq.prospect@example.com" \
  --order "created_at.desc" \
  --limit 10

# Search for conversations about a topic
python3 scripts/query.py \
  --table conversations \
  --filter "message_body=ilike.*cooling measures*" \
  --limit 5
```

### Retrieve Client Memory

```bash
# Get client preferences and history
python3 scripts/query.py \
  --table client_memory \
  --filter "client_email=eq.prospect@example.com" \
  --single

# Get all clients interested in District 9
python3 scripts/query.py \
  --table client_memory \
  --filter "preferred_districts=cs.{District 9}"
```

### Search Meeting Notes

```bash
# Get all meeting notes for a client
python3 scripts/query.py \
  --table meeting_notes \
  --filter "client_email=eq.prospect@example.com" \
  --order "meeting_date.desc"

# Find meetings with pending follow-ups
python3 scripts/query.py \
  --table meeting_notes \
  --filter "follow_up_date=lte.2026-03-10,follow_up_date=gte.2026-03-01" \
  --order "follow_up_date.asc"
```

### Insert New Data

```bash
# Store a new conversation
python3 scripts/insert.py \
  --table conversations \
  --data '{
    "client_email": "prospect@example.com",
    "client_name": "John Tan",
    "subject": "Property inquiry",
    "message_body": "Is it a good time to buy in District 9?",
    "direction": "inbound",
    "channel": "email"
  }'

# Update client memory
python3 scripts/upsert.py \
  --table client_memory \
  --match "client_email" \
  --data '{
    "client_email": "prospect@example.com",
    "client_name": "John Tan",
    "preferences": {"property_type": ["condo"], "bedrooms": "3-4"},
    "preferred_districts": ["District 9", "District 10"],
    "last_interaction": "2026-03-03T10:30:00Z"
  }'
```

### Full-Text Search

```bash
# Search across all text fields (requires PostgreSQL full-text search setup)
python3 scripts/search.py \
  --table conversations \
  --column message_body \
  --query "cooling measures HDB resale" \
  --limit 10
```

---

## Script Reference

### `query.py` - Query Database

Fetch rows from any table with filtering and ordering.

**Parameters:**

- `--table` (required): Table name
- `--filter`: PostgREST filter string (e.g., `email=eq.test@example.com`)
- `--order`: Order by column (e.g., `created_at.desc`)
- `--limit` (default: 100): Maximum rows to return
- `--offset` (default: 0): Pagination offset
- `--select`: Columns to select (default: `*`)
- `--single`: Return single row instead of array
- `--debug`: Enable debug output

**Filter Examples:**

- Equality: `email=eq.prospect@example.com`
- Like: `message_body=ilike.*property*`
- Greater than: `created_at=gt.2026-03-01`
- In array: `property_type=cs.{condo,apartment}`

**Output (JSON):**

```json
{
  "data": [
    {
      "id": "123e4567-e89b-12d3-a456-426614174000",
      "client_email": "prospect@example.com",
      "message_body": "Is it a good time to buy?",
      "created_at": "2026-03-03T10:30:00Z"
    }
  ],
  "count": 1
}
```

### `insert.py` - Insert Rows

Insert new rows into a table.

**Parameters:**

- `--table` (required): Table name
- `--data` (required): JSON object or array of objects to insert
- `--debug`: Enable debug output

### `upsert.py` - Upsert (Insert or Update)

Insert new row or update if exists (based on unique constraint).

**Parameters:**

- `--table` (required): Table name
- `--match` (required): Column(s) to match for conflict (e.g., `client_email`)
- `--data` (required): JSON object to upsert
- `--debug`: Enable debug output

### `search.py` - Full-Text Search

Perform PostgreSQL full-text search on a column.

**Parameters:**

- `--table` (required): Table name
- `--column` (required): Column to search
- `--query` (required): Search query
- `--limit` (default: 10): Maximum results
- `--debug`: Enable debug output

### `execute_sql.py` - Raw SQL Queries

Execute custom SQL queries (use with caution).

**Parameters:**

- `--query` (required): SQL query string
- `--debug`: Enable debug output

**Security:** Only use with trusted input. No parameterization.

---

## Integration with Property Email Agent

This skill is designed towork with the Property Email Agent workflow:

```bash
# 1. Email arrives from prospect@example.com

# 2. Query conversation history
python3 scripts/query.py \
  --table conversations \
  --filter "client_email=eq.prospect@example.com" \
  --order "created_at.desc" \
  --limit 5

# 3. Retrieve client memory/preferences
python3 scripts/query.py \
  --table client_memory \
  --filter "client_email=eq.prospect@example.com" \
  --single

# 4. Search meeting notes
python3 scripts/query.py \
  --table meeting_notes \
  --filter "client_email=eq.prospect@example.com" \
  --order "meeting_date.desc" \
  --limit 3

# 5. Draft reply with context (see property-email-agent skill)

# 6. Store the outbound reply
python3 scripts/insert.py \
  --table conversations \
  --data '{
    "client_email": "prospect@example.com",
    "subject": "Re: Property inquiry",
    "message_body": "...",
    "direction": "outbound",
    "channel": "email"
  }'
```

---

## Common Patterns

### Get Client Context

Fetch all relevant data for a client in one go:

```bash
# Create a composite query helper
python3 scripts/get_client_context.py --email prospect@example.com
```

(See `scripts/get_client_context.py` for implementation)

### Track Email Threading

Store Gmail thread IDs in metadata:

```bash
python3 scripts/insert.py \
  --table conversations \
  --data '{
    "client_email": "prospect@example.com",
    "message_body": "...",
    "metadata": {
      "gmail_thread_id": "thread_abc123",
      "gmail_message_id": "msg_xyz789"
    }
  }'
```

### Pagination

```bash
# Page 1 (rows 0-99)
python3 scripts/query.py --table conversations --limit 100 --offset 0

# Page 2 (rows 100-199)
python3 scripts/query.py --table conversations --limit 100 --offset 100
```

---

## Error Handling

### Common Issues

**"Connection refused"**

- Verify `SUPABASE_URL` is correct
- Check network connectivity
- Ensure project is not paused (free tier pauses after 1 week inactivity)

**"Invalid API key"**

- Verify `SUPABASE_SERVICE_KEY` is correct
- Check key format: should start with `eyJ`
- Regenerate key in Supabase dashboard if compromised

**"Table does not exist"**

- Run database schema setup (see Prerequisites)
- Check table name spelling

**"Row level security policy violation"**

- Use `service_role` key (not `anon` key) for bypassing RLS
- Or configure RLS policies appropriately

---

## Rate Limits & Cost

Supabase pricing (as of March 2026):

- **Free**: 500MB database, 1GB bandwidth, 2GB file storage
- **Pro**: 8GB database, 50GB bandwidth ($25/month)
- **Team/Enterprise**: Custom limits

**Best practices:**

- Use connection pooling for high-traffic applications
- Add database indexes for frequent queries
- Archive old conversations to keep database small
- Monitor usage in Supabase Dashboard → Settings → Usage

---

## Security & Privacy

### API Key Security

```bash
# ✅ GOOD: Environment variable
export SUPABASE_SERVICE_KEY="eyJ..."

# ❌ BAD: Hardcoded
# Never do this!
```

### Row Level Security (RLS)

Enable RLS for production:

```sql
-- Enable RLS on conversations table
ALTER TABLE conversations ENABLE ROW LEVEL SECURITY;

-- Create policy for service role (full access)
CREATE POLICY "Service role full access"
  ON conversations
  FOR ALL
  TO service_role
  USING (true)
  WITH CHECK (true);

-- Create policy for anon users (read-only, own data)
CREATE POLICY "Users see own conversations"
  ON conversations
  FOR SELECT
  TO anon
  USING (client_email = current_setting('request.jwt.claims', true)::json->>'email');
```

### Data Encryption

- Data encrypted at rest (AES-256)
- TLS 1.3 for data in transit
- Database backups encrypted

### GDPR Compliance

For property agent use case:

- Client data may be subject to GDPR/PDPA
- Implement data retention policies (auto-delete old rows)
- Provide data export/deletion on request

```sql
-- Delete client data (GDPR right to erasure)
DELETE FROM conversations WHERE client_email = 'prospect@example.com';
DELETE FROM client_memory WHERE client_email = 'prospect@example.com';
DELETE FROM meeting_notes WHERE client_email = 'prospect@example.com';
```

**See SECURITY.md for comprehensive threat model and mitigation strategies.**

---

## Troubleshooting

### Debug Mode

```bash
# Enable verbose logging
python3 scripts/query.py --table conversations --debug
```

### Test Connection

```bash
# Verify credentials and connectivity
python3 scripts/test_connection.py
```

### Check Database Schema

```bash
# List all tables
python3 scripts/execute_sql.py \
  --query "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"
```

---

## Related Skills

- **google-workspace**: Import Gmail conversations automatically
- **ragie**: Combine conversation context with property knowledge base
- **property-email-agent**: Orchestrator that uses this skill

---

## References

- [Supabase Documentation](https://supabase.com/docs)
- [PostgREST API Reference](https://postgrest.org/en/stable/api.html)
- [PostgreSQL Full-Text Search](https://www.postgresql.org/docs/current/textsearch.html)
- [Row Level Security Guide](https://supabase.com/docs/guides/auth/row-level-security)

---

## Changelog

### v1.0.0 (2026-03-03)

- Initial release
- CRUD operations (query, insert, upsert)
- Full-text search support
- Property agent schema examples
- Client context retrieval
