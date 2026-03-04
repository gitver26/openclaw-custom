#!/usr/bin/env python3
"""
Supabase Query Script
Fetch rows from any table with filtering and ordering
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


def query_table(
    table: str,
    filter_str: Optional[str] = None,
    order: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    select: str = "*",
    single: bool = False,
    debug: bool = False,
) -> dict:
    """
    Query a Supabase table.
    
    Args:
        table: Table name
        filter_str: PostgREST filter (e.g., "email=eq.test@example.com")
        order: Order by column (e.g., "created_at.desc")
        limit: Maximum rows to return
        offset: Pagination offset
        select: Columns to select
        single: Return single row instead of array
        debug: Enable debug output
        
    Returns:
        Dict with data and count
    """
    supabase = get_supabase_client()
    
    if debug:
        print(f"Querying table: {table}", file=sys.stderr)
        print(f"Filter: {filter_str}", file=sys.stderr)
        print(f"Order: {order}", file=sys.stderr)
        print(f"Limit: {limit}, Offset: {offset}", file=sys.stderr)
    
    try:
        query = supabase.table(table).select(select)
        
        # Apply filter if provided
        if filter_str:
            # Parse PostgREST filter format: "column=operator.value"
            parts = filter_str.split("=", 1)
            if len(parts) == 2:
                column = parts[0]
                op_value = parts[1]
                
                if "." in op_value:
                    operator, value = op_value.split(".", 1)
                    
                    if operator == "eq":
                        query = query.eq(column, value)
                    elif operator == "neq":
                        query = query.neq(column, value)
                    elif operator == "gt":
                        query = query.gt(column, value)
                    elif operator == "gte":
                        query = query.gte(column, value)
                    elif operator == "lt":
                        query = query.lt(column, value)
                    elif operator == "lte":
                        query = query.lte(column, value)
                    elif operator == "like":
                        query = query.like(column, value)
                    elif operator == "ilike":
                        query = query.ilike(column, value)
                    elif operator == "is":
                        query = query.is_(column, value)
                    elif operator == "in":
                        # Parse array: (val1,val2,val3)
                        values = value.strip("()").split(",")
                        query = query.in_(column, values)
                    elif operator == "cs":
                        # Contains (for arrays): cs.{val1,val2}
                        values = value.strip("{}").split(",")
                        query = query.contains(column, values)
                    else:
                        print(f"Warning: Unknown operator '{operator}', skipping filter", file=sys.stderr)
        
        # Apply order
        if order:
            # Parse: "column.asc" or "column.desc"
            if "." in order:
                column, direction = order.rsplit(".", 1)
                ascending = direction.lower() == "asc"
                query = query.order(column, desc=not ascending)
            else:
                query = query.order(order)
        
        # Apply pagination
        query = query.limit(limit).offset(offset)
        
        # Execute
        if single:
            result = query.single().execute()
            data = result.data
            count = 1 if data else 0
        else:
            result = query.execute()
            data = result.data
            count = len(data)
        
        if debug:
            print(f"Returned {count} rows", file=sys.stderr)
        
        return {
            "data": data,
            "count": count,
        }
    
    except Exception as e:
        print(f"Error: Query failed: {e}", file=sys.stderr)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Query Supabase table with filters and ordering"
    )
    parser.add_argument(
        "--table",
        required=True,
        help="Table name",
    )
    parser.add_argument(
        "--filter",
        help="PostgREST filter (e.g., 'email=eq.test@example.com')",
    )
    parser.add_argument(
        "--order",
        help="Order by column (e.g., 'created_at.desc')",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=100,
        help="Maximum rows to return (default: 100)",
    )
    parser.add_argument(
        "--offset",
        type=int,
        default=0,
        help="Pagination offset (default: 0)",
    )
    parser.add_argument(
        "--select",
        default="*",
        help="Columns to select (default: '*')",
    )
    parser.add_argument(
        "--single",
        action="store_true",
        help="Return single row instead of array",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug output",
    )
    
    args = parser.parse_args()
    
    # Query table
    result = query_table(
        table=args.table,
        filter_str=args.filter,
        order=args.order,
        limit=args.limit,
        offset=args.offset,
        select=args.select,
        single=args.single,
        debug=args.debug,
    )
    
    # Output
    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
