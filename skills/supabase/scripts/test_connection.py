#!/usr/bin/env python3
"""
Supabase Connection Test Script
Verifies database credentials and connectivity
"""

import json
import os
import sys

try:
    from supabase import create_client
except ImportError:
    print("Error: supabase library not installed. Run: pip3 install supabase", file=sys.stderr)
    sys.exit(1)


def test_connection():
    """Test Supabase connection."""
    
    # Check environment variables
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_KEY")
    
    if not url:
        print("❌ SUPABASE_URL environment variable not set", file=sys.stderr)
        sys.exit(1)
    
    if not key:
        print("❌ SUPABASE_SERVICE_KEY environment variable not set", file=sys.stderr)
        sys.exit(1)
    
    print("✅ Environment variables found")
    print(f"   URL: {url}")
    
    # Try to connect
    try:
        print("Testing database connection...")
        supabase = create_client(url, key)
        
        # Try a simple query
        result = supabase.table("information_schema.tables") \
            .select("table_name") \
            .limit(1) \
            .execute()
        
        print("✅ Database connection successful")
        
        # List tables in public schema
        tables_result = supabase.rpc("exec_sql", {
            "sql": "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' ORDER BY table_name"
        }).execute()
        
        if tables_result.data:
            print(f"✅ Found {len(tables_result.data)} tables in public schema:")
            for table in tables_result.data:
                print(f"   - {table['table_name']}")
        else:
            print("\n⚠️  No tables found in public schema")
            print("   → Create tables using SQL Editor in Supabase dashboard")
        
        print("\n🎉 Supabase is ready to use!")
        
    except Exception as e:
        print(f"❌ Connection failed: {e}", file=sys.stderr)
        print("\n💡 Troubleshooting:", file=sys.stderr)
        print("   1. Verify SUPABASE_URL format: https://your-project.supabase.co", file=sys.stderr)
        print("   2. Verify you're using service_role key (starts with 'eyJ...')", file=sys.stderr)
        print("   3. Check project is not paused (free tier pauses after 1 week)", file=sys.stderr)
        print("   4. Test network connectivity: curl {url}".format(url=url), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    test_connection()
