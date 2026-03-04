#!/usr/bin/env python3
"""
Email Classification Script
Uses LLM to detect property-related questions in emails
"""

import argparse
import json
import os
import sys

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


PROPERTY_CLASSIFICATION_PROMPT = """You are an email classifier for a Singapore property agent.

Analyze this email and determine if it contains property-related questions that require an agent's response.

Property-related topics include:
- Buying/selling timing and market conditions
- Property prices, valuation, trends
- Districts, neighborhoods, locations
- Government policies (cooling measures, ABSD, stamp duty)
- HDB regulations, BTO, resale flats
- Condo features, amenities, facilities
- Investment advice,rental yield, capital appreciation
- Financing, mortgages, loans
- Viewing requests, property inquiries

EXCLUDE:
- Spam, promotions, newsletters
- Invoices, receipts, admin emails
- Out-of-office replies
- Non-property business discussions

Email:
From: {from_email}
Subject: {subject}
Body: {body}

Respond in JSON format:
{{
  "is_property_question": true/false,
  "confidence": 0.0-1.0,
  "detected_topics": ["topic1", "topic2"],
  "reasoning": "brief explanation"
}}
"""


def classify_with_openai(subject: str, body: str, from_email: str = "") -> dict:
    """Classify using OpenAI GPT."""
    client = openai.OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
    
    prompt = PROPERTY_CLASSIFICATION_PROMPT.format(
        from_email=from_email,
        subject=subject,
        body=body,
    )
    
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a helpful email classifier. Respond only with JSON."},
            {"role": "user", "content": prompt},
        ],
        response_format={"type": "json_object"},
        temperature=0.3,
    )
    
    return json.loads(response.choices[0].message.content)


def classify_with_anthropic(subject: str, body: str, from_email: str = "") -> dict:
    """Classify using Anthropic Claude."""
    client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
    
    prompt = PROPERTY_CLASSIFICATION_PROMPT.format(
        from_email=from_email,
        subject=subject,
        body=body,
    )
    
    response = client.messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=500,
        temperature=0.3,
        messages=[
            {"role": "user", "content": prompt},
        ],
    )
    
    return json.loads(response.content[0].text)


def classify_email(
    subject: str,
    body: str,
    from_email: str = "",
    provider: str = "auto",
    debug: bool = False,
) -> dict:
    """
    Classify if email contains property questions.
    
    Args:
        subject: Email subject
        body: Email body
        from_email: Sender email (optional)
        provider: LLM provider ('openai', 'anthropic', or 'auto')
        debug: Enable debug output
        
    Returns:
        Classification result dict
    """
    if debug:
        print(f"Classifying email...", file=sys.stderr)
        print(f"Provider: {provider}", file=sys.stderr)
    
    # Auto-detect provider
    if provider == "auto":
        if HAS_OPENAI and os.environ.get("OPENAI_API_KEY"):
            provider = "openai"
        elif HAS_ANTHROPIC and os.environ.get("ANTHROPIC_API_KEY"):
            provider = "anthropic"
        else:
            print("Error: No LLM API key found. Set OPENAI_API_KEY or ANTHROPIC_API_KEY", file=sys.stderr)
            sys.exit(1)
    
    try:
        if provider == "openai":
            result = classify_with_openai(subject, body, from_email)
        elif provider == "anthropic":
            result = classify_with_anthropic(subject, body, from_email)
        else:
            print(f"Error: Unknown provider '{provider}'", file=sys.stderr)
            sys.exit(1)
        
        if debug:
            print(f"Classification: {json.dumps(result, indent=2)}", file=sys.stderr)
        
        return result
    
    except Exception as e:
        print(f"Error: Classification failed: {e}", file=sys.stderr)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Classify email as property question using LLM"
    )
    parser.add_argument("--subject", required=True, help="Email subject")
    parser.add_argument("--body", required=True, help="Email body")
    parser.add_argument("--from-email", default="", help="Sender email")
    parser.add_argument(
        "--provider",
        choices=["auto", "openai", "anthropic"],
        default="auto",
        help="LLM provider",
    )
    parser.add_argument("--debug", action="store_true", help="Enable debug output")
    
    args = parser.parse_args()
    
    result = classify_email(
        subject=args.subject,
        body=args.body,
        from_email=args.from_email,
        provider=args.provider,
        debug=args.debug,
    )
    
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
