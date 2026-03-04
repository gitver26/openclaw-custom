#!/usr/bin/env python3
"""
Ragie.ai Document Listing Script
Lists all documents indexed in Ragie.ai
"""

import argparse
import json
import os
import sys
from typing import Optional

try:
    import requests
except ImportError:
    print("Error: requests library not installed. Run: pip3 install requests", file=sys.stderr)
    sys.exit(1)


def get_api_key() -> str:
    """Get Ragie API key from environment."""
    api_key = os.environ.get("RAGIE_API_KEY")
    if not api_key:
        print("Error: RAGIE_API_KEY environment variable not set", file=sys.stderr)
        sys.exit(1)
    return api_key


def list_documents(
    limit: int = 50,
    offset: int = 0,
    source_filter: Optional[str] = None,
    debug: bool = False,
) -> dict:
    """
    List documents in Ragie.ai index.
    
    Args:
        limit: Maximum number of documents to return
        offset: Pagination offset
        source_filter: Filter by source type (e.g., "google_drive", "upload")
        debug: Enable debug output
        
    Returns:
        Dict with document list
    """
    api_key = get_api_key()
    base_url = "https://api.ragie.ai/v1"
    
    params = {
        "limit": limit,
        "offset": offset,
    }
    
    if source_filter:
        params["source"] = source_filter
    
    headers = {
        "Authorization": f"Bearer {api_key}",
    }
    
    if debug:
        print(f"Request URL: {base_url}/documents", file=sys.stderr)
        print(f"Request params: {json.dumps(params, indent=2)}", file=sys.stderr)
    
    try:
        response = requests.get(
            f"{base_url}/documents",
            params=params,
            headers=headers,
            timeout=30,
        )
        response.raise_for_status()
        
        result = response.json()
        
        if debug:
            print(f"Response status: {response.status_code}", file=sys.stderr)
            print(f"Response body: {json.dumps(result, indent=2)}", file=sys.stderr)
        
        # Format response
        documents = result.get("documents", [])
        formatted_docs = []
        
        for doc in documents:
            formatted_docs.append({
                "id": doc.get("id"),
                "name": doc.get("name", "Unknown"),
                "source": doc.get("source", "unknown"),
                "indexed_at": doc.get("created_at"),
                "chunk_count": doc.get("chunk_count", 0),
                "url": doc.get("url"),
            })
        
        return {
            "documents": formatted_docs,
            "total": result.get("total", len(formatted_docs)),
            "limit": limit,
            "offset": offset,
        }
    
    except requests.exceptions.HTTPError as e:
        print(f"Error: API request failed with status {e.response.status_code}", file=sys.stderr)
        try:
            error_detail = e.response.json()
            print(f"Error details: {json.dumps(error_detail, indent=2)}", file=sys.stderr)
        except:
            print(f"Error body: {e.response.text}", file=sys.stderr)
        sys.exit(1)
    
    except requests.exceptions.RequestException as e:
        print(f"Error: Network request failed: {e}", file=sys.stderr)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="List documents indexed in Ragie.ai"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=50,
        help="Maximum number of documents to return (default: 50)",
    )
    parser.add_argument(
        "--offset",
        type=int,
        default=0,
        help="Pagination offset (default: 0)",
    )
    parser.add_argument(
        "--source-filter",
        help="Filter by source type (e.g., google_drive, upload)",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug output",
    )
    
    args = parser.parse_args()
    
    # List documents
    result = list_documents(
        limit=args.limit,
        offset=args.offset,
        source_filter=args.source_filter,
        debug=args.debug,
    )
    
    # Output
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
