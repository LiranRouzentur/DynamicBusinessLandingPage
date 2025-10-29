# Image Assets Implementation Summary

## Overview

Implemented image download and asset folder support per `asset-aware-mode.md` and `asset-limitation-policy.md` specifications. The system now downloads images from Google Places API and stock image suggestions, stores them in an `assets/images/` folder, and serves them with proper caching.

## Changes Made

### 1. Generator Agent Schema (`ai/app/agents/generator/generator_schemas.py`)

- Added `ImageAsset` model with fields: filename, media_type, base64, alt, source_url, attribution_html
- Added `GeneratorAssets` model to hold collections of assets
- Updated `GeneratorOutput` to include optional `assets` field
- Updated schema to reflect assets structure

### 2. Generator Agent Implementation (`ai/app/agents/generator/generator_agent.py`)

- Added `_fetch_image()` method to download images using aiohttp
- Added `_download_images()` method to:
  - Extract images from content_map sections
  - Extract stock image suggestions
  - Download both types of images and convert to base64
- Updated `run()` method to:
  - Download images before generating HTML
  - Include image metadata in user message
  - Attach assets to the result
- Images are downloaded asynchronously and converted to base64 before being passed to the AI

### 3. Generator Prompt (`ai/app/agents/generator/generator_prompt.py`)

- Added IMAGE ASSET HANDLING instructions
- Specifies that images should be referenced using relative paths like `assets/images/photo_0.webp`
- Requires loading="lazy" and descriptive alt text
- Added ASSET SIZE CONSTRAINTS as critical requirements

### 4. Artifact Store (`backend/app/core/artifact_store.py`)

- Updated `save_bundle()` to accept optional `assets` parameter
- Added logic to:
  - Create `assets/images/` directory structure
  - Decode base64 images and write to disk
  - Handle errors gracefully with logging
- Images are saved as binary files under `artifacts/{session_id}/assets/images/`

### 5. Build API (`backend/app/api/build.py`)

- Updated to extract assets from bundle
- Passes assets to artifact_store when saving

### 6. Result API (`backend/app/api/result.py`)

- Updated asset path handling for CSS/JS files
- Uses `/assets/{session_id}/` for external asset references

### 7. Main App (`backend/app/main.py`)

- Added `/assets/{session_id}/{file_path:path}` route to serve assets
- Includes security check to prevent path traversal
- Sets appropriate media types for different file extensions
- Configures caching headers:
  - Images: 1 year immutable cache
  - Other assets: 1 hour cache

### 8. Requirements (`ai/requirements.txt`)

- Added `aiohttp==3.9.1` for async HTTP client

## File Structure

After generation, artifacts are saved as:

```
artifacts/
  └─ {session_id}/
      ├─ index.html
      ├─ styles.css
      ├─ app.js
      └─ assets/
          └─ images/
              ├─ photo_0.webp
              ├─ photo_1.webp
              ├─ stock_0_0.webp
              └─ ...
```

## API Routes

1. **GET /api/result/{session_id}** - Returns HTML with inlined or linked CSS/JS
2. **GET /assets/{session_id}/styles.css** - Returns CSS file
3. **GET /assets/{session_id}/app.js** - Returns JS file
4. **GET /assets/{session_id}/assets/images/{filename}** - Returns image files

## Asset Size Limits (Enforced by QA)

- HTML: ≤ 150 KB
- CSS: ≤ 50 KB
- JS: ≤ 80 KB
- Total HTML+CSS+JS: ≤ 250 KB
- Single image: ≤ 150 KB
- Gallery total: ≤ 800 KB
- All assets including images: ≤ 1 MB total

## Security Features

- Path traversal protection in asset serving route
- Session isolation (each build has its own folder)
- Safe base64 decoding with error handling
- Sanitized file paths

## Next Steps

1. Install dependencies: `pip install -r ai/requirements.txt`
2. Test the image download with a business that has photos
3. Verify that images appear correctly in the generated HTML
4. Monitor asset sizes to ensure compliance with limits
5. Consider adding image optimization/compression if needed

## Testing

To test the implementation:

1. Run the backend: `python -m backend.app.main`
2. Trigger a build for a business with photos
3. Check that images are downloaded and saved in `artifacts/{session_id}/assets/images/`
4. Verify that the HTML references images with correct paths
5. Confirm that images load when viewing the result
