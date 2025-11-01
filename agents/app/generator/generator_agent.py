"""Generator agent implementation based on landing-page-agent-with-qa.md"""
import asyncio
import hashlib
import json
import logging
import os
import re
import httpx
from typing import Dict, Any, Optional, List
from pydantic import ValidationError
from app.base_agent import BaseAgent, AgentError
from app.generator.generator_prompt import GENERATOR_SYSTEM_PROMPT
from app.generator.generator_schemas import GeneratorOutput, GENERATOR_RESPONSE_SCHEMA

logger = logging.getLogger(__name__)


# Unsplash API configuration
UNSPLASH_ACCESS_KEY = os.getenv("UNSPLASH_ACCESS_KEY", "")
UNSPLASH_API_URL = "https://api.unsplash.com/search/photos"

# Fallback emergency images (only if API fails)
EMERGENCY_FALLBACK = [
    "https://images.unsplash.com/photo-1556742049-0cfed4f6a45d?q=80&w=1600&auto=format",
    "https://images.unsplash.com/photo-1517248135467-4c7edcad34c4?q=80&w=1600&auto=format"
]


# Computes stable deterministic seed from place_id + primary_type for consistent design generation.
# Same business always gets same seed → same visual design (grid, colors, typography, animations).
def design_seed(google_data: Dict[str, Any]) -> int:
    """
    Compute a stable design seed from business identifiers.
    Same business → same seed → same design.
    Different business → different seed → different design.
    
    Args:
        google_data: Google Maps business data
        
    Returns:
        Stable integer seed
    """
    place_id = google_data.get("place_id", "")
    primary_type = google_data.get("primary_type", "")
    key = f"{place_id}|{primary_type}"
    seed_hex = hashlib.sha256(key.encode()).hexdigest()[:8]
    return int(seed_hex, 16)


# Maps seed to controlled design parameter ranges (grid width, radius, shadows, palette, typography, animations).
# Returns dict of deterministic design values that drive visual uniqueness across businesses.
def design_knobs(seed: int) -> Dict[str, int]:
    """
    Map seed to controlled design parameter ranges.
    All values are deterministic based on seed.
    
    Args:
        seed: Stable integer from design_seed()
        
    Returns:
        Dict of design parameters (grid width, radius, shadow level, etc.)
    """
    rng = seed % 1_000_000
    
    return {
        "grid_max_width": [1100, 1140, 1200, 1280][rng % 4],
        "radius": [12, 16, 20, 24][(rng // 10) % 4],
        "shadow_level": [1, 2, 3][(rng // 100) % 3],
        "palette_variant": (rng // 1000) % 6,  # choose different tints/accents
        "typography_pair": (rng // 10000) % 5,  # Inter only or Inter + Display accent
        "shape_motif": (rng // 100000) % 4,  # pill / angled / rounded-rect / outline
        "motion_profile": (rng // 200000) % 3  # subtle-fade / slide-up / parallax-lite
    }


# Fetches high-res stock images from Unsplash API based on search query (e.g., "pizza restaurant interior").
# Returns list of image URLs with 1600px width; falls back to emergency images if API fails.
async def fetch_stock_images(query: str, count: int = 3) -> List[str]:
    """
    Fetch stock images from Unsplash API based on search query.
    
    Args:
        query: Search term (e.g., "pizza restaurant", "cafe interior")
        count: Number of images to fetch (default: 3)
        
    Returns:
        List of image URLs (high-res, formatted for web use)
    """
    if not UNSPLASH_ACCESS_KEY:
        logger.warning("[fetch_stock_images] No UNSPLASH_ACCESS_KEY found, using emergency fallback")
        return EMERGENCY_FALLBACK[:count]
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            params = {
                "query": query,
                "per_page": count,
                "orientation": "landscape",
                "client_id": UNSPLASH_ACCESS_KEY
            }
            
            logger.info(f"[fetch_stock_images] Searching Unsplash for '{query}' (count={count})")
            response = await client.get(UNSPLASH_API_URL, params=params)
            
            if response.status_code != 200:
                logger.error(f"[fetch_stock_images] Unsplash API error: {response.status_code}")
                return EMERGENCY_FALLBACK[:count]
            
            data = response.json()
            results = data.get("results", [])
            
            if not results:
                logger.warning(f"[fetch_stock_images] No results for '{query}', using emergency fallback")
                return EMERGENCY_FALLBACK[:count]
            
            # Extract URLs with proper sizing (regular = ~1080px width, good for web)
            image_urls = [
                photo["urls"]["regular"] + "&w=1600&q=80&auto=format"
                for photo in results[:count]
                if "urls" in photo and "regular" in photo["urls"]
            ]
            
            logger.info(f"[fetch_stock_images] Found {len(image_urls)} images for '{query}'")
            return image_urls if image_urls else EMERGENCY_FALLBACK[:count]
            
    except Exception as e:
        logger.error(f"[fetch_stock_images] Failed to fetch images: {e}")
        return EMERGENCY_FALLBACK[:count]


# Converts QA error codes into human-readable fix instructions for the generator.
# Provides explicit guidance like "Add Google Fonts link" or "Remove visibility:hidden from body".
def explain_qa_error(error_code: str) -> str:
    """
    Convert QA error code to human-readable fix instruction.
    
    Args:
        error_code: Error code from qa_html_css()
        
    Returns:
        Human-readable instruction for fixing the error
    """
    error_explanations = {
        "too_few_sections": "Add more <section> tags (need at least 3: features, testimonial, CTA)",
        "missing_h1": "Add exactly one <h1> tag for the main heading",
        "no_google_fonts": "Add Google Fonts <link> in <head> (e.g., <link href='https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap' rel='stylesheet'>)",
        "missing_viewport": "Add <meta name='viewport' content='width=device-width, initial-scale=1'> in <head>",
        "weak_hero": "Hero section needs min-height with vh units (e.g., min-height: 60vh)",
        "missing_css_tokens": "Define CSS variables in :root (e.g., --primary-color, --radius, --shadow)",
        "body_visibility_hidden": "CRITICAL: Remove 'visibility: hidden' from body tag - this makes page invisible! Use 'visibility: visible' or remove the property entirely",
        "non_https_image": "All image URLs must use HTTPS, not HTTP. Replace http:// with https://",
        "suspicious_long_url": "Image URL is too long (>500 chars). Use shorter, direct image URLs from stock_images_urls provided",
        "using_named_colors": "CSS variables should use hex/rgb colors (e.g., #006491, rgb(0,100,145)) NOT named colors (red, blue, etc.)",
        "missing_cdn:bootstrap": "Add Bootstrap 5 CDN in <head>: <link href='https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css' rel='stylesheet'>",
        "missing_cdn:aos": "Add AOS (Animate On Scroll) CDN in <head>: <link href='https://unpkg.com/aos@2.3.1/dist/aos.css' rel='stylesheet'>",
        "missing_cdn:fontawesome": "Add Font Awesome CDN in <head>: <link rel='stylesheet' href='https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css'>",
    }
    
    # Handle dynamic error codes
    if error_code.startswith("missing_cdn:"):
        cdn_name = error_code.split(":")[-1]
        return error_explanations.get(f"missing_cdn:{cdn_name}", f"Add required {cdn_name} CDN library")
    elif error_code.startswith("missing_tag:"):
        tag = error_code.split(":")[-1]
        return f"Add missing HTML tag: {tag}"
    
    return error_explanations.get(error_code, f"Fix quality gate issue: {error_code}")


# Runs quality gates on HTML: checks sections, h1, fonts, viewport, CSS variables, CDNs, images, forms.
# Returns list of error codes (empty if passes); enforces single-file, CTA-free requirements.
def qa_html_css(index_html: str) -> List[str]:
    """
    Run quality gates on generated HTML/CSS with enhanced checks for broken designs
    
    Args:
        index_html: The HTML content to validate
        
    Returns:
        List of error codes (empty if all checks pass)
    """
    errs = []
    html_lower = index_html.lower()
    
    # Check for sections (hero + at least 3 semantic sections)
    section_count = html_lower.count("<section")
    if section_count < 3:
        errs.append("too_few_sections")
    
    # H1 present
    if "<h1" not in html_lower:
        errs.append("missing_h1")
    
    # Google Fonts link - CRITICAL for proper font rendering
    if 'fonts.googleapis.com' not in index_html:
        errs.append("no_google_fonts")
    
    # Responsive meta viewport
    if 'name="viewport"' not in index_html and "name='viewport'" not in index_html:
        errs.append("missing_viewport")
    
    # CSS rule count check removed - let the generator focus on quality over quantity
    # The Bootstrap + custom CSS combo provides sufficient styling
    # css_rule_count = len(re.findall(r"\{[^}]*\}", index_html))
    # if css_rule_count < 80:
    #     errs.append(f"too_few_css_rules:{css_rule_count}")
    
    # Hero size heuristic (should have viewport height)
    if "min-height:" not in html_lower or "vh" not in html_lower:
        errs.append("weak_hero")
    
    # Check for CSS variables (tokens)
    if "--" not in index_html or ":root" not in index_html:
        errs.append("missing_css_tokens")
    
    # NEW: Check for visibility:hidden on body (breaks rendering)
    if "body" in html_lower and "visibility:" in html_lower and "hidden" in html_lower:
        # Check if body has visibility:hidden (common mistake)
        if re.search(r'body\s*\{[^}]*visibility\s*:\s*hidden', html_lower):
            errs.append("body_visibility_hidden")
    
    # NEW: Check for REQUIRED external libraries (Bootstrap, AOS, Font Awesome)
    required_cdns = {
        'bootstrap': 'cdn.jsdelivr.net/npm/bootstrap',
        'aos': 'unpkg.com/aos',
        'fontawesome': 'font-awesome'
    }
    for cdn_name, cdn_url in required_cdns.items():
        if cdn_url not in index_html.lower():
            errs.append(f"missing_cdn:{cdn_name}")
    
    # NEW: Validate image URLs (must be HTTPS and from known sources)
    img_urls = re.findall(r'(?:src|url)\s*[=:(]\s*["\']([^"\']+)["\']', index_html, re.IGNORECASE)
    invalid_images = []
    for url in img_urls:
        if url.startswith('http://'):  # Non-HTTPS
            invalid_images.append("non_https_image")
            break
        elif url.startswith('https://') and len(url) > 500:  # Suspiciously long URLs
            invalid_images.append("suspicious_long_url")
            break
    if invalid_images:
        errs.extend(invalid_images)
    
    # NEW: Check for proper color definitions (no plain 'red', 'blue', etc.)
    inline_style_match = re.search(r'<style[^>]*>(.*?)</style>', index_html, re.DOTALL | re.IGNORECASE)
    if inline_style_match:
        css_content = inline_style_match.group(1)
        # Check for CSS variables being defined
        if ':root' in css_content:
            # Verify color variables are hex or rgb, not named colors
            color_vars = re.findall(r'--[^:]+:\s*([^;]+);', css_content)
            for color_val in color_vars:
                color_val = color_val.strip()
                # Check for bare named colors (red, blue, etc.) - these are usually mistakes
                if color_val in ['red', 'blue', 'green', 'yellow', 'black', 'white', 'gray', 'grey']:
                    errs.append("using_named_colors")
                    break
    
    # NEW: Check for complete HTML structure
    required_tags = ['<!doctype', '<html', '<head>', '<body>', '</html>']
    for tag in required_tags:
        if tag not in html_lower:
            errs.append(f"missing_tag:{tag}")
            break
    
    return errs


# Maps Google Place types to better Unsplash search terms (e.g., "pizza_restaurant" → "pizza restaurant interior").
# Returns optimized search query for stock image API to get relevant business imagery.
def build_search_query(place_types: List[str], business_name: str = "") -> str:
    """
    Build a search query for stock images based on business type.
    
    Args:
        place_types: List of Google Place types (e.g., ["pizza_restaurant", "meal_delivery"])
        business_name: Business name for additional context (optional)
        
    Returns:
        Search query string for stock image API
    """
    # Map common place types to better search terms
    type_mapping = {
        "pizza_restaurant": "pizza restaurant interior",
        "meal_delivery": "food delivery",
        "restaurant": "restaurant interior",
        "supermarket": "grocery store",
        "cafe": "coffee shop cafe",
        "bakery": "bakery pastries",
        "bar": "bar interior",
        "clothing_store": "clothing boutique",
        "electronics_store": "electronics store",
        "gym": "fitness gym",
        "hair_care": "hair salon",
        "hardware_store": "hardware store",
        "home_goods_store": "home decor store",
        "jewelry_store": "jewelry display",
        "shoe_store": "shoe store display",
        "spa": "spa wellness",
        "store": "retail store"
    }
    
    # Try to match the first place type
    for place_type in place_types:
        if place_type in type_mapping:
            query = type_mapping[place_type]
            logger.info(f"[build_search_query] Mapped '{place_type}' to '{query}'")
            return query
    
    # Fallback: use the first place type directly, cleaned up
    if place_types:
        query = place_types[0].replace("_", " ")
        logger.info(f"[build_search_query] Using cleaned place_type: '{query}'")
        return query
    
    # Ultimate fallback
    logger.warning("[build_search_query] No place types available, using 'business'")
    return "business"


class GeneratorAgent(BaseAgent):
    """Generator agent - produces static site files with QA/validation loop"""
    
    # Initializes generator with OpenAI client and optimal temperature (0.7 empirically tested).
    # No internal retries - orchestrator handles all retry logic to prevent retry explosion.
    def __init__(self, client, model: str = "gpt-4.1", temperature: float = 0.7):
        super().__init__(client, model, temperature, agent_name="Generator")
        self.default_temperature = temperature  # Store default for retries
        # Note: 0.7 is optimal based on empirical testing (matches ChatGPT quality)
        # No max_retries - removed internal QA loop, only retry on schema validation errors
    
    # Refines HTML using screenshot + errors via Responses API multimodal input (text + PNG image).
    # AI analyzes rendered page visually and fixes spacing, contrast, alignment, typography; returns (output, response_id).
    async def run_with_visual_feedback(
        self,
        html_content: str,
        screenshot_base64: str,
        validator_errors: List[str],
        previous_response_id: Optional[str] = None
    ) -> tuple[Dict[str, Any], Optional[str]]:
        """
        Refine HTML based on visual screenshot and validation errors.
        Uses Responses API with multimodal input (text + image).
        
        Args:
            html_content: Current HTML to refine
            screenshot_base64: Base64-encoded PNG screenshot
            validator_errors: List of validation errors
            previous_response_id: Previous response ID for stateful context
            
        Returns:
            Tuple of (refined output dict, new response_id)
        """
        logger.info(
            f"[Generator] Running visual feedback refinement | "
            f"screenshot_size: {len(screenshot_base64)} bytes | "
            f"errors: {len(validator_errors)} | "
            f"stateful: {bool(previous_response_id)}"
        )
        
        # Build multimodal prompt
        visual_prompt = (
            f"Analyze the screenshot of the rendered page and fix the following issues:\n\n"
            f"VALIDATION ERRORS:\n" + "\n".join(f"- {err}" for err in validator_errors) + "\n\n"
            f"Focus on:\n"
            f"1. Visual hierarchy and spacing (ensure proper rhythm and breathing room)\n"
            f"2. Color contrast and readability (check text is readable on backgrounds)\n"
            f"3. Layout alignment (ensure sections are properly aligned)\n"
            f"4. Image loading and display (verify images are visible and properly sized)\n"
            f"5. Typography and line-height (ensure text is comfortable to read)\n\n"
            f"Return the COMPLETE refined HTML in the same JSON format."
        )
        
        # Call Responses API with image
        result, response_id = await self._call_responses_api(
            system_prompt=GENERATOR_SYSTEM_PROMPT,
            user_message={
                "content": [
                    {"type": "input_text", "text": visual_prompt},
                    {"type": "input_image", "image_url": f"data:image/png;base64,{screenshot_base64}"}
                ],
                "tamplate": html_content,
                "validator_errors": validator_errors
            },
            response_schema=GENERATOR_RESPONSE_SCHEMA,
            temperature=0.2,  # Lower temperature for refinements
            max_tokens=16000,
            previous_response_id=previous_response_id,
            is_retry=True
        )
        
        # Validate and return
        validated = GeneratorOutput.model_validate(result)
        return validated.model_dump(), response_id
    
    # Adds stock image URLs to mapper_data if business images are insufficient (< 2 HTTPS images).
    # Fetches from Unsplash based on place types; combines business + stock images for variety.
    async def _enhance_with_stock_images(self, mapper_data: Dict[str, Any], google_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Add stock-image URLs to mapper_data by fetching from Unsplash API if business images are missing.
        
        Args:
            mapper_data: Mapper output data
            google_data: Google Maps business data
            
        Returns:
            Enhanced mapper_data with stock_images_urls added if needed
        """
        enhanced = mapper_data.copy()
        
        # Extract business types from google_data
        place_types = google_data.get("types", [])
        business_name = google_data.get("name", "")
        
        # Extract current images from mapper_data (note: "assats" is the field name in mapper schema)
        assats = enhanced.get("assats", {}) if isinstance(enhanced.get("assats"), dict) else {}
        business_images = assats.get("business_images_urls", []) or []
        
        # Filter to HTTPS images only
        https_images = [img for img in business_images if img and img.startswith("https://")]
        
        # Decide whether to fetch stock images
        if https_images and len(https_images) >= 2:
            # We have enough business images, use them
            selected_images = https_images
            logger.info(f"[Generator] Using {len(selected_images)} business images (no stock needed)")
        else:
            # Need to fetch stock images
            search_query = build_search_query(place_types, business_name)
            logger.info(f"[Generator] Fetching stock images for query: '{search_query}'")
            
            stock_images = await fetch_stock_images(search_query, count=3)
            
            # Combine business images (if any) with stock images
            selected_images = https_images + stock_images
            logger.info(
                f"[Generator] Using {len(https_images)} business + {len(stock_images)} stock images"
            )
        
        # Update stock_images_urls in mapper_data.assats
        if "assats" not in enhanced or not isinstance(enhanced["assats"], dict):
            enhanced["assats"] = {}
        
        enhanced["assats"]["stock_images_urls"] = selected_images
        
        return enhanced
    
    # Generates complete single-file HTML landing page with Bootstrap, AOS, Font Awesome, custom CSS/JS.
    # Uses design seed for uniqueness, fetches stock images if needed, runs QA checks; returns {html, meta, _qa_errors}.
    async def run(
        self,
        google_data: Dict[str, Any],
        mapper_data: Dict[str, Any],
        tamplate: Optional[str] = None,
        validator_errors: Optional[List[str]] = None,
        interactivity_tier: str = "enhanced",
        asset_budget: int = 3,
        final_attempt: bool = False,  # If True, use temperature=0 for deterministic output
        session_id: Optional[str] = None  # NEW: Session ID for stateful context tracking
    ) -> Dict[str, Any]:
        """
        Generate static landing page with QA/validation loop
        
        Args:
            google_data: Original Google Maps data
            mapper_data: Enriched data from mapper agent
            tamplate: Optional previous HTML attempt for iterative fixes
            validator_errors: Optional list of validation errors to fix
            interactivity_tier: "basic" | "enhanced" (default) | "highend"
            asset_budget: Target number of images (3-6)
            final_attempt: If True, use temperature=0 for deterministic output
            
        Returns:
            Generated bundle with html and meta fields
        
        Note: Internal retries removed to prevent retry explosion.
              Orchestrator handles all retry logic for predictable behavior.
        """
        logger.info(
            f"[Generator] Starting generation | "
            f"final_attempt: {final_attempt} | "
            f"tier: {interactivity_tier} | "
            f"asset_budget: {asset_budget} | "
            f"has_template: {bool(tamplate)} | "
            f"has_validator_errors: {bool(validator_errors)} | "
            f"business_name: {google_data.get('name', 'N/A')}"
        )
        
        try:
            # Compute deterministic design seed and knobs for uniqueness
            seed = design_seed(google_data)
            knobs = design_knobs(seed)
            
            logger.info(
                f"[Generator] Design uniqueness | "
                f"seed: {seed} | "
                f"grid: {knobs['grid_max_width']}px | "
                f"radius: {knobs['radius']}px | "
                f"shadow: {knobs['shadow_level']} | "
                f"motif: {knobs['shape_motif']} | "
                f"motion: {knobs['motion_profile']}"
            )
            
            # Enhance mapper_data with stock-image fallback if needed (fetch from Unsplash API)
            enhanced_mapper_data = await self._enhance_with_stock_images(mapper_data, google_data)
            
            user_message = {
                "google_data": google_data,
                "mapper_data": enhanced_mapper_data,
                "seed": seed,
                "knobs": knobs,
                "tamplate": tamplate,  # null/None on first run
                "validator_errors": validator_errors,  # null/None on first run
                "interactivity_tier": interactivity_tier,
                "asset_budget": asset_budget
            }
            
            # Creative sampling parameters (optimized for design variety)
            # Responses API only supports: temperature, top_p, max_output_tokens
            # No presence_penalty or frequency_penalty support
            current_temp = 1.05  # Raised from 0.7 for more creativity (balanced)
            top_p = 0.95  # Wide nucleus sampling for diverse token choices
            
            logger.info(
                f"[Generator] Creative sampling | "
                f"temp: {current_temp} | top_p: {top_p} | "
                f"reasoning: 'Enhanced creativity via higher temp + wide nucleus sampling'"
            )
            
            # Check if Responses API (stateful context) is enabled
            from app.base_agent import USE_RESPONSES_API
            
            # Determine cache_key for response_id tracking
            cache_key = f"generator_{session_id}" if session_id else None
            
            if USE_RESPONSES_API:
                # Use Responses API with stateful context for token savings on retries
                result, response_id = await self._call_responses_api(
                    system_prompt=GENERATOR_SYSTEM_PROMPT,
                    user_message=user_message,
                    response_schema=GENERATOR_RESPONSE_SCHEMA,
                    temperature=current_temp,
                    max_tokens=12000,
                    previous_response_id=None,  # First attempt has no previous context
                    is_retry=False,
                    cache_key=cache_key,
                    top_p=top_p,
                )
            else:
                # Fallback to original Chat Completions API
                result = await self._call_openai(
                    system_prompt=GENERATOR_SYSTEM_PROMPT,
                    user_message=user_message,
                    response_schema=GENERATOR_RESPONSE_SCHEMA,
                    temperature=current_temp,
                    responses_api_mode=True  # Enable Responses API mode
                )
                response_id = None  # No response_id in Chat Completions mode
            
            # Validate output schema (Pydantic)
            try:
                validated = GeneratorOutput.model_validate(result)
                output_dict = validated.model_dump()
                
                # Run quality gates on generated HTML
                html_content = output_dict.get("html", "")
                qa_errors = qa_html_css(html_content)
                
                # MINIMAL FLOW: Don't retry here - return errors to orchestrator for batching
                # Orchestrator will collect ALL errors (QA + MCP + CORS + visual) and retry ONCE
                if qa_errors:
                    logger.warning(
                        f"[Generator] Quality gates detected {len(qa_errors)} issue(s) | "
                        f"errors: {qa_errors} | "
                        f"Note: Returning to orchestrator for batched validation"
                    )
                    # Store QA errors for orchestrator to batch with other validators
                    output_dict["_qa_errors"] = [explain_qa_error(err) for err in qa_errors]
                
                html_size = len(output_dict.get("html", ""))
                logger.info(f"[Generator] ✓ Generation completed | html_size: {html_size} chars | qa_issues: {len(qa_errors)}")
                
                # Return immediately - no internal retry loop
                return output_dict
                
            except ValidationError as validation_err:
                # Schema validation error - don't retry internally
                # Let orchestrator handle retries to avoid retry explosion
                # (Previously had internal retries that caused 6x more attempts than expected)
                error_details = str(validation_err)
                logger.error(
                    f"[Generator] ✗ Schema validation failed | "
                    f"error: {error_details[:200]} | "
                    f"response_keys: {list(result.keys()) if isinstance(result, dict) else 'N/A'}"
                )
                raise AgentError(f"Generator schema validation failed: {validation_err}")
            
        except AgentError:
            # Re-raise AgentError (already logged)
            raise
        except Exception as e:
            error_type = type(e).__name__
            logger.error(
                f"[Generator] ✗ Generation failed with unexpected error | "
                f"error_type: {error_type} | "
                f"error: {str(e)}",
                exc_info=True
            )
            raise AgentError(f"Generator failed: {e}")


# Export for convenience
__all__ = ["GeneratorAgent"]

