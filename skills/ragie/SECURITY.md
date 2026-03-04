# Ragie.ai Skill - Security Documentation

**Version:** 1.0.0  
**Last Updated:** 2026-03-03  
**Risk Level:** Medium (external API with document access)

---

## Executive Summary

The Ragie.ai skill provides RAG (Retrieval-Augmented Generation) search across property documents stored in Google Drive. As an external service, it represents moderate security risk: property documents may contain confidential client data, pricing information, and business intelligence.

**Key risks:**

- External data storage (documents live on Ragie servers)
- API key compromise → unauthorized access to knowledge base
- Prompt injection → malicious queries extracting sensitive data
- Cost escalation from API abuse

This document applies the **4-layer security framework** (Architecture, Governance, Monetization, Messaging) to mitigate these risks.

---

## Threat Model

### Attack Vectors

| Vector                 | Impact                                | Likelihood | Mitigation Priority |
| ---------------------- | ------------------------------------- | ---------- | ------------------- |
| **API key theft**      | Complete knowledge base access        | Medium     | High                |
| **Prompt injection**   | Sensitive data extraction             | Medium     | High                |
| **Query manipulation** | Filter bypass, unauthorized documents | Low        | Medium              |
| **Rate limit DoS**     | Service disruption, cost spike        | Low        | Medium              |
| **Document poisoning** | Malicious content in knowledge base   | Low        | Low                 |
| **SSRF via URLs**      | Internal network probing              | Very Low   | Low                 |

---

## Layer 1: Architecture (Verifiable Completion)

**Principle:** RAG searches must return verifiable, attributed results. No "trust the API" assumptions.

### Verifiable Completion States

#### BAD: Unverified RAG Results

```python
# ❌ No source attribution
def search_ragie(query):
    results = ragie_api.search(query)
    return results["text"]  # Who said this? When? Source?
```

#### GOOD: Source-Attributed Results

```python
# ✅ Every chunk includes source document + URL
def search_ragie(query):
    results = ragie_api.search(query)
    return [{
        "text": chunk["text"],
        "source": {
            "document_id": chunk["document"]["id"],
            "document_name": chunk["document"]["name"],
            "url": chunk["document"]["url"],  # Verifiable link
            "indexed_at": chunk["document"]["created_at"],
        },
        "score": chunk["score"],
    } for chunk in results["scored_chunks"]]
```

**Enforcement:** `search.py` script **always** returns document metadata. Email drafts **must** cite sources.

### State Machine: RAG Search Lifecycle

```
[Query Submitted]
    ↓
[API Request] → (Rate limit check)
    ↓
[Results Returned] → (Source validation)
    ↓
[Attribution Added] → (Verifiable completion)
    ↓
[Delivered to Operator]
```

### Artifact Validation

```python
# Validate every RAG result before use
def validate_rag_chunk(chunk: dict) -> bool:
    required_fields = ["text", "document"]
    if not all(field in chunk for field in required_fields):
        raise ValueError("Invalid RAG chunk: missing required fields")

    if not chunk["document"].get("name"):
        raise ValueError("Invalid RAG chunk: no source document")

    return True
```

**Implementation:** See `scripts/search.py` lines 140-170 (format_search_results function).

---

## Layer 2: Governance (Default-Deny)

**Principle:** RAG access is opted-in, not assumed. Operators must explicitly enable and configure.

### Skill Registration (Default-Deny)

The skill is **not** available until explicitly enabled:

```json
{
  "agents": {
    "list": [
      {
        "id": "main",
        "tools": {
          "deny": ["*"], // Default: all tools denied
          "allow": ["ragie_search"] // Explicit allowlist
        }
      }
    ]
  }
}
```

### API Key Governance

**Storage:** Environment variable only (never in code/config files)

```bash
# ✅ GOOD: Environment variable
export RAGIE_API_KEY="ragie_sk_..."

# ❌ BAD: Hardcoded or in config
# RAGIE_API_KEY = "ragie_sk_..." in config.json
```

**Rotation Policy:**

- Rotate API keys quarterly (recommended)
- Immediate rotation if key suspected compromised
- Monitor API usage for anomalies (Ragie dashboard)

### Query Filtering (Prompt Injection Mitigation)

#### BAD: Unfiltered User Queries

```python
# ❌ Direct user input → RAG API
def search(user_query: str):
    return ragie_api.search(user_query)
```

#### GOOD: Sanitized Queries with Length Limits

```python
# ✅ Sanitize and limit query length
def search(user_query: str):
    # Strip control characters and excessive whitespace
    sanitized = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', user_query)
    sanitized = ' '.join(sanitized.split())

    # Enforce length limit (prevent prompt injection)
    if len(sanitized) > 500:
        raise ValueError("Query too long (max 500 chars)")

    # Log for audit
    log_query(sanitized)

    return ragie_api.search(sanitized)
```

**Implementation:** Add to `scripts/search.py` before API call.

### File Type Restrictions

Only allow safe document types in Ragie:

```python
ALLOWED_FILE_TYPES = ["pdf", "docx", "txt", "md", "xlsx"]
DISALLOWED_FILE_TYPES = ["exe", "sh", "bat", "ps1", "dll"]

# In search request
if file_types:
    if any(ft not in ALLOWED_FILE_TYPES for ft in file_types):
        raise ValueError(f"Disallowed file type. Allowed: {ALLOWED_FILE_TYPES}")
```

---

## Layer 3: Monetization (Cost Guardrails)

**Principle:** RAG API costs must be bounded and monitored. No runaway spending.

### Ragie.ai Pricing (as of March 2026)

- **Free:** 1,000 queries/month, 100MB storage
- **Pro:** 10,000 queries/month, 1GB storage ($29/month)
- **Reranking:** 2x credit cost per query

### Cost Tracking

#### Daily Budget Enforcement

```python
# ~/.openclaw/ragie-usage.json
{
  "date": "2026-03-03",
  "queries_today": 47,
  "daily_limit": 200,  # ~6,000/month
  "rerank_queries_today": 12,
  "monthly_budget": "$40"
}
```

```python
def check_budget():
    usage = load_usage()
    if usage["queries_today"] >= usage["daily_limit"]:
        raise CostLimitExceeded("Daily query limit reached")
```

**Implementation:** Add to `scripts/search.py` at entry point.

#### Operator Dashboard (Mock)

```
=== Ragie Usage (Today) ===
Queries: 47/200 (23% of daily limit)
Rerank queries: 12 (extra cost)
Estimated monthly cost: $32.45 / $40 budget

Top queries (by volume):
1. "District 9 property investment" (12x)
2. "ABSD cooling measures" (8x)
3. "HDB resale regulations" (6x)

💡 Consider caching top queries to reduce costs
```

### Rate Limiting

```python
# Rate limit: max 5 queries per minute per user
from ratelimit import limits, sleep_and_retry

@sleep_and_retry
@limits(calls=5, period=60)
def search_ragie(query: str):
    # API call
    pass
```

### Caching Strategy

```python
# Cache frequent queries for 24 hours
import hashlib
import json
from datetime import datetime, timedelta

CACHE_FILE = "~/.openclaw/ragie-cache.json"
CACHE_TTL = timedelta(hours=24)

def cached_search(query: str):
    cache_key = hashlib.sha256(query.encode()).hexdigest()

    # Check cache
    cache = load_cache()
    if cache_key in cache:
        entry = cache[cache_key]
        if datetime.now() - entry["cached_at"] < CACHE_TTL:
            return entry["results"]  # Cache hit

    # Cache miss → API call
    results = ragie_api.search(query)

    # Store in cache
    cache[cache_key] = {
        "query": query,
        "results": results,
        "cached_at": datetime.now(),
    }
    save_cache(cache)

    return results
```

**Implementation:** Add caching layer in `scripts/search.py`.

---

## Layer 4: Messaging (Explicit Failure Modes)

**Principle:** When things break, operators know exactly what happened and what to do.

### Error Taxonomy

| Error Type          | Operator Message                                                               | Action Required |
| ------------------- | ------------------------------------------------------------------------------ | --------------- |
| **API Key Invalid** | `❌ RAGIE_API_KEY invalid or expired. Regenerate at https://ragie.ai/settings` | Rotate key      |
| **Rate Limit Hit**  | `⏱️ Ragie rate limit (1000/month). Upgrade plan or wait until [date]`          | Upgrade or wait |
| **No Documents**    | `⚠️  No indexed documents. Connect Google Drive at https://ragie.ai/dashboard` | Index documents |
| **Query Timeout**   | `❌ Ragie API timeout (30s). Check network or retry`                           | Retry           |
| **Empty Results**   | `🔍 No results for query. Try broader terms or check indexing`                 | Refine query    |

### Structured Error Responses

#### BAD: Generic Errors

```python
# ❌ No context, no actionability
raise Exception("API error")
```

#### GOOD: Actionable Error Messages

```python
# ✅ Specific error + remediation steps
class RagieAPIError(Exception):
    def __init__(self, error_code: int, message: str):
        self.error_code = error_code
        self.message = message
        self.remediation = self._get_remediation()
        super().__init__(f"{message}\n💡 {self.remediation}")

    def _get_remediation(self):
        if self.error_code == 401:
            return "Check RAGIE_API_KEY in environment (~/.zshrc)"
        elif self.error_code == 429:
            return "Upgrade plan at https://ragie.ai/pricing or reduce query frequency"
        elif self.error_code == 404:
            return "Verify document indexing in Ragie dashboard"
        else:
            return "Contact support@ragie.ai with error code"
```

### Incident Response

#### Severity Levels

| Level     | Example                | Response Time | Action                             |
| --------- | ---------------------- | ------------- | ---------------------------------- |
| **SEV-1** | API key compromised    | <1 hour       | Revoke key, rotate, audit logs     |
| **SEV-2** | Cost spike ($100+/day) | <4 hours      | Disable skill, investigate queries |
| **SEV-3** | Service degradation    | <24 hours     | Monitor, contact Ragie support     |
| **SEV-4** | Empty results          | <72 hours     | Check indexing, refine queries     |

#### SEV-1 Playbook: API Key Compromise

1. **Immediate (0-15 min):**
   - Revoke API key in Ragie dashboard (Settings → API Keys → Revoke)
   - Unset `RAGIE_API_KEY` environment variable
   - Disable skill in OpenClaw config:
     ```json
     { "agents": { "list": [{ "tools": { "deny": ["ragie_search"] } }] } }
     ```

2. **Investigation (15-60 min):**
   - Check Ragie API logs for unauthorized queries
   - Review OpenClaw audit logs for suspicious activity
   - Identify compromise vector (phishing? leaked .env file?)

3. **Recovery (60-120 min):**
   - Generate new API key
   - Update production environment (`export RAGIE_API_KEY="..."`)
   - Re-enable skill with strengthened access controls
   - Document incident in runbook

4. **Post-Mortem (within 7 days):**
   - Root cause analysis
   - Update security procedures
   - Train team on key management best practices

---

## Deployment Profiles

### Profile 1: High-Risk Production (Recommended)

**Use case:** Live property agent workflow with real client data

**Configuration:**

```bash
# Strict governance
export RAGIE_API_KEY="..."  # Rotated quarterly
export RAGIE_DAILY_QUERY_LIMIT=100
export RAGIE_MONTHLY_BUDGET=50  # USD

# Enable caching
export RAGIE_CACHE_ENABLED=true
export RAGIE_CACHE_TTL=86400  # 24 hours

# Rate limiting
export RAGIE_RATE_LIMIT=5  # queries/minute

# Audit logging
export RAGIE_AUDIT_LOG=~/.openclaw/audit/ragie.log
```

**OpenClaw Config:**

```json
{
  "agents": {
    "list": [
      {
        "id": "main",
        "tools": {
          "allow": ["ragie_search"],
          "exec": {
            "approval": "required" // Operator reviews RAG queries
          }
        }
      }
    ]
  }
}
```

### Profile 2: Development/Testing (Lower Risk)

**Use case:** Testing workflow with sample data

**Configuration:**

```bash
# Relaxed limits for testing
export RAGIE_API_KEY="..."
export RAGIE_DAILY_QUERY_LIMIT=500
export RAGIE_CACHE_ENABLED=false  # See live results

# Skip approval
# (No exec approval required)
```

### Profile 3: Offline/Air-Gapped (No Ragie)

**Use case:** Security-sensitive environments

**Solution:** Self-hosted RAG alternative (e.g., LlamaIndex + local vector DB)

---

## Compliance & Privacy

### GDPR/PDPA Considerations

- **Data residency:** Ragie stores documents on AWS (check region in dashboard)
- **Right to erasure:** Delete documents in Ragie dashboard → removal within 24 hours
- **Data processing agreement:** Review Ragie Terms of Service for DPA
- **Consent:** Inform clients their property inquiries may be matched against knowledge base

### Retention Policy

```bash
# Auto-delete old documents (hypothetical - implement in Ragie if supported)
# Delete property reports older than 2 years
python3 scripts/cleanup_old_documents.py --older-than "730d"
```

### Audit Logging

```python
# Log every RAG query for compliance
import logging

logging.basicConfig(
    filename="~/.openclaw/audit/ragie.log",
    level=logging.INFO,
    format="%(asctime)s | %(user)s | %(query)s | %(results_count)d"
)

logging.info(f"Ragie query: {query} → {len(results)} results")
```

---

## Implementation Checklist

### Immediate (Before Deployment)

- [ ] Store `RAGIE_API_KEY` in environment (never in code)
- [ ] Set `chmod 600 ~/.openclaw/credentials/ragie*`
- [ ] Enable query sanitization (control character stripping)
- [ ] Add source attribution to all RAG results
- [ ] Configure daily query limits
- [ ] Enable audit logging

### Short-Term (Within 30 Days)

- [ ] Implement caching for frequent queries
- [ ] Set up cost monitoring dashboard
- [ ] Document API key rotation procedure
- [ ] Train team on incident response playbook
- [ ] Review Ragie Terms of Service for DPA

### Long-Term (Quarterly)

- [ ] Rotate API keys
- [ ] Review audit logs for anomalies
- [ ] Analyze top queries (optimize caching)
- [ ] Update threat model based on new attack vectors
- [ ] Conduct tabletop exercise for SEV-1 incident

---

## Operational Patterns

### Daily

```bash
# Check usage
python3 scripts/check_usage.py

# Review audit log
tail -n 50 ~/.openclaw/audit/ragie.log
```

### Weekly

```bash
# Analyze top queries
python3 scripts/analyze_queries.py --last-7-days

# Check for stale cache entries
python3 scripts/cache_stats.py
```

### Monthly

```bash
# Review costs
# (Check Ragie dashboard for billing)

# Rotate API key (if policy requires)
python3 scripts/rotate_api_key.py
```

---

## References

- [Ragie.ai Security](https://docs.ragie.ai/security)
- [OWASP API Security](https://owasp.org/www-project-api-security/)
- [NIST Cybersecurity Framework](https://www.nist.gov/cyberframework)

---

**Document Status:** Active  
**Next Review:** 2026-06-03 (Quarterly)  
**Owner:** OpenClaw Security Team
