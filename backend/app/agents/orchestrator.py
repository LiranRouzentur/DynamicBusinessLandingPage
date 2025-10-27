"""Main orchestrator agent - Product.md lines 94-193"""

from typing import Dict, Any, List
import json
from app.models.normalized_data import NormalizedPlacePayload, DataRichness
from app.agents.client import openai_client
from app.agents import selector, architect, mapper, generator, qa


ORCHESTRATOR_SYSTEM_PROMPT = """You are the Orchestrator. You receive normalized place data and render preferences.
Your job: validate inputs, derive business intent (data-display only), coordinate the other agents,
and assemble a final single-page bundle (index.html, styles.css, app.js) with zero runtime API calls.

Steps:
1) Validate and normalize the input payload. Infer data richness flags (has_photos, has_reviews, has_hours, has_site).
2) Ask Design-Source Selector to propose a reference design source suitable for the category and tone.
3) Ask Layout Architect to produce an explicit section/Component plan based on data richness and the chosen source.
4) Ask Content Mapper to bind real data to the plan, including safe text, curated photos, and selected reviews.
5) Ask Bundle Generator to produce index.html, styles.css, app.js with embedded data (window.__PLACE_DATA__).
6) Ask QA & Packager to validate a11y, size, no external calls (unless allow_external_cdns), then return the final bundle.

Constraints:
- Single page only.
- Strict escaping for any user text.
- Include alt text for every image.
- If a section lacks data, hide it gracefully.
- Preserve attributions for photos (render next to the image or in a credits block).
- Provide a minimal light contrast-safe theme derived from render_prefs.brand_colors or a neutral palette.
- No CTAs. The page is informational only.

Return:
- A final object with audit trail + final bundle."""


async def orchestrate_build(place_data: Dict[str, Any], render_prefs: Dict[str, Any], state=None) -> Dict[str, Any]:
    """
    Orchestrates the complete build process using OpenAI.
    
    The Orchestrator is the main agent that:
    - Validates inputs
    - Derives business intent
    - Coordinates the other agents
    - Assembles final bundle
    
    Steps:
    1) Validate and normalize input payload
    2) Call OpenAI to get orchestration plan
    3) Execute the plan by calling specialized agents
    4) Return final object with audit trail + final bundle
    """
    
    # Step 1: Validate and infer data richness flags
    validation_result = _validate_and_infer(place_data)
    
    if not validation_result["valid"]:
        return {
            "orchestrator_version": "1.0",
            "input_validation": validation_result,
            "error": "Invalid input payload"
        }
    
    place_payload = NormalizedPlacePayload(**place_data)
    data_richness = validation_result["data_richness"]
    category = _infer_category(place_payload.place.types)
    
    # Prepare input for orchestrator prompt
    orchestration_input = {
        "place": place_payload.model_dump(),
        "render_prefs": render_prefs,
        "data_richness": data_richness.model_dump() if hasattr(data_richness, 'model_dump') else data_richness,
        "category": category
    }
    
    # Step 2: Call OpenAI Orchestrator to get orchestration plan
    try:
        orchestration_plan = await openai_client.call_agent(
            system_prompt=ORCHESTRATOR_SYSTEM_PROMPT,
            user_message=orchestration_input,
            model="gpt-4o",
            temperature=0.3,
            response_format={"type": "json_object"}
        )
    except Exception as e:
        # Fallback to direct agent calls if OpenAI fails
        orchestration_plan = None
    
    # Step 3: Execute the orchestration plan
    # Whether from OpenAI or fallback, execute the 5 agent workflow
    
    # Step 4: Ask Design-Source Selector
    if state:
        state.log_event(state.phase, "Selecting design template...")
    print("[Orchestrator] Calling Selector agent...")
    design_source = await selector.select_design_source(
        business_name=place_payload.place.name,
        category=category,
        render_prefs=render_prefs,
        data_richness=data_richness
    )
    print(f"[Selector Result] {json.dumps(design_source, indent=2)}")
    if not design_source:
        print("[Orchestrator] ERROR: Selector returned None!")
    
    # Step 5: Ask Layout Architect
    if state:
        state.log_event(state.phase, "Planning layout structure...")
    print("[Orchestrator] Calling Architect agent...")
    layout_plan = await architect.create_layout_plan(
        business_name=place_payload.place.name,
        category=category,
        design_source=design_source,
        data_richness=data_richness,
        render_prefs=render_prefs
    )
    print(f"[Architect Result] {json.dumps(layout_plan, indent=2)[:2000]}")  # First 2000 chars
    if not layout_plan:
        print("[Orchestrator] ERROR: Architect returned None!")
    
    # Step 6: Ask Content Mapper
    if state:
        state.log_event(state.phase, "Mapping content to layout...")
    print("[Orchestrator] Calling Mapper agent...")
    content_map = await mapper.map_content(
        layout_plan=layout_plan,
        place_payload=place_data,
        render_prefs=render_prefs
    )
    print(f"[Mapper Result] {json.dumps(content_map, indent=2)[:2000]}")  # First 2000 chars
    if not content_map:
        print("[Orchestrator] ERROR: Mapper returned None!")
    
    # Step 7: Ask Bundle Generator (only after all 3 agents complete)
    # Verify all required data is present
    if not design_source:
        raise ValueError("Design source is missing - Selector agent failed")
    if not layout_plan:
        raise ValueError("Layout plan is missing - Architect agent failed")
    if not content_map:
        raise ValueError("Content map is missing - Mapper agent failed")
    
    if state:
        state.log_event(state.phase, "✓ All planning complete, generating HTML, CSS, and JavaScript...")
    
    print("[Orchestrator] Calling Generator agent...")
    bundle = await generator.generate_bundle(
        business_name=place_payload.place.name,
        render_prefs=render_prefs,
        layout_plan=layout_plan,
        content_map=content_map,
        design_source=design_source  # Pass design_source to generator
    )
    print(f"[Generator Result] Keys: {list(bundle.keys())}")
    print(f"[Generator Result] index.html preview: {bundle.get('index.html', bundle.get('index_html', 'N/A'))[:300]}...")
    if not bundle:
        print("[Orchestrator] ERROR: Generator returned None!")
    
    # Step 8: Ask QA & Packager
    if state:
        state.log_event(state.phase, "Running quality checks...")
    print("[Orchestrator] Calling QA agent...")
    qa_result = await qa.validate_and_package(
        bundle=bundle,
        render_prefs=render_prefs
    )
    print(f"[QA Result] Keys: {list(qa_result.keys())}")
    if 'report' in qa_result:
        print(f"[QA Result] Report: {json.dumps(qa_result['report'], indent=2)}")
    if not qa_result:
        print("[Orchestrator] ERROR: QA returned None!")
    
    # Assemble final response with audit trail + final bundle
    return {
        "orchestrator_version": "1.0",
        "input_validation": validation_result,
        "orchestration_plan": orchestration_plan,
        "context": {
            "business_name": place_payload.place.name,
            "category": category,
            "data_richness": data_richness.model_dump() if hasattr(data_richness, 'model_dump') else data_richness
        },
        "design_source": design_source,
        "layout_plan": layout_plan,
        "content_map": content_map,
        "bundle": qa_result.get("final_bundle", bundle),
        "qa_report": qa_result.get("report", {})
    }


def _validate_and_infer(place_data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate input payload and infer data richness flags."""
    warnings = []
    errors = []
    
    try:
        payload = NormalizedPlacePayload(**place_data)
        
        # Infer data richness
        has_photos = len(payload.photos) > 0
        has_reviews = len(payload.reviews) > 0
        has_hours = payload.place.opening_hours is not None and len(
            payload.place.opening_hours.weekday_text
        ) > 0
        has_site = payload.place.website is not None
        
        data_richness = DataRichness(
            has_photos=has_photos,
            has_reviews=has_reviews,
            has_hours=has_hours,
            has_site=has_site
        )
        
        if not has_photos:
            warnings.append("No photos available")
        if not has_reviews:
            warnings.append("No reviews available")
            
        return {
            "valid": True,
            "warnings": warnings,
            "errors": errors,
            "data_richness": data_richness.model_dump()
        }
        
    except Exception as e:
        errors.append(str(e))
        return {
            "valid": False,
            "warnings": warnings,
            "errors": errors,
            "data_richness": None
        }


def _infer_category(types: List[str]) -> str:
    """Infer business category from place types."""
    # Common categories mapping
    category_map = {
        "restaurant": ["restaurant", "food", "cafe", "meal"],
        "lodging": ["lodging", "hotel"],
        "store": ["store", "shopping"],
        "entertainment": ["amusement", "park", "museum"],
        "service": ["service", "business"]
    }
    
    types_lower = [t.lower() for t in types]
    
    for category, keywords in category_map.items():
        if any(kw in " ".join(types_lower) for kw in keywords):
            return category
    
    return "business"  # Default category

