# Scrapling Skill for OpenClaw

Advanced web scraping skill using [Scrapling](https://github.com/D4Vinci/Scrapling) - handles JavaScript-rendered pages, anti-bot protection, and complex data extraction.

## Quick Start

1. **Install Scrapling**:

   ```bash
   pip3 install scrapling
   ```

2. **Basic usage**:

   ```bash
   python3 scripts/scrape.py --url "https://example.com" --mode text
   ```

3. **Property listings**:
   ```bash
   python3 scripts/scrape.py \
     --url "https://property-site.com/listings" \
     --mode structured \
     --selectors '{"title": ".property-title", "price": ".price"}'
   ```

## Files

- **SKILL.md** - Main skill documentation (loaded by OpenClaw)
- **scripts/scrape.py** - Main scraping script
- **references/property-patterns.md** - Common property website patterns

## Features

✅ JavaScript rendering for dynamic sites  
✅ Anti-bot evasion  
✅ Complex CSS/XPath selectors  
✅ Structured data extraction  
✅ Pagination support  
✅ Proxy support

## When to Use

Use this skill when:

- Standard `web_fetch` fails or returns incomplete data
- Scraping property listing websites
- Handling JavaScript-rendered single-page apps
- Sites with anti-bot protection
- Need structured data extraction

## Modes

- `text` - Readable text extraction
- `html` - Raw HTML
- `structured` - JSON data using CSS selectors
- `links` - Extract all links

## See SKILL.md for full documentation
