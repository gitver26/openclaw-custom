#!/usr/bin/env python3
"""
Ragie.ai Connection Test Script
Verifies API credentials and connectivity
"""

import json
import os
import sys

try:
    import requests
except ImportError:
    print("Error: requests library not installed. Run: pip3 install requests", file=sys.stderr)
    sys.exit(1)


def test_connection():
    """Test Ragie.ai API connection."""
    
    # Check API key
    api_key = os.environ.get("RAGIE_API_KEY")
    if not api_key:
        print("❌ RAGIE_API_KEY environment variable not set", file=sys.stderr)
        sys.exit(1)
    
    print("✅ API key found")
    
    # Try a simple API call
    base_url = "https://api.ragie.ai/v1"
    headers = {
        "Authorization": f"Bearer {api_key}",
    }
    
    try:
        print("Testing API connection...")
        response = requests.get(
            f"{base_url}/documents",
            params={"limit": 1},
            headers=headers,
            timeout=10,
        )
        response.raise_for_status()
        
        result = response.json()
        doc_count = result.get("total", 0)
        
        print(f"✅ API connection successful")
        print(f"✅ Found {doc_count} indexed documents")
        
        if doc_count == 0:
            print("\n⚠️  Warning: No documents indexed yet")
            print("   → Connect Google Drive or upload documents at https://ragie.ai")
        
        print("\n🎉 Ragie.ai is ready to use!")
        
    except requests.exceptions.HTTPError as e:
        print(f"❌ API request failed with status {e.response.status_code}", file=sys.stderr)
        try:
            error_detail = e.response.json()
            print(f"❌ Error: {json.dumps(error_detail, indent=2)}", file=sys.stderr)
        except:
            print(f"❌ Error body: {e.response.text}", file=sys.stderr)
        
        if e.response.status_code == 401:
            print("\n💡 Tip: Check that your API key is valid at https://ragie.ai/settings", file=sys.stderr)
        
        sys.exit(1)
    
    except requests.exceptions.RequestException as e:
        print(f"❌ Network request failed: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    test_connection()
