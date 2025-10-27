"""Content Mapper agent - Product.md lines 399-516"""

from typing import Dict, Any
from app.agents.client import openai_client
from app.utils.sanitization import sanitize_html, escape_html
import json


MAPPER_SYSTEM_PROMPT = """Bind real data into the layout plan. Sanitize and format for safe HTML output.
Select up to render_prefs.max_reviews reviews, filter by language, drop profanity, trim long texts with "Read more" expansion handled by app.js (no external code).

Also: derive alt text for photos. Preserve attribution HTML safely in a dedicated credits section (rendered as sanitized allowed tags: <a>, <span>)."""


async def map_content(
    layout_plan: Dict[str, Any],
    place_payload: Dict[str, Any],
    render_prefs: Dict[str, Any] = None
) -> Dict[str, Any]:
  
    # Set default render_prefs
    if render_prefs is None:
        render_prefs = {"max_reviews": 6, "language": "en"}
    
    user_message = {
        "layout_plan": layout_plan,
        "place_payload": place_payload,
        "render_prefs": render_prefs
    }
    
    try:
        print(f"[Mapper] Calling OpenAI with layout_plan ({len(layout_plan.get('sections', []))} sections)")
        print(f"[Mapper] place_payload keys: {list(place_payload.keys())}")
        result = await openai_client.call_agent(
            system_prompt=MAPPER_SYSTEM_PROMPT,
            user_message=user_message,
            model="gpt-4o",
            temperature=0.7,
            response_format={"type": "json_object"}
        )
        print(f"[Mapper] OpenAI returned result with keys: {list(result.keys())}")
        
        # Apply sanitization to the result
        result = _sanitize_content_map(result)
        print(f"[Mapper] Returning result with {len(result.get('sections', []))} sections")
        return result
        
    except Exception as e:
        print(f"[Mapper] ERROR: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        # Return basic content map
        return {
            "sections": [],
            "sanitization": {
                "html_escaped_fields": [],
                "policy": "Escape all text; allow <a> with href + rel=noopener noreferrer"
            }
        }


def _sanitize_content_map(content_map: Dict[str, Any]) -> Dict[str, Any]:
    """Apply sanitization to content map"""
    # TODO: Implement proper sanitization
    return content_map

