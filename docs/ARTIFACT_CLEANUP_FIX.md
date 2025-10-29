# Artifact Cleanup Fix

## Problem

The `backend/artifacts` directory was accumulating old build artifacts across multiple builds, instead of being cleaned up at the start of each build.

## Root Cause

1. The cleanup function used relative paths that could resolve incorrectly depending on the working directory
2. Error handling was too broad and could silently fail
3. Insufficient logging made it hard to debug when cleanup didn't work

## Solution

Updated the artifact cleanup mechanism with the following changes:

### 1. `backend/app/api/build.py`

- **Line 27**: Now uses `.resolve()` to get absolute path
- **Lines 29-44**: Added detailed logging to show cleanup progress
- **Lines 36-42**: Counts items before cleanup and skips if empty
- **Lines 47-57**: Better per-item error handling that raises exceptions
- **Lines 59-64**: Improved error reporting with full traceback

### 2. `backend/app/core/artifact_store.py`

- **Line 18**: Now uses `.resolve()` to get absolute path
- **Line 20**: Added logging to show which path is being used

## Testing

The fix was tested and verified:

- Created 3 test artifacts
- Ran cleanup function
- Confirmed all artifacts were removed
- Verified the function logs each step

## How It Works Now

Every time a build is started (via POST `/api/build`):

1. The cleanup function runs automatically at line 293 of `build.py`
2. It uses absolute paths to ensure it finds the correct artifacts directory
3. It logs exactly what it's doing (path, item count, each deletion)
4. If any error occurs, it prints a full traceback for debugging
5. Only proceeds with the build if cleanup succeeds

## Usage

No changes needed to how you run builds. Just use the existing API:

```bash
POST http://localhost:8000/api/build
{
  "place_id": "ChIJ..."
}
```

The cleanup happens automatically before each build.

## Verification

To verify the cleanup is working:

1. Start the backend server
2. Look for log messages like:
   ```
   [BUILD] Cleaning artifacts from: C:\DynamicBusinessLandingPage\backend\artifacts
   [BUILD] Found X items to clean
   [BUILD] Successfully cleaned up X items from artifacts directory
   ```
3. Check the artifacts directory - it should be empty after each build starts

## Files Changed

- `backend/app/api/build.py` - Updated `_cleanup_artifacts()` function
- `backend/app/core/artifact_store.py` - Updated path resolution
