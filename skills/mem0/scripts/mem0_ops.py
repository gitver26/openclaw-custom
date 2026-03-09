#!/usr/bin/env python3
"""
mem0_ops.py — CLI bridge between openclaw agents and mem0 memory.

Provides add / search / list / delete operations so the openclaw agent
can persist and retrieve memories across sessions.

Usage (called as a subprocess tool by the agent):

  # Store a fact about user100
  python mem0_ops.py add --user user100 --message "Prefers concise answers"

  # Retrieve relevant memories before replying
  python mem0_ops.py search --user user100 --query "communication preferences"

  # List all stored memories for the user
  python mem0_ops.py list --user user100

  # Remove a specific memory
  python mem0_ops.py delete --id <memory-id>

Environment variables:
  OPENAI_API_KEY   — required (mem0 default LLM + embeddings use OpenAI)
  MEM0_API_KEY     — optional; if set, uses managed mem0 platform instead
                     of the local self-hosted store

Output: newline-delimited JSON so the agent can parse each line independently.
Errors are written to stderr; stdout always contains only valid JSON lines.
"""

import argparse
import json
import os
import sys


def _build_memory():
    """Return a configured mem0 Memory instance.

    MEM0_OPENAI_API_KEY takes precedence over OPENAI_API_KEY so that Z.AI keys
    used by the openclaw agent do not accidentally leak into mem0's OpenAI calls.
    """
    mem0_platform_key = os.getenv("MEM0_API_KEY")
    if mem0_platform_key:
        # Managed mem0 platform (https://app.mem0.ai)
        from mem0 import MemoryClient  # type: ignore
        return MemoryClient(api_key=mem0_platform_key), "platform"

    # Self-hosted: ensure mem0 uses the dedicated OpenAI key, not the Z.AI key.
    openai_key = os.getenv("MEM0_OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY")
    if not openai_key:
        raise RuntimeError(
            "Set MEM0_OPENAI_API_KEY (or OPENAI_API_KEY) to use self-hosted mem0"
        )
    # Temporarily override OPENAI_API_KEY for this process so mem0's internals pick it up.
    os.environ["OPENAI_API_KEY"] = openai_key

    from mem0 import Memory  # type: ignore
    return Memory(), "local"


def cmd_add(args):
    memory, mode = _build_memory()
    messages = [{"role": "user", "content": args.message}]
    result = memory.add(messages, user_id=args.user)
    print(json.dumps({"ok": True, "mode": mode, "result": result}))


def cmd_search(args):
    memory, mode = _build_memory()
    hits = memory.search(query=args.query, user_id=args.user, limit=args.limit)
    # Normalise: both local and platform return a list of dicts
    memories = hits if isinstance(hits, list) else hits.get("results", [])
    for m in memories:
        print(json.dumps({"id": m.get("id"), "memory": m.get("memory"), "score": m.get("score")}))


def cmd_list(args):
    memory, mode = _build_memory()
    all_mem = memory.get_all(user_id=args.user)
    items = all_mem if isinstance(all_mem, list) else all_mem.get("results", [])
    for m in items:
        print(json.dumps({"id": m.get("id"), "memory": m.get("memory")}))


def cmd_delete(args):
    memory, mode = _build_memory()
    memory.delete(memory_id=args.id)
    print(json.dumps({"ok": True, "deleted_id": args.id}))


def main():
    parser = argparse.ArgumentParser(description="mem0 memory operations for openclaw agents")
    sub = parser.add_subparsers(dest="command", required=True)

    # add
    p_add = sub.add_parser("add", help="Store a new memory")
    p_add.add_argument("--user", required=True, help="User ID (e.g. user100)")
    p_add.add_argument("--message", required=True, help="Text to remember")

    # search
    p_search = sub.add_parser("search", help="Retrieve relevant memories")
    p_search.add_argument("--user", required=True, help="User ID")
    p_search.add_argument("--query", required=True, help="Search query")
    p_search.add_argument("--limit", type=int, default=5, help="Max results (default 5)")

    # list
    p_list = sub.add_parser("list", help="List all memories for a user")
    p_list.add_argument("--user", required=True, help="User ID")

    # delete
    p_del = sub.add_parser("delete", help="Delete a memory by ID")
    p_del.add_argument("--id", required=True, help="Memory ID to delete")

    args = parser.parse_args()

    try:
        {"add": cmd_add, "search": cmd_search, "list": cmd_list, "delete": cmd_delete}[args.command](args)
    except Exception as exc:
        print(json.dumps({"ok": False, "error": str(exc)}), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
