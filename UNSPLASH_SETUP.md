# Unsplash API Setup Guide

The stock image fallback feature uses the **Unsplash API** to dynamically fetch relevant images based on the business type. This guide will help you set up your free Unsplash API key.

## Why Unsplash?

- ✅ **Free Tier**: 50 requests/hour (sufficient for testing and small-scale use)
- ✅ **High-Quality Images**: Professional stock photos
- ✅ **Search API**: Find relevant images by keyword
- ✅ **No Attribution Required**: For demo/development (see Unsplash Guidelines for production)

---

## Step 1: Create an Unsplash Account

1. Go to [https://unsplash.com/join](https://unsplash.com/join)
2. Sign up with your email or use GitHub/Google OAuth
3. Verify your email address

---

## Step 2: Register as a Developer

1. Go to [https://unsplash.com/developers](https://unsplash.com/developers)
2. Click **"Register as a developer"**
3. Accept the API Terms and Conditions

---

## Step 3: Create a New Application

1. Go to [https://unsplash.com/oauth/applications](https://unsplash.com/oauth/applications)
2. Click **"New Application"**
3. Fill in the application details:
   - **Application name**: "Dynamic Business Landing Page" (or your preferred name)
   - **Description**: "Generates landing pages with dynamic stock images"
   - **Check all required checkboxes** (Guidelines acknowledgment, etc.)
4. Click **"Create Application"**

---

## Step 4: Get Your Access Key

1. Once created, you'll see your application dashboard
2. Scroll to the **"Keys"** section
3. Copy your **Access Key** (not the Secret Key)
   - It will look like: `abc123xyz456...` (long alphanumeric string)

---

## Step 5: Add to Environment Variables

### For the Agents Service

Add to `agents/.env`:

```env
# Unsplash API for stock image fallback
UNSPLASH_ACCESS_KEY=your_access_key_here
```

### For the Simple OpenAI Server

Add to `simple_openai_server/.env` (or project root `.env`):

```env
# Unsplash API for stock image fallback
UNSPLASH_ACCESS_KEY=your_access_key_here
```

### Example `.env` File

```env
# OpenAI Configuration
OPENAI_API_KEY=sk-...your_openai_key...

# Unsplash Configuration
UNSPLASH_ACCESS_KEY=abc123xyz456...your_unsplash_key...

# Backend URL (optional)
BACKEND_URL=http://localhost:8000
```

---

## Step 6: Test the Integration

### Test with Simple Server

```bash
cd simple_openai_server
python run_example.py
```

You should see logs like:
```
[*] Mapped 'pizza_restaurant' to 'pizza restaurant interior'
[*] Searching Unsplash for 'pizza restaurant interior' (count=3)
[OK] Found 3 images for 'pizza restaurant interior'
```

### Test with Agents

```bash
cd agents
python test_build_no_mcp.py
```

Look for logs:
```
[Generator] Fetching stock images for query: 'pizza restaurant interior'
[Generator] Using 0 business + 3 stock images
```

---

## Rate Limits

### Demo (Development) - Default

- **50 requests/hour**
- Sufficient for testing and development
- No additional approval needed

### Production (if needed)

- **5,000 requests/hour**
- Requires submitting your application for review
- Go to your app dashboard → **"Apply for Production"**
- Provide details about your use case

---

## Fallback Behavior

If the Unsplash API is unavailable or you don't provide an API key:

1. **Emergency Fallback**: The system uses 2 hardcoded generic business images
2. **No Crashes**: The generator continues with these fallback images
3. **Logs Warning**: `"No UNSPLASH_ACCESS_KEY found, using emergency fallback"`

---

## API Usage Best Practices

1. **Cache Images**: In production, consider caching fetched image URLs by business type
2. **Monitor Rate Limits**: Log API usage to avoid hitting limits
3. **Upgrade if Needed**: If you exceed 50 req/hour, apply for Production access
4. **Attribution** (Production): Follow Unsplash Guidelines for crediting photographers

---

## Troubleshooting

### Error: "No UNSPLASH_ACCESS_KEY found"

**Solution**: Make sure your `.env` file is in the correct location and the key name is exact:
```env
UNSPLASH_ACCESS_KEY=your_key_here
```

### Error: "401 Unauthorized"

**Solution**: Your Access Key might be invalid. Generate a new one from your Unsplash app dashboard.

### Error: "403 Rate Limit Exceeded"

**Solution**: You've hit the 50 requests/hour limit. Wait an hour or apply for Production access.

### No Results for Search Query

**Solution**: The system automatically falls back to emergency images. Check the business type mapping in:
- `agents/app/generator/generator_agent.py` → `build_search_query()`
- `simple_openai_server/simple_agent.py` → `build_search_query()`

You can customize the `type_mapping` dictionary to improve search relevance.

---

## Alternative: Use Emergency Fallback Only

If you don't want to use the Unsplash API, the system will automatically use the emergency fallback images. These are 2 generic high-quality images that work for any business type.

Simply **don't set** the `UNSPLASH_ACCESS_KEY` environment variable.

---

## Summary

1. Create Unsplash account → [unsplash.com/join](https://unsplash.com/join)
2. Register as developer → [unsplash.com/developers](https://unsplash.com/developers)
3. Create new application → [unsplash.com/oauth/applications](https://unsplash.com/oauth/applications)
4. Copy Access Key
5. Add to `.env` file:
   ```env
   UNSPLASH_ACCESS_KEY=your_access_key_here
   ```
6. Test with `run_example.py` or `test_build_no_mcp.py`

**Free tier limit**: 50 requests/hour ✅

Done! Your stock image fallback is now dynamic and relevant to each business type. 🎉

