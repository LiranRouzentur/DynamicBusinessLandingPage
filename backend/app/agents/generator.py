"""Bundle Generator agent - Product.md lines 518-574"""

from typing import Dict, Any
from app.agents.client import openai_client
import json


GENERATOR_SYSTEM_PROMPT = """Generate a single-page bundle: index.html, styles.css, app.js.
Embed the mapped content as a JSON blob on window.__PLACE_DATA__.
No external network calls at runtime. No external libraries unless allow_external_cdns=true.

Requirements:
- index.html: semantic structure matching the layout plan; include <meta> for viewport and language dir; include credits section.
- styles.css: responsive grid, readable typography, accessible color contrast. If brand_colors exist, use them; if not, neutral palette.
- app.js: hydrate content, lazy-load images, "Read more" toggles for long review text, zero third-party dependencies.
- Security: escape text nodes; for allowed attributions, safely set via a sanitizer that only allows <a> with href + rel attrs.
- Performance: defer JS; preload hero image if present; compress whitespace in output if possible.

Return the 3 files as strings. Do not truncate."""


# Response schema for Generator
GENERATOR_RESPONSE_SCHEMA = {
    "index_html": "<!doctype html><html lang='en' dir='ltr'>...</html>",
    "styles_css": "/* responsive, accessible styles */",
    "app_js": "window.__PLACE_DATA__=...;(()=>{ /* hydrate DOM safely */ })();",
    "meta": {
        "estimated_total_kb": 85,
        "external_requests": 0
    }
}


async def generate_bundle(
    business_name: str,
    render_prefs: Dict[str, Any],
    layout_plan: Dict[str, Any],
    content_map: Dict[str, Any],
    design_source: Dict[str, Any] = None
) -> Dict[str, Any]:
    """
    Generate index.html, styles.css, app.js bundle.
    
    Input from Orchestrator:
    {
      "business_name": "string",
      "render_prefs": {
        "language": "en",
        "direction": "ltr",
        "brand_colors": { "primary": "#0f766e", "accent": "#22d3ee" },
        "font_stack": "system-ui",
        "allow_external_cdns": false
      },
      "layout_plan": { /* from Architect */ },
      "content_map": { /* from Mapper */ }
    }
    
    Output:
    {
      "index_html": "<!doctype html>...",
      "styles_css": "/* css */",
      "app_js": "// js",
      "meta": {
        "estimated_total_kb": 85,
        "external_requests": 0
      }
    }
    """
    user_message = {
        "business_name": business_name,
        "render_prefs": render_prefs,
        "layout_plan": layout_plan,
        "content_map": content_map,
        "design_source": design_source  # Include design source for context
    }
    
    try:
        result = await openai_client.call_agent(
            system_prompt=GENERATOR_SYSTEM_PROMPT,
            user_message=user_message,
            model="gpt-4o",
            temperature=0.7,
            response_format={"type": "json_object"}
        )
        return result
        
    except Exception as e:
        # Return basic bundle
        return _generate_fallback_bundle(business_name, render_prefs)


def _generate_fallback_bundle(business_name: str, render_prefs: Dict[str, Any]) -> Dict[str, Any]:
    """Generate a basic fallback bundle"""
    return {
        "index_html": f"<!doctype html><html><head><title>{business_name}</title></head><body></body></html>",
        "styles_css": "/* basic styles */",
        "app_js": "/* basic hydration */",
        "meta": {
            "estimated_total_kb": 10,
            "external_requests": 0
        }
    }

