# Stock Image API Migration Summary

## What Changed

Replaced **hardcoded stock image URLs** with **dynamic Unsplash API integration** for fetching relevant stock images.

---

## Before (Hardcoded)

```python
CATEGORY_STOCK = {
    "pizza_restaurant": [
        "https://images.unsplash.com/photo-1542831371-29b0f74f9713...",
        "https://images.pexels.com/photos/2619967/..."
    ],
    "restaurant": [...],
    "supermarket": [...],
    # ... 20+ categories
}

def pick_assets(place_types, images):
    if images:
        return images
    for place_type in place_types:
        if place_type in CATEGORY_STOCK:
            return CATEGORY_STOCK[place_type]
    return CATEGORY_STOCK["default"]
```

**Problems:**
- ❌ Static list of categories
- ❌ Same images for every business of the same type
- ❌ Manual curation required
- ❌ Limited to pre-defined categories

---

## After (Dynamic API)

```python
async def fetch_stock_images(query: str, count: int = 3) -> List[str]:
    """Fetch relevant stock images from Unsplash API"""
    if not UNSPLASH_ACCESS_KEY:
        return EMERGENCY_FALLBACK[:count]
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        params = {
            "query": query,
            "per_page": count,
            "orientation": "landscape",
            "client_id": UNSPLASH_ACCESS_KEY
        }
        response = await client.get(UNSPLASH_API_URL, params=params)
        data = response.json()
        results = data.get("results", [])
        
        image_urls = [
            photo["urls"]["regular"] + "&w=1600&q=80&auto=format"
            for photo in results[:count]
        ]
        
        return image_urls if image_urls else EMERGENCY_FALLBACK[:count]

def build_search_query(place_types: List[str], business_name: str = "") -> str:
    """Map business types to effective search queries"""
    type_mapping = {
        "pizza_restaurant": "pizza restaurant interior",
        "meal_delivery": "food delivery",
        "restaurant": "restaurant interior",
        # ... 15+ optimized mappings
    }
    
    for place_type in place_types:
        if place_type in type_mapping:
            return type_mapping[place_type]
    
    return place_types[0].replace("_", " ")
```

**Benefits:**
- ✅ Dynamic, relevant images for each business
- ✅ Covers all business types (not just pre-defined)
- ✅ Variety: different images each time
- ✅ Search-optimized queries for better results
- ✅ Graceful fallback if API fails
- ✅ No manual curation needed

---

## How It Works

1. **Business images available?**
   - YES → Use business images
   - NO → Continue to step 2

2. **Build search query**
   - Map business type (e.g., `"pizza_restaurant"`) to search term (e.g., `"pizza restaurant interior"`)
   - Or use raw place type if no mapping exists

3. **Fetch from Unsplash**
   - Call Unsplash Search API with query
   - Request 3 landscape-oriented images
   - Return high-res URLs (1600px width)

4. **Fallback if needed**
   - If API fails or no key provided → Use 2 emergency fallback images
   - If no results for query → Use emergency fallback

---

## Files Modified

### Agents Service

1. **`agents/app/generator/generator_agent.py`**
   - Added `fetch_stock_images()` function
   - Added `build_search_query()` function
   - Removed `CATEGORY_STOCK` dictionary
   - Removed `pick_assets()` function
   - Made `_enhance_with_stock_images()` async
   - Updated `run()` to await `_enhance_with_stock_images()`

### Simple OpenAI Server

2. **`simple_openai_server/simple_agent.py`**
   - Added `fetch_stock_images()` function
   - Added `build_search_query()` function
   - Removed `CATEGORY_STOCK` dictionary
   - Removed `pick_assets()` function
   - Made `_enhance_with_stock_images()` async
   - Updated `build_index_html()` to await `_enhance_with_stock_images()`

### Dependencies

3. **`simple_openai_server/requirements.txt`**
   - Added `httpx==0.25.2`

4. **`agents/requirements.txt`**
   - No change (already had `httpx`)

### Documentation

5. **`UNSPLASH_SETUP.md`** (NEW)
   - Complete guide for getting Unsplash API key
   - Step-by-step instructions
   - Troubleshooting tips

6. **`STOCK_IMAGE_API_MIGRATION.md`** (NEW - this file)
   - Migration summary
   - Before/after comparison

---

## Environment Variables

Add to `.env` files:

```env
# Unsplash API for stock image fallback
UNSPLASH_ACCESS_KEY=your_access_key_here
```

**Locations:**
- `agents/.env`
- `simple_openai_server/.env` (or project root `.env`)

---

## API Limits

### Free Tier (Demo)
- **50 requests/hour**
- No approval needed
- Sufficient for development and testing

### Production Tier
- **5,000 requests/hour**
- Requires application review
- Apply at: [unsplash.com/oauth/applications](https://unsplash.com/oauth/applications)

---

## Testing

### Test Simple Server

```bash
cd simple_openai_server
python run_example.py
```

**Expected output:**
```
[*] Mapped 'pizza_restaurant' to 'pizza restaurant interior'
[*] Searching Unsplash for 'pizza restaurant interior' (count=3)
[OK] Found 3 images for 'pizza restaurant interior'
   Using 0 business + 3 stock images
```

### Test Agents

```bash
cd agents
python test_build_no_mcp.py
```

**Expected output:**
```
[Generator] Fetching stock images for query: 'pizza restaurant interior'
[Generator] Using 0 business + 3 stock images
```

---

## Fallback Strategy

### Priority Order:

1. **Business images** (if ≥2 HTTPS images available)
2. **Unsplash API** (dynamic search based on business type)
3. **Emergency fallback** (2 generic images if API fails)

### Emergency Fallback Images:

```python
EMERGENCY_FALLBACK = [
    "https://images.unsplash.com/photo-1556742049-0cfed4f6a45d?q=80&w=1600&auto=format",
    "https://images.unsplash.com/photo-1517248135467-4c7edcad34c4?q=80&w=1600&auto=format"
]
```

These are high-quality, generic business-related images that work for any business type.

---

## Search Query Mapping

The `build_search_query()` function maps Google Place types to effective Unsplash search terms:

| Place Type | Search Query |
|------------|--------------|
| `pizza_restaurant` | "pizza restaurant interior" |
| `meal_delivery` | "food delivery" |
| `restaurant` | "restaurant interior" |
| `supermarket` | "grocery store" |
| `cafe` | "coffee shop cafe" |
| `bakery` | "bakery pastries" |
| `bar` | "bar interior" |
| `clothing_store` | "clothing boutique" |
| `gym` | "fitness gym" |
| `hair_care` | "hair salon" |
| `spa` | "spa wellness" |
| *(any other)* | *(cleaned place_type)* |

You can customize this mapping by editing the `type_mapping` dictionary.

---

## Benefits Summary

### For Users
- ✅ More relevant images for their specific business
- ✅ Fresh, varied visuals (not the same stock images)
- ✅ Better first impression with high-quality photos

### For Developers
- ✅ No need to curate stock image lists
- ✅ Automatic support for new business types
- ✅ Easy to customize search queries
- ✅ Graceful fallback if API unavailable

### For Maintenance
- ✅ No hardcoded URLs to maintain
- ✅ No broken image links over time
- ✅ Dynamic adaptation to business types

---

## Migration Checklist

- [x] Remove `CATEGORY_STOCK` dictionary
- [x] Remove `pick_assets()` function
- [x] Add `fetch_stock_images()` async function
- [x] Add `build_search_query()` function
- [x] Make `_enhance_with_stock_images()` async
- [x] Add `await` for async calls
- [x] Add `httpx` dependency
- [x] Update `.env` with `UNSPLASH_ACCESS_KEY`
- [x] Test simple server
- [x] Test agents service
- [x] Document setup process
- [x] Test fallback behavior

---

## Rollback (if needed)

If you need to rollback to hardcoded images:

1. Remove the Unsplash API code
2. Restore the `CATEGORY_STOCK` dictionary
3. Restore the `pick_assets()` function
4. Make `_enhance_with_stock_images()` synchronous
5. Remove `await` calls

(Alternatively, just don't set `UNSPLASH_ACCESS_KEY` and it will use emergency fallback.)

---

## Next Steps

1. ✅ Get Unsplash API key → [See UNSPLASH_SETUP.md](./UNSPLASH_SETUP.md)
2. ✅ Add to `.env` files
3. ✅ Install dependencies: `pip install -r requirements.txt`
4. ✅ Test with example scripts
5. ⏳ Monitor API usage
6. ⏳ Consider caching for production
7. ⏳ Apply for Production tier if needed (5K requests/hour)

---

## Support

- **Unsplash API Docs**: [https://unsplash.com/documentation](https://unsplash.com/documentation)
- **Rate Limits**: [https://unsplash.com/documentation#rate-limiting](https://unsplash.com/documentation#rate-limiting)
- **API Guidelines**: [https://help.unsplash.com/en/articles/2511245-unsplash-api-guidelines](https://help.unsplash.com/en/articles/2511245-unsplash-api-guidelines)

---

**Migration completed successfully!** 🎉

Dynamic stock image fetching is now live. Images are fetched in real-time based on business type, providing relevant, high-quality visuals for every landing page.

