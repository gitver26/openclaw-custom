# mem0 Memory Skill

Provides persistent, searchable memory for openclaw agents using [mem0](https://github.com/mem0ai/mem0).
Memories are scoped per user (e.g. `user100`) and survive container restarts via the mounted volume.

## Setup

Install the Python package (already done inside `Dockerfile.user100`):

```bash
pip install mem0ai
```

Set at least `OPENAI_API_KEY` in your environment (mem0 uses OpenAI for embeddings and its default LLM).
Optionally set `MEM0_API_KEY` to use the managed [mem0 platform](https://app.mem0.ai) instead of the local store.

## Operations

All operations are handled by `scripts/mem0_ops.py` and emit newline-delimited JSON to stdout.

### Add a memory

```bash
python skills/mem0/scripts/mem0_ops.py add \
  --user user100 \
  --message "Prefers concise, bullet-point answers"
```

### Search memories

```bash
python skills/mem0/scripts/mem0_ops.py search \
  --user user100 \
  --query "communication style" \
  --limit 5
```

### List all memories

```bash
python skills/mem0/scripts/mem0_ops.py list --user user100
```

### Delete a memory

```bash
python skills/mem0/scripts/mem0_ops.py delete --id <memory-id>
```

## Agent integration pattern

The openclaw agent calls `mem0_ops.py` as a subprocess tool:

1. **Before replying** — search for relevant memories:
   ```
   python skills/mem0/scripts/mem0_ops.py search --user user100 --query "<user message>"
   ```
2. **After a conversation turn** — store anything worth remembering:
   ```
   python skills/mem0/scripts/mem0_ops.py add --user user100 --message "<fact to remember>"
   ```

## Storage backends

| `MEM0_API_KEY` set? | Backend                   | Notes                                          |
| ------------------- | ------------------------- | ---------------------------------------------- |
| No                  | Local (qdrant in-process) | Zero config; data lives in `~/.openclaw/mem0/` |
| Yes                 | Managed mem0 platform     | Cross-device sync; requires account            |

## Scrapling integration

Use the existing [Scrapling skill](../scrapling/SKILL.md) to fetch web content, then pipe the result into mem0 to build a searchable knowledge base:

```bash
# 1. Scrape a page
python skills/scrapling/scripts/scrape.py \
  --url "https://example.com/article" \
  --mode text > /tmp/article.txt

# 2. Store the content as a memory
python skills/mem0/scripts/mem0_ops.py add \
  --user user100 \
  --message "$(cat /tmp/article.txt)"
```
