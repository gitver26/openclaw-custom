---
name: scrapling
description: Advanced web scraping for dynamic content and property listings. Use when standard web_fetch fails, when scraping JavaScript-rendered pages, property websites, e-commerce sites, or pages with anti-bot protection. Handles complex selectors, pagination, and data extraction.
metadata:
  {
    "openclaw":
      {
        "emoji": "🕷️",
        "requires": { "bins": ["python3"], "packages": ["scrapling"] },
        "install":
          [
            {
              "id": "pip",
              "kind": "pip",
              "package": "scrapling",
              "label": "Install Scrapling (pip)",
            },
          ],
      },
  }
---

# Scrapling — Advanced Web Scraping Skill

Scrapling is a powerful Python library for scraping JavaScript-rendered pages, bypassing anti-bot measures, and extracting structured data from complex websites like property listings, e-commerce sites, and dynamic content.

## ⚠️ Security Warning

**This skill executes arbitrary Python code and fetches untrusted content from the internet.**

**Required before use:**

- Run in a **sandboxed environment** (never on your daily driver)
- Configure **URL allowlisting** to prevent SSRF attacks
- Enable **network policies** to block private IP ranges
- Review **[SECURITY.md](SECURITY.md)** for complete threat model and hardening guide
- Understand that scraped content is **untrusted input** (prompt injection risk)

**Minimum safe config:**

```json5
{
  agents: {
    list: [
      {
        id: "scraper",
        sandbox: { mode: "all", scope: "agent" },
        tools: { deny: ["process", "exec"] },
      },
    ],
  },
}
```

See [SECURITY.md](SECURITY.md) for production-grade configurations.

## When to Use This Skill

- Property listing websites (real estate, rentals)
- JavaScript-rendered single-page applications
- Sites with anti-bot protection or CAPTCHAs
- Pagination and infinite scroll
- Complex data extraction requiring CSS/XPath selectors
- When `web_fetch` returns incomplete or missing content

## Installation

```bash
pip3 install scrapling
```

## Quick Examples

### Basic URL Scraping

```bash
python3 scripts/scrape.py --url "https://example.com" --mode text
```

### Property Listing Extraction

```bash
python3 scripts/scrape.py \
  --url "https://property-site.com/listings" \
  --mode structured \
  --selectors '{
    "title": ".property-title",
    "price": ".property-price",
    "address": ".property-address",
    "description": ".property-description"
  }'
```

### Extract Links

```bash
python3 scripts/scrape.py --url "https://example.com" --mode links
```

### With JavaScript Rendering

```bash
python3 scripts/scrape.py \
  --url "https://spa-website.com" \
  --mode structured \
  --render-js \
  --selectors '{
    "listings": {
      "selector": ".listing-card",
      "multiple": true,
      "fields": {
        "title": ".title",
        "price": ".price"
      }
    }
  }'
```

## Script Usage

The `scripts/scrape.py` helper provides:

- **URL fetching** with automatic retry and anti-bot evasion
- **Multiple output modes**: text, html, structured (JSON), links
- **CSS/XPath selectors** for precise data extraction
- **JavaScript rendering** for dynamic content
- **Pagination support** for multi-page scraping
- **Proxy support** with automatic rotation

### Command-Line Arguments

```
--url           Target URL to scrape
--mode          Output mode: text, html, structured, links (default: text)
--selectors     JSON object defining CSS/XPath selectors for structured mode
--render-js     Enable JavaScript rendering (slower, more reliable)
--proxy         Proxy URL (http://proxy:port)
--timeout       Request timeout in seconds (default: 30)
--user-agent    Custom user agent string
--output        Save output to file instead of stdout
```

## Common Patterns

### Property Listings

```python
selectors = {
    "listings": {
        "selector": ".property-card",
        "multiple": True,
        "fields": {
            "title": ".property-title",
            "price": ".price-value",
            "bedrooms": ".bedrooms",
            "bathrooms": ".bathrooms",
            "sqft": ".square-feet",
            "address": ".address",
            "url": {"selector": "a.property-link", "attr": "href"},
            "image": {"selector": "img.main-photo", "attr": "src"}
        }
    }
}
```

### Pagination

```python
# Extract next page URL
next_page_selector = {
    "next_page": {"selector": "a.next-page", "attr": "href"}
}
```

### E-commerce Products

```python
selectors = {
    "products": {
        "selector": ".product-item",
        "multiple": True,
        "fields": {
            "name": "h3.product-name",
            "price": ".price",
            "rating": ".star-rating::attr(data-rating)",
            "reviews": ".review-count",
            "availability": ".stock-status"
        }
    }
}
```

## Troubleshooting

### Content Not Loading

- Enable `--render-js` for JavaScript-heavy sites
- Increase `--timeout` for slow-loading pages
- Try different `--user-agent` strings

### Anti-Bot Blocks

- Use `--proxy` with rotating proxies
- Add delays between requests
- Use realistic user agent strings

### Selector Issues

- Inspect page HTML to find correct selectors
- Use browser DevTools to test CSS selectors
- Try XPath if CSS selectors aren't working

## Advanced: Python API

For custom scripts, use Scrapling's Python API directly:

```python
from scrapling import Fetcher

# Basic fetch
fetcher = Fetcher()
page = fetcher.get("https://example.com")
print(page.text)

# With selectors
title = page.css_first(".title::text")
links = page.css("a::attr(href)")

# JavaScript rendering
page = fetcher.get("https://spa-site.com", render_js=True)

# Extract structured data
data = page.extract({
    "title": ".title",
    "items": {
        "selector": ".item",
        "multiple": True,
        "fields": {
            "name": ".name",
            "price": ".price"
        }
    }
})
```

## Performance Notes

- Standard mode: Fast, lightweight, no JS execution
- JavaScript mode (`--render-js`): Slower, uses headless browser, better for SPAs
- Caching: Results aren't cached by default (unlike `web_fetch`)
- Rate limiting: Respect site ToS, add delays for bulk scraping

## Comparison with web_fetch

| Feature              | web_fetch | scrapling         |
| -------------------- | --------- | ----------------- |
| JavaScript rendering | ❌        | ✅                |
| Anti-bot evasion     | ❌        | ✅                |
| Complex selectors    | ❌        | ✅                |
| Structured data      | ❌        | ✅                |
| Speed                | Fast      | Medium-Slow       |
| Caching              | ✅        | ❌ (customizable) |
| Best for             | Articles  | Dynamic sites     |

## See Also

- [Web Tools](/tools/web) - Built-in web_fetch and web_search
- [Browser Tool](/tools/browser) - Full browser automation
- Scrapling docs: https://github.com/D4Vinci/Scrapling
