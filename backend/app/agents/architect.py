"""Layout Architect agent - Product.md lines 250-397"""

from typing import Dict, Any
from app.agents.client import openai_client
import json


ARCHITECT_SYSTEM_PROMPT = """Design a section/component blueprint for a single-page informational landing page.
Inputs: business_name, category, design_source, data_richness, render_prefs.

Output: ordered sections with explicit component types, props, and visibility rules based on data availability.

Constraints:
- Single page.
- Avoid CTA-oriented components.
- Include empty-state and fallback rules.
- Include accessibility requirements (headings, alt text, focus styles)."""


# Response schema example for Architect
ARCHITECT_RESPONSE_EXAMPLE = {
    "sections": [
        {
            "id": "hero",
            "title": "Top",
            "components": [
                {
                    "type": "headline",
                    "props": {"level": "h1", "bind": "place.name"}
                },
                {
                    "type": "subheadline",
                    "props": {"text_from": ["category", "place.types"]}
                },
                {
                    "type": "metaRow",
                    "props": {
                        "fields": [
                            "rating",
                            "user_ratings_total",
                            "price_level",
                            "formatted_address"
                        ]
                    }
                }
            ],
            "visible_if": "true"
        },
        {
            "id": "gallery",
            "title": "Photos",
            "components": [
                {
                    "type": "imageGrid",
                    "props": {"bind": "photos", "max": 8, "lazy": True}
                }
            ],
            "visible_if": "has_photos"
        },
        {
            "id": "about",
            "title": "About",
            "components": [
                {
                    "type": "keyValueList",
                    "props": {
                        "items": [
                            {"label": "Address", "bind": "place.formatted_address"},
                            {"label": "Website", "bind": "place.website"},
                            {"label": "Phone", "bind": "place.formatted_phone_number"},
                            {"label": "Hours", "bind": "place.opening_hours.weekday_text"}
                        ],
                        "linkify": ["place.website"]
                    }
                }
            ],
            "visible_if": "true"
        },
        {
            "id": "reviews",
            "title": "Reviews",
            "components": [
                {
                    "type": "reviewList",
                    "props": {"bind": "reviews", "max": 6, "avatar": True}
                }
            ],
            "visible_if": "has_reviews"
        },
        {
            "id": "credits",
            "title": "Attributions",
            "components": [
                {
                    "type": "attributionList",
                    "props": {"bind": "photos.attributions"}
                }
            ],
            "visible_if": "has_photos"
        },
        {
            "id": "map",
            "title": "Location",
            "components": [
                {
                    "type": "staticMapPlaceholder",
                    "props": {"bind": "place.geometry"}
                }
            ],
            "visible_if": "true"
        }
    ],
    "empty_state_rules": [
        "Hide section if data_richness flag is false",
        "If no photos: render a 3-col color block with business initials"
    ],
    "a11y_notes": [
        "Single H1 in hero",
        "Alt text for every image",
        "Sufficient color contrast for text/background",
        "Keyboard-focus outlines on interactive items"
    ]
}


async def create_layout_plan(
    business_name: str,
    category: str,
    design_source: Dict[str, Any],
    data_richness: Dict[str, bool],
    render_prefs: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Create section/component blueprint for the landing page.
    
    Input from Orchestrator:
    {
      "business_name": "string",
      "category": "string",
      "design_source": {
        "name": "string",
        "url": "string",
        "style_keywords": ["string"]
      },
      "data_richness": {
        "has_photos": true,
        "has_reviews": true,
        "has_hours": true,
        "has_site": true
      },
      "render_prefs": {
        "language": "en",
        "direction": "ltr"
      }
    }
    
    Output: See ARCHITECT_RESPONSE_EXAMPLE
    """
    user_message = {
        "business_name": business_name,
        "category": category,
        "design_source": design_source,
        "data_richness": data_richness,
        "render_prefs": render_prefs
    }
    
    try:
        result = await openai_client.call_agent(
            system_prompt=ARCHITECT_SYSTEM_PROMPT,
            user_message=user_message,
            model="gpt-4o",
            temperature=0.7,
            response_format={"type": "json_object"}
        )
        return result
        
    except Exception as e:
        # Return default layout plan
        return ARCHITECT_RESPONSE_EXAMPLE

