#!/usr/bin/env python3
"""
Gmail Monitoring Script
Lists unread emails within a time range for property agent workflow
"""

import argparse
import json
import os
import sys
from datetime import datetime, timedelta
from typing import List, Dict

# Add parent directory to path for importing google-workspace scripts
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../google-workspace/scripts"))

try:
    from google_auth import get_gmail_service
    from googleapiclient.errors import HttpError
except ImportError:
    print("Error: google-workspace skill required. See /skills/google-workspace/", file=sys.stderr)
    sys.exit(1)


def parse_time_string(time_str: str) -> datetime:
    """Parse time string (duration like '1h' or ISO timestamp)."""
    if time_str.endswith("h"):
        hours = int(time_str[:-1])
        return datetime.utcnow() - timedelta(hours=hours)
    elif time_str.endswith("m"):
        minutes = int(time_str[:-1])
        return datetime.utcnow() - timedelta(minutes=minutes)
    elif time_str.endswith("d"):
        days = int(time_str[:-1])
        return datetime.utcnow() - timedelta(days=days)
    else:
        # Assume ISO timestamp
        return datetime.fromisoformat(time_str.replace("Z", "+00:00"))


def check_gmail(
    since: str = "1h",
    until: str = None,
    unread_only: bool = True,
    debug: bool = False,
) -> List[Dict]:
    """
    Check Gmail for new messages.
    
    Args:
        since: Time range start (duration like "1h" or ISO timestamp)
        until: Time range end (ISO timestamp, optional)
        unread_only: Only fetch unread messages
        debug: Enable debug output
        
    Returns:
        List of email dicts
    """
    service = get_gmail_service()
    
    # Parse time range
    since_dt = parse_time_string(since)
    until_dt = parse_time_string(until) if until else datetime.utcnow()
    
    if debug:
        print(f"Checking Gmail from {since_dt} to {until_dt}", file=sys.stderr)
    
    # Build query
    query_parts = []
    
    # Time range (Gmail uses RFC 3339)
    after_str = since_dt.strftime("%Y/%m/%d")
    query_parts.append(f"after:{after_str}")
    
    if until:
        before_str = until_dt.strftime("%Y/%m/%d")
        query_parts.append(f"before:{before_str}")
    
    # Unread filter
    if unread_only:
        query_parts.append("is:unread")
    
    # Exclude common noise
    query_parts.append("-category:promotions")
    query_parts.append("-category:social")
    query_parts.append("-category:updates")
    
    query = " ".join(query_parts)
    
    if debug:
        print(f"Gmail query: {query}", file=sys.stderr)
    
    try:
        # List messages
        results = service.users().messages().list(
            userId="me",
            q=query,
            maxResults=100,
        ).execute()
        
        messages = results.get("messages", [])
        
        if debug:
            print(f"Found {len(messages)} messages", file=sys.stderr)
        
        # Fetch full message details
        emails = []
        for msg in messages:
            msg_id = msg["id"]
            
            try:
                full_msg = service.users().messages().get(
                    userId="me",
                    id=msg_id,
                    format="metadata",
                    metadataHeaders=["From", "Subject", "Date"],
                ).execute()
                
                headers = {h["name"]: h["value"] for h in full_msg["payload"]["headers"]}
                
                emails.append({
                    "id": msg_id,
                    "thread_id": full_msg.get("threadId"),
                    "from": headers.get("From", ""),
                    "subject": headers.get("Subject", ""),
                    "snippet": full_msg.get("snippet", ""),
                    "date": headers.get("Date", ""),
                    "labels": full_msg.get("labelIds", []),
                })
            
            except HttpError as e:
                if debug:
                    print(f"Warning: Failed to fetch message {msg_id}: {e}", file=sys.stderr)
                continue
        
        return emails
    
    except HttpError as e:
        print(f"Error: Gmail API request failed: {e}", file=sys.stderr)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Check Gmail for new emails (property agent workflow)"
    )
    parser.add_argument(
        "--since",
        default="1h",
        help="Time range start (e.g., '1h', '24h', '2026-03-03T10:00:00Z')",
    )
    parser.add_argument(
        "--until",
        help="Time range end (ISO timestamp, optional)",
    )
    parser.add_argument(
        "--unread-only",
        action="store_true",
        default=True,
        help="Only fetch unread messages (default: true)",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug output",
    )
    
    args = parser.parse_args()
    
    # Check Gmail
    emails = check_gmail(
        since=args.since,
        until=args.until,
        unread_only=args.unread_only,
        debug=args.debug,
    )
    
    # Output
    print(json.dumps({
        "emails": emails,
        "count": len(emails),
    }, indent=2))


if __name__ == "__main__":
    main()
