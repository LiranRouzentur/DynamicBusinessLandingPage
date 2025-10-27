# Build Process Debugging - Comprehensive Analysis

## Problem Analysis

Based on your logs, the issue is:

1. ✅ Business selection works
2. ✅ API call succeeds (202 response)
3. ✅ Session created
4. ❌ SSE connects but gets error immediately
5. ❌ Build gets stuck on "Fetching place details from Google Maps"
6. ❌ After 20 minutes, error: "Build failed: 'index_html'"

## Root Causes Identified

### 1. SSE Progress Streaming Not Sending Updates

**Problem**: The progress endpoint only sends events when state changes, but state is updated inside an async background task that may not be running or is failing silently.

**Evidence**:

- SSE connects but shows error
- No progress updates in the left panel
- Build shows "Fetching..." forever

### 2. Build Process Likely Failing at Google API Call

**Problem**: The `google_fetcher.fetch_place()` call is likely:

- Blocking or timing out
- Not being properly awaited
- Failing with an exception that's being swallowed

**Evidence**:

- Build sticks at "Fetching place details"
- Eventually fails with 'index_html' error (trying to access result that doesn't exist)

## Fixes Applied

### 1. Enhanced SSE Progress Streaming (`backend/app/api/progress.py`)

```python
# Added initial state send
initial_event = ProgressEvent(...)
yield f"data: {initial_event.model_dump_json()}\n\n"

# Added phase change detection
if (state.progress != last_progress or
    state.current_step != last_step or
    state.phase != last_phase):
```

**Why**: SSE now sends an initial event immediately and tracks phase changes, not just progress/step.

### 2. Comprehensive Logging (`backend/app/api/build.py`)

```python
print(f"[BUILD] Build started for session {session_id}")
print(f"[BUILD] Session {session_id}: Calling google_fetcher.fetch_place({place_id})...")
print(f"[BUILD] Session {session_id}: google_fetcher returned successfully")
```

**Why**: Every step of the build process is now logged with `[BUILD]` prefix for easy tracking.

### 3. Detailed Google Fetcher Logging (`backend/app/core/google_fetcher.py`)

```python
print(f"[FETCHER] Starting fetch_place for place_id: {place_id}")
print(f"[FETCHER] Calling _fetch_place_details...")
print(f"[FETCHER] _fetch_place_details returned")
print(f"[FETCHER] Extracted {len(photos)} photos")
print(f"[FETCHER] Extracted {len(reviews)} reviews")
```

**Why**: Track exactly where the Google API call is failing or getting stuck.

## What to Check Now

### 1. Watch Backend Logs

When you start a build, you should see:

```
[BUILD] Build started for session abc-123, place ChIJ...
[BUILD] Session abc-123: Transitioning to FETCHING
[BUILD] State updated: phase=FETCHING, progress=0.05
[BUILD] Session abc-123: Calling google_fetcher.fetch_place...
[FETCHER] Starting fetch_place for place_id: ChIJ...
[FETCHER] Calling _fetch_place_details...
[FETCHER] _fetch_place_details returned
[FETCHER] Extracted X photos
[FETCHER] Extracted Y reviews
[BUILD] Session abc-123: google_fetcher returned successfully
```

### 2. Check Where It Stops

If it stops at any of these points, that's where the issue is:

- Stops before `[BUILD]` → Background task not starting
- Stops at `[FETCHER] Calling _fetch_place_details...` → Google API blocking
- Stops at `[FETCHER] _fetch_place_details returned` → Photo/review extraction failing
- Shows error at any point → Error handling issue

### 3. Common Issues to Look For

**A. Google API Key Issue**

- Check if API key is valid
- Check if Places API is enabled
- Check console for "INVALID_REQUEST" or "NOT_FOUND"

**B. Google API Rate Limits**

- Too many requests
- Check for "GOOGLE_RATE_LIMIT" errors

**C. Async/Await Issue**

- `asyncio.to_thread()` might be blocking
- Could be waiting for result that never comes

**D. State Not Being Updated**

- State updates happen but SSE doesn't poll fast enough
- State gets stuck in one phase

## Next Steps

1. **Restart the backend** to load new logging code
2. **Start a new build** and watch both:
   - Browser console (frontend logs)
   - Backend terminal (server logs)
3. **Find where the log stops** - that's your error point
4. **Share the last log line** - I can fix the specific issue

## Expected Flow (Working)

```
Frontend: Select business
↓
[BUILD] Build started...
↓
[BUILD] Transitioning to FETCHING
↓
[FETCHER] Starting fetch_place...
↓
[FETCHER] _fetch_place_details returned
↓
[BUILD] google_fetcher returned successfully
↓
[BUILD] Transitioning to ORCHESTRATING
↓
[BUILD] Running orchestrator...
↓
[BUILD] Orchestrator completed
↓
[BUILD] Transitioning to GENERATING
↓
[BUILD] Transitioning to QA
↓
[BUILD] Transitioning to READY
↓
Frontend: Landing page displays
```

## SSE Progress Updates

With the new code, you should see progress in the left panel:

- "Connecting to Google Places API..." (progress: 5%)
- "Fetched X photos and Y reviews" (progress: 15%)
- "Preparing AI orchestration..." (progress: 20%)
- "Initializing AI workflow..." (progress: 25%)
- "Selecting design template..." (progress: 30%)
- ... (continues through all phases)

If you still only see "Fetching..." then the SSE isn't receiving events.
