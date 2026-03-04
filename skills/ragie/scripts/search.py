#!/usr/bin/env python3
"""
Ragie.ai RAG Search Script
Performs semantic search across indexed documents in Ragie.ai
"""

import argparse
import json
import os
import sys
from typing import Any, Dict, List, Optional

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


def search_ragie(
    query: str,
    max_results: int = 5,
    file_types: Optional[List[str]] = None,
    metadata_filter: Optional[Dict[str, Any]] = None,
    rerank: bool = False,
    rerank_top_k: int = 3,
    debug: bool = False,
) -> Dict[str, Any]:
    """
    Search Ragie.ai index for relevant documents.
    
    Args:
        query: Search query text
        max_results: Number of results to return
        file_types: List of file extensions to filter (e.g., ["pdf", "docx"])
        metadata_filter: Dict of metadata filters
        rerank: Enable reranking for better relevance
        rerank_top_k: Number of top results after reranking
        debug: Enable debug output
        
    Returns:
        Dict with search results
    """
    api_key = get_api_key()
    base_url = "https://api.ragie.ai/v1"
    
    # Build request payload
    payload = {
        "query": query,
        "top_k": max_results,
        "rerank": rerank,
    }
    
    if rerank:
        payload["rerank_top_k"] = rerank_top_k
    
    if file_types:
        payload["file_types"] = file_types
    
    if metadata_filter:
        payload["filter"] = metadata_filter
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    
    if debug:
        print(f"Request URL: {base_url}/search", file=sys.stderr)
        print(f"Request payload: {json.dumps(payload, indent=2)}", file=sys.stderr)
    
    try:
        response = requests.post(
            f"{base_url}/search",
            json=payload,
            headers=headers,
            timeout=30,
        )
        response.raise_for_status()
        
        result = response.json()
        
        if debug:
            print(f"Response status: {response.status_code}", file=sys.stderr)
            print(f"Response body: {json.dumps(result, indent=2)}", file=sys.stderr)
        
        return result
    
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


def format_search_results(results: Dict[str, Any], mode: str = "search") -> Dict[str, Any]:
    """
    Format search results for different output modes.
    
    Args:
        results: Raw API response
        mode: Output mode (search|snippets|sources)
        
    Returns:
        Formatted results dict
    """
    chunks = results.get("scored_chunks", [])
    
    if mode == "snippets":
        # Return just text snippets
        return {
            "query": results.get("query", ""),
            "snippets": [chunk.get("text", "") for chunk in chunks],
            "total": len(chunks),
        }
    
    elif mode == "sources":
        # Return document metadata only
        sources = {}
        for chunk in chunks:
            doc = chunk.get("document", {})
            doc_id = doc.get("id")
            if doc_id and doc_id not in sources:
                sources[doc_id] = {
                    "id": doc_id,
                    "name": doc.get("name", "Unknown"),
                    "source": doc.get("source", "unknown"),
                    "url": doc.get("url"),
                }
        
        return {
            "query": results.get("query", ""),
            "sources": list(sources.values()),
            "total": len(sources),
        }
    
    else:  # mode == "search"
        # Return full chunks with metadata
        formatted_chunks = []
        for chunk in chunks:
            formatted_chunks.append({
                "chunk_id": chunk.get("id"),
                "text": chunk.get("text", ""),
                "score": chunk.get("score", 0.0),
                "document": {
                    "id": chunk.get("document", {}).get("id"),
                    "name": chunk.get("document", {}).get("name", "Unknown"),
                    "source": chunk.get("document", {}).get("source", "unknown"),
                    "url": chunk.get("document", {}).get("url"),
                },
            })
        
        return {
            "query": results.get("query", ""),
            "results": formatted_chunks,
            "total": len(formatted_chunks),
        }


def main():
    parser = argparse.ArgumentParser(
        description="Search Ragie.ai knowledge base for relevant documents"
    )
    parser.add_argument(
        "--query",
        required=True,
        help="Search query text",
    )
    parser.add_argument(
        "--max-results",
        type=int,
        default=5,
        help="Maximum number of results to return (default: 5)",
    )
    parser.add_argument(
        "--file-types",
        help="Comma-separated file extensions (e.g., pdf,docx,txt)",
    )
    parser.add_argument(
        "--filter",
        help="JSON metadata filter (e.g., '{\"property_type\": \"condo\"}')",
    )
    parser.add_argument(
        "--rerank",
        action="store_true",
        help="Enable reranking for better relevance (slower, more accurate)",
    )
    parser.add_argument(
        "--rerank-top-k",
        type=int,
        default=3,
        help="Number of top results after reranking (default: 3)",
    )
    parser.add_argument(
        "--mode",
        choices=["search", "snippets", "sources"],
        default="search",
        help="Output mode: search (full), snippets (text only), sources (metadata only)",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug output",
    )
    
    args = parser.parse_args()
    
    # Parse file types
    file_types = None
    if args.file_types:
        file_types = [ft.strip() for ft in args.file_types.split(",")]
    
    # Parse metadata filter
    metadata_filter = None
    if args.filter:
        try:
            metadata_filter = json.loads(args.filter)
        except json.JSONDecodeError as e:
            print(f"Error: Invalid JSON filter: {e}", file=sys.stderr)
            sys.exit(1)
    
    # Perform search
    results = search_ragie(
        query=args.query,
        max_results=args.max_results,
        file_types=file_types,
        metadata_filter=metadata_filter,
        rerank=args.rerank,
        rerank_top_k=args.rerank_top_k,
        debug=args.debug,
    )
    
    # Format and output
    formatted = format_search_results(results, mode=args.mode)
    print(json.dumps(formatted, indent=2))


if __name__ == "__main__":
    main()
