#!/usr/bin/env python3
"""
Supabase Upsert Script
Insert new row or update if exists (based on unique constraint)
"""

import argparse
import json
import os
import sys

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


def upsert_row(
    table: str,
    data: dict,
    match_column: str,
    debug: bool = False,
) -> dict:
    """
    Upsert a row (insert or update on conflict).
    
    Args:
        table: Table name
        data: Dict to upsert
        match_column: Column(s) to match for conflict (e.g., "email")
        debug: Enable debug output
        
    Returns:
        Dict with upserted data
    """
    supabase = get_supabase_client()
    
    if debug:
        print(f"Upserting into table: {table}", file=sys.stderr)
        print(f"Match column: {match_column}", file=sys.stderr)
        print(f"Data: {json.dumps(data, indent=2)}", file=sys.stderr)
    
    try:
        # Supabase upsert with on_conflict parameter
        result = supabase.table(table).upsert(
            data,
            on_conflict=match_column
        ).execute()
        
        if debug:
            print(f"Upserted successfully", file=sys.stderr)
        
        return {
            "data": result.data,
            "count": len(result.data) if isinstance(result.data, list) else 1,
        }
    
    except Exception as e:
        print(f"Error: Upsert failed: {e}", file=sys.stderr)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Upsert row into Supabase table (insert or update on conflict)"
    )
    parser.add_argument(
        "--table",
        required=True,
        help="Table name",
    )
    parser.add_argument(
        "--match",
        required=True,
        help="Column(s) to match for conflict (e.g., 'client_email')",
    )
    parser.add_argument(
        "--data",
        required=True,
        help="JSON object to upsert",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug output",
    )
    
    args = parser.parse_args()
    
    # Parse data
    try:
        data = json.loads(args.data)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON data: {e}", file=sys.stderr)
        sys.exit(1)
    
    # Upsert
    result = upsert_row(
        table=args.table,
        data=data,
        match_column=args.match,
        debug=args.debug,
    )
    
    # Output
    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
