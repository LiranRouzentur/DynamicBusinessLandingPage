# Stock Images Fallback Feature

## Overview

Added stock image fallback functionality to the AI agents system. When no photos are available for a landing page (e.g., a supermarket with no Google Maps photos), the system now automatically suggests relevant stock images based on the business category.

## Changes Made

### 1. Mapper Agent Schema (`ai/app/agents/mapper/mapper_schemas.py`)

- **Added `StockImageSuggestion` model** with fields:

  - `search_query`: The search query used to find stock images
  - `suggested_urls`: List of stock image URLs (uses Unsplash format)
  - `alt_text`: Descriptive alt text for accessibility
  - `usage_note`: Note indicating these are stock images

- **Updated `MapperOutput` model** to include:

  - `stock_image_suggestions`: List of stock image suggestions (empty when photos are available)

- **Updated `MAPPER_RESPONSE_SCHEMA`** to include the new field structure for OpenAI structured output

### 2. Mapper Agent Prompt (`ai/app/agents/mapper/mapper_prompt.py`)

Added detailed instructions for stock image fallback:

- When no photos are available, AI must analyze business category/types
- Generate 3-5 relevant stock image URLs using Unsplash API format
- Provide descriptive alt text
- Include usage notes

Example: For a supermarket without photos, the AI will suggest:

- URLs like `https://source.unsplash.com/800x600/?supermarket,interior`
- Alt text: "Modern grocery store interior with fresh produce section"
- Usage note: "Stock images used as fallback when no business photos available"

### 3. Generator Agent Prompt (`ai/app/agents/generator/generator_prompt.py`)

Added handling instructions for stock images:

- Use stock images from `content_map.stock_image_suggestions` when no photos available
- Render in same gallery/image sections as regular photos
- Use provided alt_text for accessibility
- Add subtle attribution if available
- Ensure lazy-loading works for both regular and stock images

### 4. Mapper Agent Implementation (`ai/app/agents/mapper/mapper_agent.py`)

- Updated error handler to include `stock_image_suggestions: []` in fallback response

## How It Works

### Data Flow

1. **Backend** fetches place data from Google Maps API
2. **Mapper Agent** receives place_data and checks if photos array is empty
3. **If no photos**: Mapper generates toggle_image_suggestions based on business category
4. **Generator Agent** receives content_map (including stock_image_suggestions)
5. **Generator** uses stock images in gallery sections when photos are missing
6. **Final HTML** displays either real photos or stock images with proper alt text

### Example Use Case

When building a landing page for a supermarket with no Google Maps photos:

1. Mapper detects empty photos array
2. Analyzes business category: "supermarket", "grocery store"
3. Generates stock image suggestions:
   - `https://source.unsplash.com/800x600/?supermarket,interior`
   - `https://source.unsplash.com/800x600/?grocery,produce`
   - `https://source.unsplash.com/800x600/?grocery,cart`
4. Generator renders these as gallery images
5. User sees relevant supermarket imagery instead of empty space

## Benefits

- **Better UX**: No empty image sections on landing pages
- **Relevant imagery**: AI selects contextually appropriate stock photos
- **Accessibility**: Proper alt text for all images
- **Flexibility**: Works for any business category (restaurants, retail, services, etc.)
- **Seamless**: Users cannot distinguish between real and stock images in terms of quality

## Technical Notes

- Uses Unsplash API for stock images (free, high-quality)
- Stock images are lazy-loaded like regular photos
- Attribution can be added via usage_note field
- No additional external dependencies required
- Backward compatible: When photos exist, stock_image_suggestions is empty
