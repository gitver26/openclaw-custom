# Supabase Skill - Security Documentation

**Version:** 1.0.0  
**Last Updated:** 2026-03-03  
**Risk Level:** High (stores PII + conversation history)

---

## Executive Summary

The Supabase skill provides PostgreSQL database operations for storing conversation history, client memory, meeting notes, and property interactions. As the system of record for client data, it represents **high security risk**: database compromise exposes all client PII, business intelligence, and communication history.

**Key risks:**

- Service role key compromise → full database access (read/write/delete)
- SQL injection → data exfiltration or corruption
- Accidental data deletion → loss of client history
- GDPR/PDPA violations → regulatory penalties
- Cost escalation from runaway queries

This document applies the **4-layer security framework** (Architecture, Governance, Monetization, Messaging) to mitigate these risks.

---

## Threat Model

### Attack Vectors

| Vector                        | Impact                       | Likelihood | Mitigation Priority |
| ----------------------------- | ---------------------------- | ---------- | ------------------- |
| **Service key theft**         | Complete database access     | High       | **Critical**        |
| **SQL injection**             | Data exfiltration/corruption | Medium     | **Critical**        |
| **Accidental deletion**       | Loss of client history       | Medium     | High                |
| **Row Level Security bypass** | Unauthorized data access     | Low        | High                |
| **Query performance DoS**     | Service disruption           | Low        | Medium              |
| **Backup compromise**         | Historical data exposure     | Low        | Low                 |

---

## Layer 1: Architecture (Verifiable Completion)

**Principle:** Database writes must be atomic, validated, and auditable. No "fire and forget."

### Verifiable Completion States

#### BAD: Unverified Write

```python
# ❌ No confirmation of write success
def store_conversation(email, body):
    supabase.table("conversations").insert({"client_email": email, "message_body": body})
    return  # Did it succeed? Was it written?
```

#### GOOD: Verified Write with Return

```python
# ✅ Verify write succeeded + return inserted ID
def store_conversation(email, body):
    result = supabase.table("conversations").insert({
        "client_email": email,
        "message_body": body,
        "created_at": datetime.utcnow().isoformat(),
    }).execute()

    if not result.data:
        raise DatabaseError("Failed to insert conversation")

    inserted_id = result.data[0]["id"]
    log_audit("conversation_stored", {"id": inserted_id, "email": email})

    return {
        "id": inserted_id,
        "verified": True,
        "timestamp": result.data[0]["created_at"]
    }
```

**Enforcement:** All `insert.py`/`upsert.py` operations return inserted record IDs.

### State Machine: Database Lifecycle

```
[Data Prepared]
    ↓
[Validation] → (Schema check, field types)
    ↓
[Transaction Start]
    ↓
[Write to DB]
    |
    ├─ Success → [Commit] → [Return Verified ID]
    └─ Failure → [Rollback] → [Log Error + Alert]
```

### Input Validation (SQL Injection Prevention)

#### BAD: No Validation

```python
# ❌ Direct user input → database (SQL injection risk even with ORM)
def get_conversations(email):
    return supabase.table("conversations").select("*").eq("client_email", email).execute()
```

#### GOOD: Validated Input

```python
# ✅ Validate email format before query
import re

EMAIL_REGEX = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'

def get_conversations(email: str):
    # Validate email format
    if not re.match(EMAIL_REGEX, email):
        raise ValueError(f"Invalid email format: {email}")

    # Length check
    if len(email) > 254:  # RFC 5321 max
        raise ValueError("Email too long")

    # Query with validated input
    result = supabase.table("conversations") \
        .select("*") \
        .eq("client_email", email) \
        .execute()

    return result.data
```

**Implementation:** Add validation to all scripts in `scripts/` folder.

### Artifact Validation (Response Integrity)

```python
# Validate database responses before returning to agent
def validate_response(data: Any) -> bool:
    if data is None:
        return False

    # Check for SQL error messages in response (defense in depth)
    if isinstance(data, dict) and "error" in data:
        raise DatabaseError(f"Query returned error: {data['error']}")

    return True
```

---

## Layer 2: Governance (Default-Deny)

**Principle:** Database access is tiered. Read-only by default, write requires approval.

### Three-Tier Access Model

#### Tier 0: Read-Only (Default)

```json
{
  "agents": {
    "list": [
      {
        "id": "main",
        "tools": {
          "allow": ["supabase_query"], // Read only
          "deny": ["supabase_insert", "supabase_update", "supabase_delete"]
        }
      }
    ]
  }
}
```

#### Tier 1: Supervised Write (Approval Required)

```json
{
  "agents": {
    "list": [
      {
        "id": "main",
        "tools": {
          "allow": ["supabase_query", "supabase_insert", "supabase_upsert"],
          "exec": {
            "approval": "required", // Operator reviews before write
            "approvalMsg": "Agent wants to write to database: {operation}"
          }
        }
      }
    ]
  }
}
```

#### Tier 2: Production-Grade (Audited Auto-Write)

```json
{
  "agents": {
    "list": [
      {
        "id": "main",
        "tools": {
          "allow": ["supabase_*"], // All operations
          "exec": {
            "approval": "none",
            "audit": "all" // Log every operation
          }
        }
      }
    ]
  }
}
```

**Recommendation:** Start with Tier 0, graduate to Tier 1, then Tier 2 after observing agent behavior.

### Row Level Security (RLS)

#### Enable RLS on All Tables

```sql
-- Stop production before applying RLS!
ALTER TABLE conversations ENABLE ROW LEVEL SECURITY;
ALTER TABLE client_memory ENABLE ROW LEVEL SECURITY;
ALTER TABLE meeting_notes ENABLE ROW LEVEL SECURITY;
ALTER TABLE property_interactions ENABLE ROW LEVEL SECURITY;

-- Service role bypasses RLS (full access)
CREATE POLICY "Service role full access"
  ON conversations
  FOR ALL
  TO service_role
  USING (true)
  WITH CHECK (true);

-- Anon users can only read their own conversations
CREATE POLICY "Users see own data"
  ON conversations
  FOR SELECT
  TO anon
  USING (client_email = current_setting('request.jwt.claims', true)::json->>'email');
```

**Security benefit:** Even if anon key leaks, attackers can't read other clients' data.

### API Key Governance

**Two Keys, Different Purposes:**

1. **Service Role Key** (High privilege)
   - Full database access (bypasses RLS)
   - Use only in secure server environments
   - Rotate quarterly

2. **Anon Key** (Low privilege)
   - Subject to RLS policies
   - Safe for browser/mobile apps
   - Can be public (with proper RLS)

**Storage:**

```bash
# ✅ GOOD: Environment variables
export SUPABASE_SERVICE_KEY="eyJ..."  # Never commit to git!

# ❌ BAD: Hardcoded
# SUPABASE_SERVICE_KEY = "eyJ..." in config.json
```

### Query Filtering (SQL Injection Defense)

#### BAD: Unsafe Raw SQL

```python
# ❌ SQL injection vulnerability
def search(user_input: str):
    query = f"SELECT * FROM conversations WHERE message_body LIKE '%{user_input}%'"
    return supabase.rpc("exec_sql", {"sql": query}).execute()
```

#### GOOD: Parameterized Queries (Supabase Python Client)

```python
# ✅ Safe: uses PostgREST operators (no raw SQL)
def search(search_term: str):
    # Validate input first
    if len(search_term) > 200:
        raise ValueError("Search term too long")

    # Use safe PostgREST operators
    return supabase.table("conversations") \
        .select("*") \
        .ilike("message_body", f"%{search_term}%") \
        .execute()
```

**Rule:** Avoid `execute_sql.py` script unless absolutely necessary. Prefer ORM/PostgREST methods.

---

## Layer 3: Monetization (Cost Guardrails)

**Principle:** Database operations must be bounded to prevent runaway costs and resource exhaustion.

### Supabase Pricing (as of March 2026)

- **Free:** 500MB database, 1GB bandwidth, 2GB file storage
- **Pro:** 8GB database, 50GB bandwidth ($25/month)
- **Team:** 100GB database, 250GB bandwidth ($599/month)

### Cost Tracking

#### Query Budget Enforcement

```python
# ~/.openclaw/supabase-usage.json
{
  "date": "2026-03-03",
  "queries_today": 1240,
  "writes_today": 47,
  "daily_limits": {
    "queries": 10000,
    "writes": 500
  }
}
```

```python
def check_budget():
    usage = load_usage()
    if usage["queries_today"] >= usage["daily_limits"]["queries"]:
        raise CostLimitExceeded("Daily query limit reached")
    if usage["writes_today"] >= usage["daily_limits"]["writes"]:
        raise CostLimitExceeded("Daily write limit reached")
```

**Implementation:** Add to `scripts/query.py` and `scripts/insert.py`.

#### Operator Dashboard (Mock)

```
=== Supabase Usage (Today) ===
Queries: 1,240 / 10,000 (12% of daily limit)
Writes: 47 / 500 (9%)
Database size: 142MB / 500MB (28% of free tier)

Top tables (by query volume):
1. conversations (834 queries)
2. client_memory (312 queries)
3. meeting_notes (94 queries)

⚠️  Database size growing 5MB/day → will exceed free tier in 72 days
💡 Consider archiving old conversations (>90 days)
```

### Storage Limits

```sql
-- Monitor database size
SELECT
  pg_size_pretty(pg_database_size(current_database())) as database_size,
  pg_size_pretty(pg_total_relation_size('conversations')) as conversations_size;

-- Auto-archive old data (prevent storage overflow)
DELETE FROM conversations
WHERE created_at < NOW() - INTERVAL '90 days'
RETURNING client_email, subject, created_at;
```

### Connection Pooling

```python
# Use connection pooling for high-traffic apps
from supabase import create_client, ClientOptions

supabase = create_client(
    url,
    key,
    options=ClientOptions(
        max_retries=3,
        timeout=10,
    )
)
```

---

## Layer 4: Messaging (Explicit Failure Modes)

**Principle:** When database operations fail, operators know exactly what broke and how to fix it.

### Error Taxonomy

| Error Type             | Operator Message                                                           | Action Required      |
| ---------------------- | -------------------------------------------------------------------------- | -------------------- |
| **Invalid API Key**    | `❌ SUPABASE_SERVICE_KEY invalid. Check Settings → API in dashboard`       | Regenerate key       |
| **Project Paused**     | `⏸️  Project paused (free tier >7 days idle). Resume at [dashboard URL]`   | Resume project       |
| **Table Missing**      | `❌ Table 'conversations' does not exist. Run schema setup SQL`            | Create schema        |
| **RLS Violation**      | `❌ Row Level Security policy blocked query. Use service_role key`         | Check RLS policies   |
| **Connection Timeout** | `❌ Database timeout (10s). Check network or increase timeout`             | Retry or investigate |
| **Disk Full**          | `💾 Database storage limit (500MB free tier). Archive old data or upgrade` | Cleanup or upgrade   |

### Structured Error Responses

#### BAD: Generic Database Errors

```python
# ❌ No context
raise Exception("Query failed")
```

#### GOOD: Actionable Error Messages

```python
# ✅ Specific error + remediation
class SupabaseError(Exception):
    def __init__(self, operation: str, error: dict):
        self.operation = operation
        self.code = error.get("code")
        self.message = error.get("message")
        self.remediation = self._get_remediation()
        super().__init__(f"{operation} failed: {self.message}\n💡 {self.remediation}")

    def _get_remediation(self):
        if self.code == "PGRST301":  # Table not found
            return "Run database schema setup (see /skills/supabase/SKILL.md)"
        elif self.code == "PGRST302":  # RLS violation
            return "Check Row Level Security policies or use service_role key"
        elif "timeout" in self.message.lower():
            return "Increase timeout or check database performance (Dashboard → Database → Metrics)"
        else:
            return "Check Supabase logs at [dashboard URL]/logs"
```

### Incident Response

#### Severity Levels

| Level     | Example                       | Response Time | Action                                 |
| --------- | ----------------------------- | ------------- | -------------------------------------- |
| **SEV-1** | Service key compromised       | <1 hour       | Revoke key, audit access logs, rotate  |
| **SEV-2** | Accidental mass deletion      | <2 hours      | Restore from backup (if available)     |
| **SEV-3** | Query performance degradation | <8 hours      | Add indexes, optimize queries          |
| **SEV-4** | Minor data inconsistency      | <48 hours     | Manual correction + prevent recurrence |

#### SEV-1 Playbook: Service Key Compromise

1. **Immediate (0-15 min):**
   - Revoke service role key in Supabase dashboard (Settings → API → Revoke)
   - Unset `SUPABASE_SERVICE_KEY` environment variable
   - Disable skill:
     ```json
     { "agents": { "list": [{ "tools": { "deny": ["supabase_*"] } }] } }
     ```
   - **Critical:** Check if data was exfiltrated (Dashboard → Logs → API tab)

2. **Investigation (15-60 min):**
   - Review database logs for unauthorized queries
   - Check for data modifications (look for suspicious INSERT/UPDATE/DELETE)
   - Identify compromise vector (phishing, leaked .env, git commit?)
   - **Export audit logs:** Dashboard → Logs → Download

3. **Recovery (60-180 min):**
   - Generate new service role key
   - Update production environment (`export SUPABASE_SERVICE_KEY="..."`)
   - Enable Row Level Security if not already enabled (defense in depth)
   - Restore from backup if data was corrupted
   - Re-enable skill with hardened access controls (Tier 1: approval required)

4. **Post-Mortem (within 7 days):**
   - Root cause analysis
   - Update key rotation procedures
   - Implement stricter governance (e.g., Tier 1 → Tier 0 for sensitive tables)
   - Train team on secret management

#### SEV-2 Playbook: Accidental Mass Deletion

1. **Immediate (0-30 min):**
   - **Stop all agents immediately:** Disable skill to prevent further deletions
   - Check Supabase dashboard for active transactions (Dashboard → Database → Activity)
   - Estimate data loss scope:
     ```sql
     SELECT COUNT(*) FROM conversations;  -- Compare to yesterday's count
     ```

2. **Recovery (30-120 min):**
   - **Point-in-Time Recovery (Pro tier only):**
     - Dashboard → Database → Backups → Restore to [timestamp before deletion]
   - **Free tier (no automatic backups):**
     - Restore from manual backup (if you have one)
     - Otherwise, data is lost → inform affected clients
   - **Prevent recurrence:** Add DELETE confirmation in scripts

3. **Prevention (going forward):**
   - Enable soft deletes (add `deleted_at` column instead of hard deletes)
   - Implement "are you sure?" prompts for DELETE operations
   - Regular backups (Pro tier or manual exports)

---

## Deployment Profiles

### Profile 1: Production (Highest Security)

**Use case:** Live property agent with real client data

**Configuration:**

```bash
# Strict governance
export SUPABASE_URL="https://your-project.supabase.co"
export SUPABASE_SERVICE_KEY="..."  # Rotated quarterly
export SUPABASE_DAILY_QUERY_LIMIT=10000
export SUPABASE_DAILY_WRITE_LIMIT=500

# Enable auditing
export SUPABASE_AUDIT_LOG=~/.openclaw/audit/supabase.log

# Backup reminders
export SUPABASE_BACKUP_ENABLED=true
export SUPABASE_BACKUP_FREQUENCY="weekly"
```

**OpenClaw Config:** Tier 1 (approval required for writes)

```json
{
  "agents": {
    "list": [
      {
        "id": "main",
        "tools": {
          "allow": ["supabase_query", "supabase_insert", "supabase_upsert"],
          "exec": {
            "approval": "required",
            "approvalMsg": "Agent wants to write to database: {operation} on table {table}"
          }
        }
      }
    ]
  }
}
```

**RLS:** Enabled on all tables

### Profile 2: Development (Medium Security)

**Use case:** Testing workflow with sample/synthetic data

**Configuration:**

```bash
# Separate dev project
export SUPABASE_URL="https://your-dev-project.supabase.co"
export SUPABASE_SERVICE_KEY="..."  # Different key from production
export SUPABASE_DAILY_QUERY_LIMIT=50000  # Higher for testing

# Skip approval for faster iteration
# (No exec approval)
```

**OpenClaw Config:** Tier 2 (auto-write with audit logging)

**RLS:** Optional (can disable for testing)

### Profile 3: Air-Gapped (No Cloud)

**Use case:** Security-sensitive environments (government, healthcare)

**Solution:** Self-hosted PostgreSQL + OpenClaw local tools

```bash
# Local PostgreSQL instead of Supabase
export DATABASE_URL="postgresql://localhost:5432/openclaw"
```

---

## Compliance & Privacy

### GDPR/PDPA Considerations

- **Right to access:** Provide client data export:
  ```sql
  SELECT * FROM conversations WHERE client_email = 'prospect@example.com';
  ```
- **Right to erasure:** Delete all client data:
  ```sql
  DELETE FROM conversations WHERE client_email = 'prospect@example.com';
  DELETE FROM client_memory WHERE client_email = 'prospect@example.com';
  DELETE FROM meeting_notes WHERE client_email = 'prospect@example.com';
  DELETE FROM property_interactions WHERE client_email = 'prospect@example.com';
  ```
- **Data retention:** Auto-delete after 90 days (configurable):
  ```sql
  DELETE FROM conversations WHERE created_at < NOW() - INTERVAL '90 days';
  ```
- **Breach notification:** 72-hour reporting requirement → have incident response plan

### Data Encryption

- **At rest:** AES-256 (Supabase default)
- **In transit:** TLS 1.3
- **Backups:** Encrypted (Pro tier only)

### Audit Logging

```python
# Log every database operation
import logging

logging.basicConfig(
    filename="~/.openclaw/audit/supabase.log",
    level=logging.INFO,
    format="%(asctime)s | %(user)s | %(operation)s | %(table)s | %(affected_rows)d"
)

logging.info(f"Supabase query: {operation} on {table} → {row_count} rows")
```

---

## Implementation Checklist

### Immediate (Before Deployment)

- [ ] Store `SUPABASE_SERVICE_KEY` in environment (never in code)
- [ ] Run database schema setup SQL
- [ ] Enable Row Level Security on all tables
- [ ] Set up daily query/write limits
- [ ] Enable audit logging
- [ ] Create manual backup (export to CSV)

### Short-Term (Within 30 Days)

- [ ] Implement soft deletes (`deleted_at` column)
- [ ] Add confirmation prompts for DELETE operations
- [ ] Set up weekly backup reminders (Pro tier or manual)
- [ ] Document incident response playbook
- [ ] Train team on GDPR data export/erasure procedures

### Long-Term (Quarterly)

- [ ] Rotate service role key
- [ ] Review audit logs for anomalies
- [ ] Analyze database size (archive old data if needed)
- [ ] Update threat model
- [ ] Conduct tabletop exercise for SEV-1/SEV-2 incidents

---

## Operational Patterns

### Daily

```bash
# Check usage
python3 scripts/check_usage.py

# Review audit log
tail -n 100 ~/.openclaw/audit/supabase.log | grep "DELETE\|UPDATE"
```

### Weekly

```bash
# Database health check
python3 scripts/db_health_check.py

# Create backup (manual, if free tier)
python3 scripts/export_backup.py --output backup-$(date +%Y%m%d).csv
```

### Monthly

```bash
# Review storage usage
python3 scripts/analyze_storage.py

# Archive old conversations (>90 days)
python3 scripts/archive_old_data.py --older-than 90d

# Rotate service key (if policy requires)
python3 scripts/rotate_service_key.py
```

--

## References

- [Supabase Security](https://supabase.com/docs/guides/platform/security)
- [PostgreSQL Row Level Security](https://www.postgresql.org/docs/current/ddl-rowsecurity.html)
- [OWASP Database Security](https://cheatsheetseries.owasp.org/cheatsheets/Database_Security_Cheat_Sheet.html)
- [GDPR Right to Erasure](https://gdpr-info.eu/art-17-gdpr/)

---

**Document Status:** Active  
**Next Review:** 2026-06-03 (Quarterly)  
**Owner:** OpenClaw Security Team
