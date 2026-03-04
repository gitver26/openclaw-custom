#!/usr/bin/env python3
"""
Get Client Context Helper
Fetch all relevant data for a client (conversations, memory, notes) in one go.
This is the primary script used by the Property Email Agent workflow.
"""

import argparse
import json
import os
import sys
from typing import Optional

try:
    from supabase import create_client, Client
except ImportError:
    print("Error: supabase library not installed. Run: pip3 install supabase", file=sys.stderr)
    sys.exit(1)


def get_supabase_client() -> Client:
    """Create Supabase client from environment variables."""
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_KEY")
    
    if not url or not key:
        print("Error: SUPABASE_URL and SUPABASE_SERVICE_KEY environment variables required", file=sys.stderr)
        sys.exit(1)
    
    return create_client(url, key)


def get_client_context(
    client_email: str,
    conversation_limit: int = 10,
    meeting_limit: int = 5,
    debug: bool = False,
) -> dict:
    """
    Fetch complete context for a client.
    
    Args:
        client_email: Client email address
        conversation_limit: Max conversations to fetch
        meeting_limit: Max meeting notes to fetch
        debug: Enable debug output
        
    Returns:
        Dict with all client data
    """
    supabase = get_supabase_client()
    
    if debug:
        print(f"Fetching context for: {client_email}", file=sys.stderr)
    
    context = {
        "client_email": client_email,
        "conversations": [],
        "client_memory": None,
        "meeting_notes": [],
        "property_interactions": [],
    }
    
    try:
        # 1. Get recent conversations
        if debug:
            print("Fetching conversations...", file=sys.stderr)
        
        conversations = supabase.table("conversations") \
            .select("*") \
            .eq("client_email", client_email) \
            .order("created_at", desc=True) \
            .limit(conversation_limit) \
            .execute()
        
        context["conversations"] = conversations.data
        
        if debug:
            print(f"  Found {len(conversations.data)} conversations", file=sys.stderr)
        
        # 2. Get client memory/preferences
        if debug:
            print("Fetching client memory...", file=sys.stderr)
        
        try:
            memory = supabase.table("client_memory") \
                .select("*") \
                .eq("client_email", client_email) \
                .single() \
                .execute()
            
            context["client_memory"] = memory.data
            
            if debug:
                print(f"  Found client memory", file=sys.stderr)
        
        except Exception as e:
            if debug:
                print(f"  No client memory found (this is OK for new clients)", file=sys.stderr)
            context["client_memory"] = None
        
        # 3. Get meeting notes
        if debug:
            print("Fetching meeting notes...", file=sys.stderr)
        
        notes = supabase.table("meeting_notes") \
            .select("*") \
            .eq("client_email", client_email) \
            .order("meeting_date", desc=True) \
            .limit(meeting_limit) \
            .execute()
        
        context["meeting_notes"] = notes.data
        
        if debug:
            print(f"  Found {len(notes.data)} meeting notes", file=sys.stderr)
        
        # 4. Get property interactions
        if debug:
            print("Fetching property interactions...", file=sys.stderr)
        
        interactions = supabase.table("property_interactions") \
            .select("*") \
            .eq("client_email", client_email) \
            .order("interaction_date", desc=True) \
            .limit(10) \
            .execute()
        
        context["property_interactions"] = interactions.data
        
        if debug:
            print(f"  Found {len(interactions.data)} property interactions", file=sys.stderr)
        
        # Summary
        context["summary"] = {
            "total_conversations": len(context["conversations"]),
            "has_memory": context["client_memory"] is not None,
            "total_meetings": len(context["meeting_notes"]),
            "total_interactions": len(context["property_interactions"]),
        }
        
        return context
    
    except Exception as e:
        print(f"Error: Failed to fetch client context: {e}", file=sys.stderr)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Fetch complete context for a client from Supabase"
    )
    parser.add_argument(
        "--email",
        required=True,
        help="Client email address",
    )
    parser.add_argument(
        "--conversation-limit",
        type=int,
        default=10,
        help="Maximum conversations to fetch (default: 10)",
    )
    parser.add_argument(
        "--meeting-limit",
        type=int,
        default=5,
        help="Maximum meeting notes to fetch (default: 5)",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug output",
    )
    
    args = parser.parse_args()
    
    # Get context
    context = get_client_context(
        client_email=args.email,
        conversation_limit=args.conversation_limit,
        meeting_limit=args.meeting_limit,
        debug=args.debug,
    )
    
    # Output
    print(json.dumps(context, indent=2, default=str))


if __name__ == "__main__":
    main()
