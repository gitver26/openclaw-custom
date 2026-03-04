#!/usr/bin/env python3
"""
Supabase Insert Script
Insert new rows into a table
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


def insert_rows(
    table: str,
    data: dict or list,
    debug: bool = False,
) -> dict:
    """
    Insert rows into a Supabase table.
    
    Args:
        table: Table name
        data: Dict (single row) or list of dicts (multiple rows)
        debug: Enable debug output
        
    Returns:
        Dict with inserted data
    """
    supabase = get_supabase_client()
    
    if debug:
        print(f"Inserting into table: {table}", file=sys.stderr)
        print(f"Data: {json.dumps(data, indent=2)}", file=sys.stderr)
    
    try:
        result = supabase.table(table).insert(data).execute()
        
        if debug:
            print(f"Inserted {len(result.data) if isinstance(result.data, list) else 1} rows", file=sys.stderr)
        
        return {
            "data": result.data,
            "count": len(result.data) if isinstance(result.data, list) else 1,
        }
    
    except Exception as e:
        print(f"Error: Insert failed: {e}", file=sys.stderr)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Insert rows into Supabase table"
    )
    parser.add_argument(
        "--table",
        required=True,
        help="Table name",
    )
    parser.add_argument(
        "--data",
        required=True,
        help="JSON object or array to insert",
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
    
    # Insert
    result = insert_rows(
        table=args.table,
        data=data,
        debug=args.debug,
    )
    
    # Output
    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
