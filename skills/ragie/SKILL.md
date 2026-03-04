---
name: ragie
description: "RAG (Retrieval-Augmented Generation) integration with Ragie.ai for searching property documents, files, and knowledge base stored in Google Drive"
tags: ["rag", "search", "knowledge-base", "property"]
version: 1.0.0
author: "openclaw"
requires:
  - python3
  - requests
environment:
  - RAGIE_API_KEY
---

# Ragie.ai RAG Integration Skill

This skill provides retrieval-augmented generation (RAG) capabilities through [Ragie.ai](https://ragie.ai), enabling semantic search across property documents, agent knowledge bases, and files stored in Google Drive or other connected data sources.

## Overview

Ragie.ai is a managed RAG platform that:

- Indexes documents from multiple sources (Google Drive, Dropbox, URLs, etc.)
- Provides semantic search with embedding-based retrieval
- Returns relevant context chunks with source attribution
- Supports filtering by metadata and file types

**Use this skill when you need to:**

- Search property listings, market reports, or investment documents
- Find relevant context from agent's knowledge base before answering client questions
- Retrieve specific data points from large document collections
- Combine structured data with unstructured knowledge

---

## Prerequisites

### 1. Ragie.ai Account Setup

1. Sign up at [https://ragie.ai](https://ragie.ai)
2. Connect your Google Drive or upload documents
3. Wait for indexing to complete (check dashboard)
4. Generate an API key from Settings → API Keys

### 2. Environment Configuration

Store your API key securely:

```bash
# Add to your environment (e.g., ~/.zshrc or ~/.bashrc)
export RAGIE_API_KEY="ragie_sk_..."

# Or use OpenClaw config
openclaw config set env.RAGIE_API_KEY "ragie_sk_..."
```

**Security:** Never commit API keys to git. Use environment variables or secure secret management.

### 3. Install Dependencies

```bash
pip3 install requests
```

---

## Usage Examples

### Search Property Knowledge Base

```bash
# Basic search
python3 scripts/search.py \
  --query "What are the govt cooling measures affecting 4-room HDB resale flats?" \
  --max-results 5

# Search with file type filter
python3 scripts/search.py \
  --query "Singapore property investment hotspots 2026" \
  --file-types "pdf,docx" \
  --max-results 3
```

### Rerank Results (Higher Quality)

```bash
# Use reranking for better relevance (slower, more accurate)
python3 scripts/search.py \
  --query "best time to buy property in Singapore" \
  --max-results 10 \
  --rerank \
  --rerank-top-k 3
```

### Search with Metadata Filtering

```bash
# Filter by custom metadata (if configured in Ragie dashboard)
python3 scripts/search.py \
  --query "condo prices" \
  --filter '{"property_type": "condo", "district": "District 9"}' \
  --max-results 5
```

### List Indexed Documents

```bash
# See what documents are available
python3 scripts/list_documents.py --limit 20
```

---

## Script Reference

### `search.py` - Semantic Search

Performs RAG retrieval across indexed documents.

**Parameters:**

- `--query` (required): Search query text
- `--max-results` (default: 5): Number of results to return
- `--file-types`: Comma-separated file extensions (e.g., "pdf,docx,txt")
- `--filter`: JSON metadata filter (must match Ragie schema)
- `--rerank`: Enable reranking for better relevance (slower)
- `--rerank-top-k` (default: 3): Number of top results after reranking
- `--mode` (default: "search"): Output mode
  - `search`: Return chunks with sources
  - `snippets`: Return just text snippets
  - `sources`: Return document metadata only

**Output (JSON):**

```json
{
  "query": "govt cooling measures HDB",
  "results": [
    {
      "chunk_id": "chunk_abc123",
      "text": "The Additional Buyer's Stamp Duty (ABSD) for HDB resale flats...",
      "score": 0.87,
      "document": {
        "id": "doc_xyz789",
        "name": "HDB_Cooling_Measures_2025.pdf",
        "source": "google_drive",
        "url": "https://drive.google.com/file/d/..."
      }
    }
  ],
  "total": 1
}
```

### `list_documents.py` - List Indexed Documents

Shows what documents are in your Ragie index.

**Parameters:**

- `--limit` (default: 50): Maximum number of documents to return
- `--offset` (default: 0): Pagination offset
- `--source-filter`: Filter by source type (e.g., "google_drive", "upload")

**Output (JSON):**

```json
{
  "documents": [
    {
      "id": "doc_xyz789",
      "name": "Property_Market_Report_Q1_2026.pdf",
      "source": "google_drive",
      "indexed_at": "2026-03-01T10:30:00Z",
      "chunk_count": 45
    }
  ],
  "total": 123
}
```

---

## Integration with Property Email Agent

This skill is designed to work with the Property Email Agent workflow:

```bash
# 1. Property Email Agent receives email: "Is it a good time to buy in District 9?"

# 2. Ragie search for relevant context
python3 scripts/search.py \
  --query "Is it a good time to buy property in District 9 Singapore?" \
  --max-results 5 \
  --rerank \
  --rerank-top-k 3

# 3. Use results to draft informed email reply
# (See property-email-agent skill)
```

---

## Common Patterns

### Multi-Query Search

When client questions are complex, break them into multiple searches:

```bash
# Question: "Which district is best for investment and what are the cooling measures?"

# Search 1: Investment hotspots
python3 scripts/search.py \
  --query "best Singapore districts for property investment 2026" \
  --max-results 3

# Search 2: Cooling measures
python3 scripts/search.py \
  --query "Singapore property cooling measures ABSD taxes" \
  --max-results 3
```

### Verify Source Attribution

Always include source links in email replies:

```bash
# Extract sources from search results
python3 scripts/search.py \
  --query "property market trends" \
  --mode sources \
  --max-results 5
```

---

## Error Handling

### Common Issues

**"API key not found"**

- Ensure `RAGIE_API_KEY` is set in environment
- Verify key format: `ragie_sk_...`

**"No documents indexed"**

- Check Ragie dashboard for indexing status
- Google Drive sync may take 10-30 minutes for initial indexing

**"Rate limit exceeded"**

- Ragie free tier: 1000 requests/month
- Implement caching or upgrade plan

**"Empty results"**

- Try broader query terms
- Check document indexing in Ragie dashboard
- Verify file types are supported (PDF, DOCX, TXT, MD)

---

## Rate Limits & Cost

Ragie.ai pricing (as of March 2026):

- **Free**: 1000 queries/month, 100MB storage
- **Pro**: 10,000 queries/month, 1GB storage ($29/month)
- **Enterprise**: Custom limits

**Best practices:**

- Cache frequent queries (see `cache.py` helper)
- Use `max-results` to limit API costs
- Enable reranking only for important queries (costs 2x credits)

---

## Security & Privacy

### Data Handling

- Ragie stores and indexes your documents on their servers
- Data is encrypted at rest and in transit
- Google Drive access uses OAuth (revocable permissions)

### API Key Security

```bash
# ✅ GOOD: Environment variable
export RAGIE_API_KEY="ragie_sk_..."

# ❌ BAD: Hardcoded in scripts
# Never do this!
```

### GDPR & Compliance

- Client data in property documents may be subject to GDPR
- Use Ragie's data retention policies (Settings → Retention)
- Document deletion removes data within 24 hours

**See SECURITY.md for comprehensive threat model and mitigation strategies.**

---

## Troubleshooting

### Debug Mode

```bash
# Enable verbose logging
python3 scripts/search.py \
  --query "test" \
  --debug
```

### Check API Connection

```bash
# Verify credentials
python3 scripts/test_connection.py
```

### Clear Local Cache

```bash
# If using cache helper
rm -f ~/.openclaw/ragie-cache.json
```

---

## Related Skills

- **google-workspace**: Sync documents from Google Drive to Ragie
- **supabase**: Store conversation history for follow-up context
- **property-email-agent**: Orchestrator that uses this skill

---

## References

- [Ragie.ai Documentation](https://docs.ragie.ai)
- [Ragie API Reference](https://docs.ragie.ai/api-reference)
- [RAG Best Practices](https://docs.ragie.ai/guides/rag-best-practices)

---

## Changelog

### v1.0.0 (2026-03-03)

- Initial release
- Basic search and document listing
- Reranking support
- Metadata filtering
