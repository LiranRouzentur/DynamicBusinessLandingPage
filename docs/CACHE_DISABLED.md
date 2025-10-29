# Cache Disabled for Local Development

All caching logic has been removed from the entire project for local development.

## Changes Made

### 1. Backend Service - Build Endpoint (`backend/app/api/build.py`)

**Before:** System checked cache and reused cached builds  
**After:** Every build runs fresh from scratch

**Changes:**

- ✅ Cache import commented out
- ✅ Cache check removed (no cache lookup)
- ✅ Cache saving removed (no cache storage after build)
- ✅ Updated docstring to reflect new behavior

### 2. Build Flow

**New Flow (Simplified):**

```
1. POST /api/build with place_id
2. Clean up old artifacts
3. Generate new session_id
4. Fetch from Google Places API
5. Run AI agents (Designer → Mapper → Generator → QA)
6. Save artifacts
7. Return session_id
```

**No More:**

- ❌ Cache lookups
- ❌ Cache storage
- ❌ Returning cached session_ids

## Benefits

✅ **Fresh builds every time** - No stale data
✅ **Simpler code flow** - Easier to debug
✅ **Clean artifacts** - Old builds automatically removed
✅ **True development environment** - See changes immediately

## Summary by Service

### Backend Service

- ✅ Cache import commented out
- ✅ Cache check removed
- ✅ Cache saving removed
- ✅ BuildResponse always returns `cached=False`
- ✅ Config updated to document cache is disabled

### Agents Service

- ✅ No caching logic exists (already cache-free)
- ✅ Each request triggers a fresh AI agent workflow

## Enabling Cache in Production

To enable caching in production, uncomment the cache logic in `backend/app/api/build.py`:

1. Uncomment the import:

   ```python
   from app.core.cache import cache_manager
   ```

2. Uncomment the cache check in `start_build()`:

   ```python
   cached_data = cache_manager.get(request.place_id)
   if cached_data:
       session_id = cached_data.get("session_id", str(uuid.uuid4()))
       return BuildResponse(session_id=session_id, cached=True)
   ```

3. Uncomment the cache save in `_run_build()`:
   ```python
   cache_manager.set(
       place_id=place_id,
       data={"session_id": session_id, "bundle": bundle},
       payload_hash=None
   )
   ```

## Testing

To verify caching is disabled:

1. Run a build
2. Run the same build again (same place_id)
3. You should see "Cleanup artifacts directory" message
4. A completely new build should run (not returned from cache)
