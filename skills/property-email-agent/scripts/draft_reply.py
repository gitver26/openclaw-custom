#!/usr/bin/env python3
"""
Email Draft Generator
Orchestrates context gathering + LLM draft generation
"""

import argparse
import json
import os
import sys
from typing import Dict, List

# Add skill paths
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../ragie/scripts"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../supabase/scripts"))

try:
    from search import search_ragie
    from get_client_context import get_client_context
except ImportError:
    print("Error: ragie and supabase skills required", file=sys.stderr)
    sys.exit(1)

try:
    import openai
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False

try:
    import anthropic
    HAS_ANTHROPIC = True
except ImportError:
    HAS_ANTHROPIC = False


DRAFT_PROMPT_TEMPLATE = """You are a professional Singapore property agent drafting a reply email.

Client email: {client_email}
Original subject: {original_subject}
Original message: {original_body}

Context from Ragie (property knowledge base):
{ragie_context}

Context from Supabase (client history):
{supabase_context}

Instructions:
1. Draft a professional, helpful email reply (300-450 words)
2. Use 2-3 clear headings (##)
3. Include bullet points for key information
4. Reference specific data from the context (with sources)
5. Be conversational but data-driven
6. End with a clear call-to-action
7. Sign off professionally

Format:
Subject: Re: [original subject]

Dear [Name],

[Opening paragraph]

## [Heading 1]
[Content with bullet points]

## [Heading 2]
[Content]

## Next Steps
[Call-to-action]

Best regards,
[Agent Name]
[Title]

---
Sources: [List Ragie documents used]
"""


def generate_draft(
    client_email: str,
    original_subject: str,
    original_body: str,
    search_query: str,
    provider: str = "auto",
    debug: bool = False,
) -> Dict:
    """Generate email draft with context."""
    
    if debug:
        print("=== Context Gathering ===", file=sys.stderr)
    
    # 1. Search Ragie for property knowledge
    if debug:
        print("Searching Ragie...", file=sys.stderr)
    
    ragie_results = search_ragie(
        query=search_query,
        max_results=5,
        rerank=True,
        rerank_top_k=3,
        debug=debug,
    )
    
    ragie_context = "\n\n".join([
        f"- {chunk['text']}\n  Source: {chunk['document']['name']}"
        for chunk in ragie_results.get("scored_chunks", [])[:3]
    ])
    
    # 2. Get client context from Supabase
    if debug:
        print("Fetching client context from Supabase...", file=sys.stderr)
    
    try:
        client_context = get_client_context(
            client_email=client_email,
            conversation_limit=5,
            meeting_limit=3,
            debug=debug,
        )
        
        supabase_context = f"""
Previous conversations: {client_context['summary']['total_conversations']}
Has stored preferences: {client_context['summary']['has_memory']}
Meeting notes: {client_context['summary']['total_meetings']}
"""
        if client_context.get("client_memory"):
            memory = client_context["client_memory"]
            supabase_context += f"\nClient preferences: {json.dumps(memory.get('preferences', {}))}"
            supabase_context += f"\nPreferred districts: {memory.get('preferred_districts', [])}"
    
    except Exception as e:
        if debug:
            print(f"No client context found (new client): {e}", file=sys.stderr)
        supabase_context = "New client (no previous history)"
    
    # 3. Generate draft with LLM
    if debug:
        print("=== Generating Draft ===", file=sys.stderr)
    
    prompt = DRAFT_PROMPT_TEMPLATE.format(
        client_email=client_email,
        original_subject=original_subject,
        original_body=original_body,
        ragie_context=ragie_context or "(No relevant documents found)",
        supabase_context=supabase_context,
    )
    
    # Auto-detect provider
    if provider == "auto":
        if HAS_OPENAI and os.environ.get("OPENAI_API_KEY"):
            provider = "openai"
        elif HAS_ANTHROPIC and os.environ.get("ANTHROPIC_API_KEY"):
            provider = "anthropic"
    
    try:
        if provider == "openai":
            client = openai.OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are a professional property agent."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.7,
                max_tokens=1500,
            )
            draft_text = response.choices[0].message.content
        
        elif provider == "anthropic":
            client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
            response = client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=1500,
                temperature=0.7,
                messages=[{"role": "user", "content": prompt}],
            )
            draft_text = response.content[0].text
        
        else:
            print(f"Error: No LLM provider available", file=sys.stderr)
            sys.exit(1)
        
        # Parse subject and body
        lines = draft_text.strip().split("\n")
        subject_line = next((l for l in lines if l.startswith("Subject:")), "Re: " + original_subject)
        subject = subject_line.replace("Subject:", "").strip()
        
        # Body is everything after subject
        body_start = draft_text.find("\n\n")
        body = draft_text[body_start:].strip() if body_start > 0 else draft_text
        
        word_count = len(body.split())
        
        return {
            "draft": {
                "subject": subject,
                "body": body,
                "word_count": word_count,
            },
            "context_used": {
                "ragie_chunks": len(ragie_results.get("scored_chunks", [])),
                "supabase_conversations": client_context.get("summary", {}).get("total_conversations", 0) if 'client_context' in locals() else 0,
            },
        }
    
    except Exception as e:
        print(f"Error: Draft generation failed: {e}", file=sys.stderr)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Generate email draft with context")
    parser.add_argument("--client-email", required=True, help="Client email address")
    parser.add_argument("--original-subject", required=True, help="Original email subject")
    parser.add_argument("--original-body", required=True, help="Original email body")
    parser.add_argument("--query", required=True, help="Search query for Ragie")
    parser.add_argument("--provider", choices=["auto", "openai", "anthropic"], default="auto")
    parser.add_argument("--debug", action="store_true", help="Enable debug output")
    
    args = parser.parse_args()
    
    result = generate_draft(
        client_email=args.client_email,
        original_subject=args.original_subject,
        original_body=args.original_body,
        search_query=args.query,
        provider=args.provider,
        debug=args.debug,
    )
    
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
