# Debugging Guide - Business Selection Not Starting

## Changes Made

### 1. Fixed SearchBox.tsx

- **Issue**: Listener cleanup code was broken
- **Fix**: Removed incorrect listener cleanup, added debug logs
- **Location**: `client/src/components/LeftPanel/SearchBox.tsx`

### 2. Added Debug Logging

Added comprehensive console logging at every step:

- Google Maps initialization status
- Place selection event firing
- Place ID extraction
- API request payload
- Session creation

### 3. Added Validation

- Check for empty/undefined place_id before making API call
- Alert user if place_id is missing

## Expected Flow When Working

### Step 1: User types in search box

```
Console should show:
- "Place selected:" (with place object)
- "Place ID:" (the actual place_id)
```

### Step 2: API request is made

```
Console should show:
- "Business selected, starting build process for place: [place_id]"
- "Sending POST to /api/build with payload: {place_id: '...'}"
```

### Step 3: Backend processes request

```
Backend console should show:
- "Build started for session [session_id], place [place_id]"
- "Session [session_id]: Transitioning to FETCHING"
```

### Step 4: Frontend receives response

```
Console should show:
- "Build session started: {session_id: '...', cached: false}"
- "Session ID received: [session_id]"
```

## How to Debug

### 1. Open Browser Console

- Press `F12` or right-click → Inspect
- Go to Console tab

### 2. Test the Search

1. Type in the search box
2. Select a business from the dropdown
3. Watch the console for the logs above

### 3. Check Backend Logs

The backend terminal should show build progress logs.

### 4. Common Issues

#### Issue: "Place selected:" but no "Place ID:"

**Problem**: The place object doesn't have a `place_id` property
**Solution**: The Google Maps API key might not have Places API enabled

#### Issue: No "gmp-placeselect event fired"

**Problem**: The autocomplete isn't properly initialized
**Check**:

- Look for "Error initializing Autocomplete:" in console
- Check if Google Maps API key is configured

#### Issue: API request fails

**Problem**: Backend not running or CORS issue
**Solution**:

- Check backend is running: `curl http://localhost:8000/health`
- Should return `{"status":"healthy"}`

## Environment Check

### Backend Environment

```bash
cd backend
# Check .env exists and has:
GOOGLE_MAPS_API_KEY=...
OPENAI_API_KEY=...
```

### Frontend Environment

```bash
cd client
# Check .env.local exists and has:
VITE_GOOGLE_MAPS_API_KEY=...
```

## Next Steps

1. **Refresh the browser** to load the new debug code
2. **Open browser console** (F12)
3. **Try selecting a business** and watch the console
4. **Share the console output** if issue persists

The debug logs will show exactly where the process is failing.
