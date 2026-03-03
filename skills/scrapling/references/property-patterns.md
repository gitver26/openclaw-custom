# Property Website Scraping Patterns

This reference provides common CSS selectors and patterns for popular property listing websites. Use these as starting points and adjust based on the specific site structure.

## Generic Property Listing Pattern

Most property websites follow similar patterns. Start with these selectors and inspect the HTML to refine:

```json
{
  "listings": {
    "selector": ".property, .listing, [data-testid*='property'], article",
    "multiple": true,
    "fields": {
      "title": "h2, h3, .title, .property-title, [class*='title']",
      "price": ".price, [class*='price'], [data-testid*='price']",
      "address": ".address, [class*='address'], [data-testid*='address']",
      "bedrooms": "[class*='bed'], [data-testid*='bed']",
      "bathrooms": "[class*='bath'], [data-testid*='bath']",
      "sqft": "[class*='sqft'], [class*='square']",
      "url": { "selector": "a", "attr": "href" },
      "image": { "selector": "img", "attr": "src" }
    }
  }
}
```

## Common Property Websites

### Zillow-style Sites

```json
{
  "listings": {
    "selector": "article[data-test='property-card'], .property-card",
    "multiple": true,
    "fields": {
      "title": "address, .list-card-addr",
      "price": ".list-card-price, [data-test='property-card-price']",
      "details": ".list-card-details",
      "beds": ".beds",
      "baths": ".baths",
      "sqft": ".sqft",
      "url": { "selector": "a.list-card-link", "attr": "href" },
      "zpid": { "selector": "article", "attr": "data-zpid" }
    }
  }
}
```

### Realtor.com-style Sites

```json
{
  "listings": {
    "selector": "[data-testid='property-card']",
    "multiple": true,
    "fields": {
      "address": "[data-testid='property-address']",
      "price": "[data-testid='property-price']",
      "beds": "[data-testid='property-beds']",
      "baths": "[data-testid='property-baths']",
      "sqft": "[data-testid='property-sqft']",
      "url": { "selector": "a[data-testid='property-anchor']", "attr": "href" }
    }
  }
}
```

### Apartments.com-style Rental Sites

```json
{
  "listings": {
    "selector": ".placard, .property-item",
    "multiple": true,
    "fields": {
      "name": ".property-title, h2.title",
      "price": ".price-range, .rent",
      "address": ".property-address",
      "beds": ".bed-range",
      "availability": ".availability",
      "amenities": { "selector": ".amenity", "multiple": true },
      "url": { "selector": "a.property-link", "attr": "href" },
      "phone": ".phone-link"
    }
  }
}
```

### Trulia-style Sites

```json
{
  "listings": {
    "selector": "[data-testid='home-card']",
    "multiple": true,
    "fields": {
      "price": "[data-testid='home-card-price']",
      "address": "[data-testid='home-card-address']",
      "beds": "[data-testid='home-card-beds']",
      "baths": "[data-testid='home-card-baths']",
      "sqft": "[data-testid='home-card-sqft']",
      "status": ".listing-status"
    }
  }
}
```

## International Property Sites

### UK Property Sites (Rightmove/Zoopla style)

```json
{
  "listings": {
    "selector": ".propertyCard, .listing-results-wrapper > div",
    "multiple": true,
    "fields": {
      "title": ".propertyCard-title, h2",
      "price": ".propertyCard-priceValue, .listing-price",
      "address": ".propertyCard-address, .listing-address",
      "description": ".propertyCard-description",
      "bedrooms": ".propertyCard-bed, .num-beds",
      "property_type": ".propertyCard-type"
    }
  }
}
```

### Australian Property Sites (Domain/Realestate.com.au style)

```json
{
  "listings": {
    "selector": "[data-testid='listing-card-wrapper']",
    "multiple": true,
    "fields": {
      "address": "[data-testid='address']",
      "price": "[data-testid='listing-card-price']",
      "beds": "[data-testid='property-features-beds']",
      "baths": "[data-testid='property-features-baths']",
      "parking": "[data-testid='property-features-parking']"
    }
  }
}
```

## Pagination Handling

### Common Pagination Patterns

```json
{
  "next_page": {
    "selector": "a.next, a[rel='next'], .pagination .next, [aria-label='Next page']",
    "attr": "href"
  }
}
```

### Page Number Extraction

```json
{
  "total_pages": ".total-pages, [aria-label*='total pages']",
  "current_page": ".current-page, [aria-current='page']",
  "page_links": {
    "selector": ".pagination a",
    "multiple": true,
    "attr": "href"
  }
}
```

## Dynamic Content Tips

### JavaScript-Rendered Sites

Many modern property sites use React/Vue/Angular and require JavaScript rendering:

```bash
# Enable JavaScript rendering
python3 scripts/scrape.py \
  --url "https://spa-property-site.com" \
  --render-js \
  --mode structured \
  --selectors '...'
```

### Infinite Scroll

For sites with infinite scroll, you may need to:

1. Use `--render-js` to trigger load
2. Scroll the page programmatically (requires custom script)
3. Look for API endpoints in browser DevTools Network tab

## Troubleshooting Selectors

### Finding the Right Selectors

1. **Open browser DevTools** (F12 or right-click → Inspect)
2. **Use selector tool** (click the arrow icon)
3. **Click on the element** you want to scrape
4. **Copy selector** (right-click in Elements panel → Copy → Copy selector)
5. **Test in console**: `document.querySelector("your-selector")`

### Common Issues

**Problem**: Selector returns null

```bash
# Solution: Try broader selectors with multiple fallbacks
"title": "h1, h2, .title, [class*='title'], [data-testid*='title']"
```

**Problem**: Getting wrong element

```bash
# Solution: Add more specific parent context
"selector": ".property-card .price"  # More specific than just ".price"
```

**Problem**: Content appears empty

```bash
# Solution: Use --render-js for dynamic content
--render-js
```

## Best Practices

1. **Start broad, then narrow**: Use flexible selectors that work across pages
2. **Multiple fallbacks**: Provide multiple selectors in case of changes
3. **Respect robots.txt**: Check site's scraping policy
4. **Add delays**: Don't hammer the server
5. **Cache results**: Save scraped data to avoid repeated requests
6. **Handle errors**: Not all fields will be present on all listings
7. **Check for APIs**: Property sites often have public APIs (check Network tab)

## Example: Full Property Search Workflow

```bash
# 1. Scrape search results page
python3 scripts/scrape.py \
  --url "https://propertysite.com/search?city=austin" \
  --mode structured \
  --render-js \
  --selectors '{
    "listings": {
      "selector": ".property-card",
      "multiple": true,
      "fields": {
        "title": ".title",
        "price": ".price",
        "url": {"selector": "a", "attr": "href"}
      }
    },
    "next_page": {"selector": "a.next", "attr": "href"}
  }' \
  --output results.json

# 2. Parse results and get individual listing URLs
# (Agent can read results.json and extract URLs)

# 3. Scrape individual listing detail page
python3 scripts/scrape.py \
  --url "https://propertysite.com/listing/123" \
  --mode structured \
  --selectors '{
    "title": "h1.property-title",
    "price": ".listing-price",
    "description": ".property-description",
    "features": {"selector": ".feature-item", "multiple": true},
    "images": {"selector": ".gallery img", "multiple": true, "attr": "src"},
    "agent": {
      "selector": ".agent-info",
      "fields": {
        "name": ".agent-name",
        "phone": ".agent-phone",
        "email": ".agent-email"
      }
    }
  }'
```

## Rate Limiting Example

When scraping multiple pages, add delays:

```bash
# Scrape multiple URLs with delay
for url in url1 url2 url3; do
  python3 scripts/scrape.py --url "$url" --mode structured --selectors '...'
  sleep 2  # 2 second delay between requests
done
```

## Proxy Usage

For sites with rate limiting or geo-restrictions:

```bash
python3 scripts/scrape.py \
  --url "https://property-site.com" \
  --proxy "http://proxy-server:8080" \
  --mode structured \
  --selectors '...'
```
