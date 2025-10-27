"""Design-Source Selector agent - Product.md lines 195-248"""

from typing import Dict, Any
from app.agents.client import openai_client
import json


SELECTOR_SYSTEM_PROMPT = """You select a reference design source (template/theme) for a single informational landing page.
Input: business_name, category, render_prefs, data_richness.
Output: 1 design source that best fits tone and category, with rationale and style keywords.

Rules:
- Must suit a data-display page (no CTA emphasis).
- Favor clean, content-first layouts (good typography, card/grid sections).
- Provide license/usage note.
- Assume the final page will be custom-built; your source is inspiration and structure guidance.
- No external dependency is required from the chosen source; it's a reference."""


# Response schema for Selector
SELECTOR_RESPONSE_SCHEMA = {
    "name": "string",
    "url": "string",
    "style_keywords": ["string"],
    "layout_notes": ["string"],
    "license_note": "string"
}


async def select_design_source(
    business_name: str,
    category: str,
    render_prefs: Dict[str, Any],
    data_richness: Dict[str, bool]
) -> Dict[str, Any]:
    """
    Select a reference design source for the business category.
    
    Input schema (from Orchestrator):
    {
      "business_name": "string",
      "category": "string",
      "render_prefs": {
        "language": "en",
        "direction": "ltr",
        "brand_colors": { "primary": "#0f766e", "accent": "#22d3ee" },
        "font_stack": "system-ui",
        "allow_external_cdns": false
      },
      "data_richness": {
        "has_photos": true,
        "has_reviews": true,
        "has_hours": true,
        "has_site": true
      }
    }
    
    Output schema:
    {
      "name": "UIdeck - Solid Content",
      "url": "https://example.com/template",
      "style_keywords": ["content-first", "grid", "cards", "accessible", "neutral"],
      "layout_notes": [
        "Hero with name + category",
        "Responsive grid for photos",
        "Readable reviews section with avatars"
      ],
      "license_note": "Free for personal/commercial with attribution (verify)"
    }
    """
    user_message = {
        "business_name": business_name,
        "category": category,
        "render_prefs": render_prefs,
        "data_richness": data_richness
    }
    
    try:
        result = await openai_client.call_agent(
            system_prompt=SELECTOR_SYSTEM_PROMPT,
            user_message=user_message,
            model="gpt-4o",
            temperature=0.7,
            response_format={"type": "json_object"}
        )
        return result
        
    except Exception as e:
        # Fallback design source
        return {
            "name": "Minimal Content Layout",
            "url": "https://example.com/template",
            "style_keywords": ["content-first", "minimal", "accessible"],
            "layout_notes": [
                "Simple hero section",
                "Content-focused layout",
                "Clean typography"
            ],
            "license_note": "Template-based design"
        }

