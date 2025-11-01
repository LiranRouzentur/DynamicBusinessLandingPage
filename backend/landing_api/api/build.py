"""Build API endpoint - refactored for better maintainability"""
from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from landing_api.models.schemas import BuildRequest, BuildResponse
from landing_api.models.errors import ApplicationError, ErrorCode
from landing_api.core.auth import verify_api_key
from landing_api.core.google_fetcher import google_fetcher
from landing_api.core.artifact_store import artifact_store
from landing_api.core.state_machine import BuildState, BuildPhase
from landing_api.core.agents_client import agents_client
from landing_api.core.config import settings
import uuid
import asyncio
import shutil
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime, timedelta

# --- New pipeline-aligned error and fetch helpers ---
# Ensures business name is not a place_id or empty string; returns "Business" if invalid.
# Prevents display of technical IDs (ChIJ..., places/...) in user-facing content.
def _sanitize_business_name(name: Optional[str]) -> str:
    """
    Ensure business name is not a place_id or empty string.
    
    Args:
        name: Business name from API or data
        
    Returns:
        Sanitized business name, defaults to "Business" if invalid
    """
    if not name or not isinstance(name, str):
        return "Business"
    
    name = name.strip()
    
    # Check if name looks like a place_id
    if not name or name.startswith("places/") or name.startswith("ChIJ"):
        return "Business"
    
    return name


# Fetches place data from Google Places API and logs progress to state machine.
# Sanitizes business name and emits user-friendly events; returns None if fetch fails.
async def _fetch_place_data(place_id: str, state) -> dict:
    """Fetch place data from Google Places API and log progress to state."""
    from landing_api.core.google_fetcher import google_fetcher
    logger.info(f"[GOOGLE FETCH] Fetching place data for place_id: {place_id}")
    state.log_event(BuildPhase.FETCHING, "Discovering your business details...")
    try:
        place_data = await google_fetcher.fetch_place(place_id)
        business_name = _sanitize_business_name(place_data.get("name"))
        state.log_event(BuildPhase.FETCHING, f"✓ Found {business_name} — gathering all the details")
        return place_data
    except Exception as e:
        _handle_error(state, e)
        return None

# Formats and logs build errors to state machine; distinguishes ApplicationError with hints from generic exceptions.
# Updates state metadata with error info and marks build as failed.
def _handle_error(state, error):
    """Handle build errors and log them to state"""
    logger.error(f"Build error: {repr(error)}")
    
    # Format error message based on error type
    if isinstance(error, ApplicationError):
        error_msg = f"✗ {error.message}"
        if error.hint:
            error_msg += f" {error.hint}"
        error_info = error.model_dump()
    else:
        error_msg = "✗ An error occurred. Please try again."
        error_info = {
            "message": str(error),
            "type": type(error).__name__,
            "retryable": True
        }
    
    state.log_event(BuildPhase.ERROR, error_msg)
    state.metadata["success"] = False
    state.metadata["error"] = error_info


router = APIRouter()
logger = logging.getLogger(__name__)

# In-memory session store (in production, use Redis or similar)
session_store = {}


# ============================================================================
# Helper Functions
# ============================================================================

# Returns default rendering preferences (language, direction, CDN allowance, review limits).
# Used when client doesn't provide render_prefs in build request.
def _get_default_render_prefs() -> Dict[str, Any]:
    """Get default rendering preferences"""
    return {
        "language": "en",
        "direction": "ltr",
        "allow_external_cdns": True,
        "max_reviews": 6
    }


# Calculates data availability flags (has_photos, has_reviews, has_hours, has_site) from place data.
# Helps agents adapt generation strategy based on available content richness.
def _calculate_data_richness(place_data: Dict[str, Any]) -> Dict[str, bool]:
    """Calculate data richness flags from place data"""
    status = place_data.get("status", {})
    return {
        "has_photos": len(place_data.get("photos", [])) > 0,
        "has_reviews": len(place_data.get("reviews", [])) > 0,
        "has_hours": len(status.get("weekday_descriptions", [])) > 0,
        "has_site": place_data.get("website_url") is not None
    }


# Validates bundle contains non-empty HTML string; raises ApplicationError if missing/invalid.
# Critical validation before file I/O to ensure output meets requirements.
def _validate_html(bundle: Dict[str, Any], session_id: str) -> None:
    """Validate the bundle contains the HTML output string."""
    if "html" not in bundle or not isinstance(bundle["html"], str) or not bundle["html"].strip():
        logger.error(f"Session {session_id}: Missing or empty html field")
        raise ApplicationError(
            code=ErrorCode.BUNDLE_INVALID,
            message=f"Landing page output missing HTML document.",
            retryable=False,
            hint="The generated HTML is missing. Please report this issue."
        )

# Validates and saves inline HTML bundle to artifact store; logs progress events.
# Emits user-friendly messages ("Design complete", "Polishing") and handles storage errors.
async def _process_bundle(
    session_id: str,
    bundle: Dict[str, Any],
    state: BuildState
) -> None:
    """Process and save inline-html bundle output"""
    _validate_html(bundle, session_id)
    state.log_event(BuildPhase.GENERATING, "✓ Design complete — bringing it all together")
    state.log_event(BuildPhase.QA, "Polishing every detail for perfection...")
    try:
        artifact_store.save_html(session_id=session_id, html=bundle["html"], meta=bundle.get("meta"))
        state.log_event(BuildPhase.QA, "✓ Final touches applied")
    except Exception as e:
        logger.error(f"Failed to save html artifact: {e}", exc_info=True)
        raise ApplicationError(
            code=ErrorCode.CACHE_ERROR,
            message=f"Failed to save landing page: {str(e)}",
            retryable=True,
            hint="Storage issue encountered. Please try again."
        )

# Invokes agents service to generate landing page HTML/meta; logs progress and handles errors.
# Calculates data richness and category before sending; returns agent result or None if failed.
async def _call_ai_agents(session_id: str, place_data: dict, render_prefs: dict, state) -> dict:
    """Invoke agent service to generate landing page HTML/meta. Logs progress and handles errors."""
    try:
        from landing_api.core.agents_client import agents_client
        state.log_event(BuildPhase.GENERATING, "Crafting your unique design...")
        # Calculate data richness and category
        data_richness = _calculate_data_richness(place_data)
        category = place_data.get("types", ["establishment"])[0] if place_data.get("types") else "establishment"
        
        result = await agents_client.build(
            session_id=session_id,
            business_name=place_data.get("name", "Business"),
            category=category,
            place_data=place_data,
            render_prefs=render_prefs,
            data_richness=data_richness,
        )
        if not result or not result.get("success"):
            error_msg = result.get("error", "Unknown error") if result else "Agent service unavailable"
            raise ApplicationError(
                code="ORCHESTRATION_ERROR",
                message=f"AI agents failed: {error_msg}",
                retryable=True,
                hint="The AI generation service encountered an issue. Please try again."
            )
        state.log_event(BuildPhase.GENERATING, "✓ Design elements coming together beautifully")
        return result
    except Exception as e:
        _handle_error(state, e)
        return None


# ============================================================================
# Main Build Logic
# ============================================================================

# Main build workflow: fetches place data → calls AI agents → processes bundle → emits success.
# Updates state machine throughout; creates storytelling progress messages for user experience.
async def _run_build(session_id: str, place_id: str, render_prefs: dict) -> None:
    """Main build workflow"""
    logger.info(f"[BUILD START] Session {session_id}, place_id: {place_id}")
    state = session_store.get(session_id)
    if not state:
        logger.error(f"Session {session_id} not found")
        return
    
    try:
        logger.info(f"[STEP 1] Fetching place data for {place_id}")
        # Step 1: Fetch place data
        place_data = await _fetch_place_data(place_id, state)
        if not place_data:
            logger.warning(f"[BUILD] No place data returned for {place_id}")
            return
        
        # Create engaging opening narrative based on business info
        business_name = _sanitize_business_name(place_data.get("name"))
        
        business_type = place_data.get("types", ["establishment"])[0] if place_data.get("types") else "business"
        category = business_type.replace("_", " ").title()
        
        # Determine business type description
        type_desc = ""
        if category and category.lower() not in ["establishment", "point of interest"]:
            type_desc = category.lower()
        
        # Create a story-like opening message similar to AI generator example
        opening_message = f"I'll create a stunning landing page for {business_name}"
        if type_desc:
            opening_message += f", a {type_desc}"
        opening_message += ", with an elegant, high-end design."
        
        # Add plan details
        has_photos = len(place_data.get("photos", [])) > 0
        has_reviews = len(place_data.get("reviews", [])) > 0
        
        plan_features = []
        plan_features.append("Hero section with bold branding")
        if has_reviews:
            plan_features.append("Customer testimonials showcase")
        if has_photos:
            plan_features.append("Beautiful imagery gallery")
        plan_features.append("Key benefits highlight")
        plan_features.append("Contact information section")
        plan_features.append("Clean, modern footer")
        
        # Show plan details in correct order: Plan: header first, then opening message, then sections
        state.log_event(BuildPhase.ORCHESTRATING, "Plan:")
        state.log_event(BuildPhase.ORCHESTRATING, opening_message)
        state.log_event(BuildPhase.ORCHESTRATING, "Key Features:")
        for feature in plan_features[:5]:  # Show up to 5 features
            state.log_event(BuildPhase.ORCHESTRATING, f"• {feature}")
        state.log_event(BuildPhase.ORCHESTRATING, "Design:")
        state.log_event(BuildPhase.ORCHESTRATING, "• Fresh color palette")
        state.log_event(BuildPhase.ORCHESTRATING, "• Luxurious spacing and typography")
        state.log_event(BuildPhase.ORCHESTRATING, "• Smooth fade-in animations")
        state.log_event(BuildPhase.ORCHESTRATING, "• Premium, breathable layout")
        state.log_event(BuildPhase.ORCHESTRATING, "Structure:")
        state.log_event(BuildPhase.ORCHESTRATING, "• Single responsive landing page with multiple sections")
        
        logger.info(f"[STEP 2] Calling AI agents...")
        # Step 2: Call AI agents
        agents_result = await _call_ai_agents(session_id, place_data, render_prefs, state)
        
        if not agents_result or not agents_result.get("success"):
            error_msg = None
            if agents_result:
                error_msg = agents_result.get("error", "Unknown error")
                logger.error(f"AI agents failed: {error_msg}")
                state.log_event(BuildPhase.ERROR, f"Build failed: {error_msg}")
            else:
                error_msg = "AI agents service unavailable"
                logger.error("AI agents returned None - build failed")
                state.log_event(BuildPhase.ERROR, f"Build failed: {error_msg}")
            state.metadata["success"] = False
            state.metadata["error"] = {"message": error_msg, "retryable": True}
            return
        
        logger.info(f"[STEP 3] Processing bundle...")
        # Step 3: Process bundle
        await _process_bundle(session_id, agents_result["bundle"], state)
        
        # Success
        state.log_event(BuildPhase.READY, f"✓ Your stunning landing page is ready!")
        state.metadata["success"] = True
        state.metadata["business_name"] = place_data.get("name", "Unknown")
        logger.info(f"Build completed successfully for session {session_id}")
        
    except ApplicationError as e:
        _handle_error(state, e)
    except Exception as e:
        logger.exception("Unexpected error in build")
        _handle_error(state, e)


# Sync wrapper for background task; runs async build in new event loop via asyncio.run().
# Uses print() with flush for reliable logging in background threads; handles event loop lifecycle.
def _run_build_sync(session_id: str, place_id: str, render_prefs: dict) -> None:
    """Sync wrapper for background task"""
    # Use print() with flush to bypass logging issues in background tasks
    print(f"\n{'='*80}", flush=True)
    print(f"[BACKGROUND TASK START] Session: {session_id}, Place ID: {place_id}", flush=True)
    print(f"{'='*80}\n", flush=True)
    
    logger.info(f"[BACKGROUND TASK] Starting build for session {session_id}")
    
    loop = None
    try:
        print("[BACKGROUND TASK] Creating new event loop...", flush=True)
        # Use asyncio.run() which properly handles event loop lifecycle
        # This ensures all async resources are cleaned up before the loop closes
        asyncio.run(_run_build(session_id, place_id, render_prefs))
        print("[BACKGROUND TASK] ✓ Build completed successfully", flush=True)
    except Exception as e:
        print(f"[BACKGROUND TASK] ✗ ERROR: {e}", flush=True)
        logger.error(f"Sync wrapper error: {e}", exc_info=True)


# Background task: periodically cleans up terminal sessions older than 1 hour every 5 minutes.
# Prevents memory leaks from accumulated session state; runs forever until service shutdown.
async def cleanup_old_sessions() -> None:
    """Periodically clean up terminal sessions older than 1 hour"""
    import asyncio
    while True:
        try:
            await asyncio.sleep(300)  # Check every 5 minutes
            
            cutoff_time = datetime.utcnow() - timedelta(hours=1)
            sessions_to_remove = [
                session_id for session_id, state in session_store.items()
                if state.is_terminal() and state.last_updated and state.last_updated < cutoff_time
            ]
            
            for session_id in sessions_to_remove:
                del session_store[session_id]
                logger.info(f"Cleaned up old session: {session_id}")
            
            if sessions_to_remove:
                logger.info(f"Cleaned up {len(sessions_to_remove)} old sessions")
        except Exception as e:
            logger.error(f"Error in cleanup_old_sessions: {e}", exc_info=True)
            await asyncio.sleep(300)  # Wait before retrying on error


# Cleans up artifact directories older than 1 hour to prevent disk space buildup.
# Removes entire session directories from artifacts path; logs cleanup count.
def _cleanup_old_artifacts() -> None:
    """Clean up artifacts older than 1 hour"""
    artifacts_path = Path(settings.asset_store).resolve()
    
    if not artifacts_path.exists():
        return
    
    try:
        cutoff_time = datetime.utcnow() - timedelta(hours=1)
        items_cleaned = 0
        
        for item in artifacts_path.iterdir():
            if item.is_dir():
                try:
                    creation_time = datetime.utcfromtimestamp(item.stat().st_ctime)
                    if creation_time < cutoff_time:
                        shutil.rmtree(item)
                        items_cleaned += 1
                except Exception as e:
                    logger.warning(f"Error removing {item.name}: {e}")
        
        if items_cleaned > 0:
            logger.info(f"Cleaned up {items_cleaned} old artifact directories")
    except Exception as e:
        logger.error(f"Failed to clean artifacts: {e}", exc_info=True)


# ============================================================================
# API Endpoint
# ============================================================================

# POST /api/build: starts new build for place_id (no caching - always fresh generation).
# Creates session, stores state, starts background task; returns 202 Accepted with session_id for SSE polling.
@router.post("/build", response_model=BuildResponse, status_code=202)
async def start_build(
    request: BuildRequest,
    background_tasks: BackgroundTasks,
    api_key: str = Depends(verify_api_key)
) -> BuildResponse:
    """
    Start a new build for a place_id.
    
    No caching - every request generates a fresh landing page.
    """
    logger.info(f"POST /api/build received for place_id: {request.place_id}")
    
    # Clean old artifacts
    _cleanup_old_artifacts()
    
    # Generate session
    session_id = str(uuid.uuid4())
    session_store[session_id] = BuildState(session_id)
    
    # Set render prefs
    render_prefs = request.render_prefs.model_dump() if request.render_prefs else _get_default_render_prefs()
    
    # Start background build (no caching - always fresh)
    background_tasks.add_task(_run_build_sync, session_id, request.place_id, render_prefs)
    logger.info(f"Background task started for session {session_id}")
    
    return BuildResponse(session_id=session_id)

