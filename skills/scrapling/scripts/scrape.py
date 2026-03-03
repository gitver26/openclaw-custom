#!/usr/bin/env python3
"""
Scrapling Web Scraper - Advanced web scraping with anti-bot evasion

This script wraps the Scrapling library for use with OpenClaw.
It handles JavaScript rendering, complex selectors, and structured data extraction.

Usage:
    python3 scrape.py --url "https://example.com" --mode text
    python3 scrape.py --url "https://example.com" --mode structured --selectors '{...}'
    python3 scrape.py --url "https://example.com" --mode links --render-js

Modes:
    text       - Extract readable text content
    html       - Return raw HTML
    structured - Extract data using CSS/XPath selectors (requires --selectors)
    links      - Extract all links from the page

Examples:
    # Simple text extraction
    python3 scrape.py --url "https://news.site.com/article" --mode text

    # Property listings with structured data
    python3 scrape.py --url "https://realty.com/listings" --mode structured \\
      --selectors '{"title": ".property-title", "price": ".price"}'

    # JavaScript-rendered SPA
    python3 scrape.py --url "https://spa-site.com" --mode text --render-js
"""

import argparse
import json
import sys
from typing import Dict, Any, Optional

try:
    from scrapling import Fetcher
except ImportError:
    print(json.dumps({
        "error": "Scrapling not installed. Run: pip3 install scrapling",
        "success": False
    }))
    sys.exit(1)


def scrape_text(page) -> str:
    """Extract readable text from page."""
    # Try to get main content first, fallback to full text
    main_content = page.css_first("main, article, .content, #content")
    if main_content:
        return main_content.text.strip()
    return page.text.strip()


def scrape_html(page) -> str:
    """Return raw HTML."""
    return page.html


def scrape_links(page) -> list:
    """Extract all links from page."""
    links = []
    for link in page.css("a"):
        href = link.attrs.get("href")
        text = link.text.strip()
        if href:
            links.append({
                "url": href,
                "text": text if text else None
            })
    return links


def scrape_structured(page, selectors: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract structured data using CSS/XPath selectors.
    
    Selector format:
    {
        "field_name": "css_selector",
        "field_name": {
            "selector": "css_selector",
            "attr": "href",  # optional: extract attribute instead of text
            "multiple": True  # optional: return list of matches
        },
        "nested": {
            "selector": ".parent",
            "multiple": True,
            "fields": {
                "sub_field": ".child"
            }
        }
    }
    """
    result = {}
    
    for field_name, selector_config in selectors.items():
        # Simple string selector
        if isinstance(selector_config, str):
            element = page.css_first(selector_config)
            result[field_name] = element.text.strip() if element else None
            
        # Complex selector configuration
        elif isinstance(selector_config, dict):
            selector = selector_config.get("selector")
            attr = selector_config.get("attr")
            multiple = selector_config.get("multiple", False)
            fields = selector_config.get("fields")
            
            if not selector:
                result[field_name] = None
                continue
            
            # Handle nested fields
            if fields:
                if multiple:
                    elements = page.css(selector)
                    result[field_name] = []
                    for elem in elements:
                        item = {}
                        for sub_field, sub_selector in fields.items():
                            if isinstance(sub_selector, str):
                                sub_elem = elem.css_first(sub_selector)
                                item[sub_field] = sub_elem.text.strip() if sub_elem else None
                            elif isinstance(sub_selector, dict):
                                sub_elem = elem.css_first(sub_selector.get("selector", ""))
                                if sub_elem:
                                    if sub_selector.get("attr"):
                                        item[sub_field] = sub_elem.attrs.get(sub_selector["attr"])
                                    else:
                                        item[sub_field] = sub_elem.text.strip()
                                else:
                                    item[sub_field] = None
                        result[field_name].append(item)
                else:
                    element = page.css_first(selector)
                    if element:
                        item = {}
                        for sub_field, sub_selector in fields.items():
                            if isinstance(sub_selector, str):
                                sub_elem = element.css_first(sub_selector)
                                item[sub_field] = sub_elem.text.strip() if sub_elem else None
                            elif isinstance(sub_selector, dict):
                                sub_elem = element.css_first(sub_selector.get("selector", ""))
                                if sub_elem:
                                    if sub_selector.get("attr"):
                                        item[sub_field] = sub_elem.attrs.get(sub_selector["attr"])
                                    else:
                                        item[sub_field] = sub_elem.text.strip()
                                else:
                                    item[sub_field] = None
                        result[field_name] = item
                    else:
                        result[field_name] = None
            
            # Handle simple multiple elements
            elif multiple:
                elements = page.css(selector)
                if attr:
                    result[field_name] = [e.attrs.get(attr) for e in elements if e.attrs.get(attr)]
                else:
                    result[field_name] = [e.text.strip() for e in elements]
            
            # Handle single element
            else:
                element = page.css_first(selector)
                if element:
                    if attr:
                        result[field_name] = element.attrs.get(attr)
                    else:
                        result[field_name] = element.text.strip()
                else:
                    result[field_name] = None
    
    return result


def main():
    parser = argparse.ArgumentParser(
        description="Advanced web scraping with Scrapling",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument(
        "--url",
        required=True,
        help="Target URL to scrape"
    )
    
    parser.add_argument(
        "--mode",
        choices=["text", "html", "structured", "links"],
        default="text",
        help="Output mode (default: text)"
    )
    
    parser.add_argument(
        "--selectors",
        type=str,
        help="JSON object defining CSS/XPath selectors for structured mode"
    )
    
    parser.add_argument(
        "--render-js",
        action="store_true",
        help="Enable JavaScript rendering (slower, for dynamic content)"
    )
    
    parser.add_argument(
        "--proxy",
        type=str,
        help="Proxy URL (e.g., http://proxy:8080)"
    )
    
    parser.add_argument(
        "--timeout",
        type=int,
        default=30,
        help="Request timeout in seconds (default: 30)"
    )
    
    parser.add_argument(
        "--user-agent",
        type=str,
        help="Custom user agent string"
    )
    
    parser.add_argument(
        "--output",
        type=str,
        help="Save output to file instead of stdout"
    )
    
    args = parser.parse_args()
    
    # Validate selectors for structured mode
    selectors = None
    if args.mode == "structured":
        if not args.selectors:
            print(json.dumps({
                "error": "Structured mode requires --selectors argument",
                "success": False
            }))
            sys.exit(1)
        
        try:
            selectors = json.loads(args.selectors)
        except json.JSONDecodeError as e:
            print(json.dumps({
                "error": f"Invalid JSON in --selectors: {str(e)}",
                "success": False
            }))
            sys.exit(1)
    
    # Configure fetcher
    fetcher_kwargs = {
        "timeout": args.timeout,
    }
    
    if args.proxy:
        fetcher_kwargs["proxy"] = args.proxy
    
    if args.user_agent:
        fetcher_kwargs["headers"] = {"User-Agent": args.user_agent}
    
    try:
        # Create fetcher and fetch page
        fetcher = Fetcher(**fetcher_kwargs)
        
        fetch_kwargs = {"render_js": args.render_js}
        page = fetcher.get(args.url, **fetch_kwargs)
        
        # Extract data based on mode
        if args.mode == "text":
            output_data = {
                "success": True,
                "url": args.url,
                "content": scrape_text(page),
                "mode": "text"
            }
        
        elif args.mode == "html":
            output_data = {
                "success": True,
                "url": args.url,
                "content": scrape_html(page),
                "mode": "html"
            }
        
        elif args.mode == "links":
            output_data = {
                "success": True,
                "url": args.url,
                "links": scrape_links(page),
                "mode": "links"
            }
        
        elif args.mode == "structured":
            output_data = {
                "success": True,
                "url": args.url,
                "data": scrape_structured(page, selectors),
                "mode": "structured"
            }
        
        # Output results
        output_json = json.dumps(output_data, indent=2, ensure_ascii=False)
        
        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(output_json)
            print(json.dumps({
                "success": True,
                "message": f"Output saved to {args.output}"
            }))
        else:
            print(output_json)
    
    except Exception as e:
        error_output = {
            "success": False,
            "error": str(e),
            "url": args.url,
            "mode": args.mode
        }
        print(json.dumps(error_output, indent=2))
        sys.exit(1)


if __name__ == "__main__":
    main()
