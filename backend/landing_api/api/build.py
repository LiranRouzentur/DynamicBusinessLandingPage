"""Build API endpoint - refactored for better maintainability"""
from fastapi import APIRouter, HTTPException, BackgroundTasks
from landing_api.models.schemas import BuildRequest, BuildResponse
from landing_api.models.errors import ApplicationError, ErrorCode
from landing_api.core.google_fetcher import google_fetcher
from landing_api.core.artifact_store import artifact_store
from landing_api.core.state_machine import BuildState, BuildPhase
from landing_api.core.agents_client import agents_client
from landing_api.core.config import settings
import uuid
import asyncio
import shutil
import logging
import json
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime, timedelta

router = APIRouter()
logger = logging.getLogger(__name__)

# In-memory session store (in production, use Redis or similar)
session_store = {}


# ============================================================================
# Helper Functions
# ============================================================================

def _get_default_render_prefs() -> Dict[str, Any]:
    """Get default rendering preferences"""
    return {
        "language": "en",
        "direction": "ltr",
        "allow_external_cdns": True,
        "max_reviews": 6
    }


def _calculate_data_richness(place_data: Dict[str, Any]) -> Dict[str, bool]:
    """Calculate data richness flags from place data"""
    status = place_data.get("status", {})
    return {
        "has_photos": len(place_data.get("photos", [])) > 0,
        "has_reviews": len(place_data.get("reviews", [])) > 0,
        "has_hours": len(status.get("weekday_descriptions", [])) > 0,
        "has_site": place_data.get("website_url") is not None
    }


def _normalize_bundle_keys(bundle: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize bundle keys from 'file.ext' to 'file_ext' format"""
    key_mapping = {
        "index.html": "index_html",
        "styles.css": "styles_css",
        "app.js": "app_js"
    }
    
    for old_key, new_key in key_mapping.items():
        if old_key in bundle and new_key not in bundle:
            bundle[new_key] = bundle.pop(old_key)
    
    return bundle


def _validate_bundle(bundle: Dict[str, Any], session_id: str) -> None:
    """Validate bundle has all required files"""
    required_keys = ["index_html", "styles_css", "app_js"]
    missing_keys = [key for key in required_keys if key not in bundle]
    
    if missing_keys:
        logger.error(f"Session {session_id}: Missing bundle keys: {missing_keys}")
        raise ApplicationError(
            code=ErrorCode.BUNDLE_INVALID,
            message=f"Bundle missing required files: {', '.join(missing_keys)}",
            retryable=False,
            hint="The generated bundle is incomplete. Please report this issue."
        )


def _handle_error(state: BuildState, error: Exception, is_application_error: bool = False) -> None:
    """Handle errors consistently"""
    if is_application_error:
        # Use user-friendly messages from ApplicationError
        error_msg = f"✗ {error.message}"
        if error.hint:
            error_msg += f" {error.hint}"
    else:
        error_msg = "✗ An error occurred. Please try again."
    
    state.log_event(BuildPhase.ERROR, error_msg)
    state.metadata["success"] = False
    state.metadata["error"] = error.model_dump() if is_application_error else {
        "message": str(error),
        "type": type(error).__name__,
        "retryable": True
    }


async def _fetch_place_data(place_id: str, state: BuildState) -> Optional[Dict[str, Any]]:
    """Fetch place data from Google Places API"""
    logger.info(f"[GOOGLE FETCH] Starting fetch for place_id: {place_id}")
    state.log_event(BuildPhase.FETCHING, "Gathering business information...")
    
    try:
        place_data = await google_fetcher.fetch_place(place_id)
        business_name = place_data.get("name") or "this business"
        
        # Build a user-friendly message
        details = []
        photos_count = len(place_data.get("photos", []))
        reviews_count = len(place_data.get("reviews", []))
        
        if photos_count > 0:
            details.append(f"{photos_count} photo{'s' if photos_count != 1 else ''}")
        if reviews_count > 0:
            details.append(f"{reviews_count} review{'s' if reviews_count != 1 else ''}")
        
        if details:
            detail_text = ", ".join(details)
            message = f"✓ Business information retrieved ({detail_text})"
        else:
            message = f"✓ Business information retrieved"
        
        state.log_event(BuildPhase.FETCHING, message)
        logger.info(f"Place data fetched for {business_name}")
        return place_data
        
    except ApplicationError as e:
        _handle_error(state, e, is_application_error=True)
        return None


async def _call_ai_agents(
    session_id: str,
    place_data: Dict[str, Any],
    render_prefs: Dict[str, Any],
    state: BuildState
) -> Optional[Dict[str, Any]]:
    """Call AI agents service to generate landing page"""
    state.log_event(BuildPhase.GENERATING, "Starting page generation...")
    
    data_richness = _calculate_data_richness(place_data)
    
    # Infer category from primary_type or types
    category = place_data.get("primary_type", "business")
    if not category or category == "establishment":
        types = place_data.get("types", [])
        category = types[0] if types else "business"
    
    agents_result = await agents_client.build(
        session_id=session_id,
        business_name=place_data.get("name", "Business"),
        category=category,
        place_data=place_data,
        render_prefs=render_prefs,
        data_richness=data_richness
    )
    
    if not agents_result or not agents_result.get("success"):
        error_msg = agents_result.get("error", "Unknown error") if agents_result else "Service unavailable"
        logger.error(f"Agents service failed: {error_msg}")
        raise ApplicationError(
            code=ErrorCode.ORCHESTRATION_ERROR,
            message=f"AI agents failed: {error_msg}",
            retryable=True,
            hint="The AI generation service encountered an issue. Please try again."
        )
    
    logger.info("Agents service completed successfully")
    return agents_result


async def _process_bundle(
    session_id: str,
    bundle: Dict[str, Any],
    state: BuildState
) -> None:
    """Process and save bundle artifacts"""
    # Normalize keys
    bundle = _normalize_bundle_keys(bundle)
    
    # Validate
    _validate_bundle(bundle, session_id)
    
    state.log_event(BuildPhase.GENERATING, "✓ Page design completed successfully")
    state.log_event(BuildPhase.QA, "Running final quality checks...")
    
    # Save artifacts
    try:
        artifact_store.save_bundle(
            session_id=session_id,
            index_html=bundle["index_html"],
            styles_css=bundle["styles_css"],
            app_js=bundle["app_js"],
            assets=bundle.get("assets")
        )
        state.log_event(BuildPhase.QA, "✓ All quality checks completed")
    except Exception as e:
        logger.error(f"Failed to save artifacts: {e}", exc_info=True)
        raise ApplicationError(
            code=ErrorCode.CACHE_ERROR,
            message=f"Failed to save artifacts: {str(e)}",
            retryable=True,
            hint="Storage issue encountered. Please try again."
        )


# ============================================================================
# Main Build Logic
# ============================================================================

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
        
        logger.info(f"[STEP 2] Calling AI agents...")
        # Step 2: Call AI agents
        state.log_event(BuildPhase.ORCHESTRATING, "Initializing page creation workflow...")
        agents_result = await _call_ai_agents(session_id, place_data, render_prefs, state)
        
        logger.info(f"[STEP 3] Processing bundle...")
        # Step 3: Process bundle
        await _process_bundle(session_id, agents_result["bundle"], state)
        
        # Success
        state.log_event(BuildPhase.READY, "✓ Your landing page is ready to view!")
        state.metadata["success"] = True
        state.metadata["business_name"] = place_data.get("name", "Unknown")
        logger.info(f"Build completed successfully for session {session_id}")
        
    except ApplicationError as e:
        _handle_error(state, e, is_application_error=True)
    except Exception as e:
        logger.exception("Unexpected error in build")
        _handle_error(state, e, is_application_error=False)


def _run_build_sync(session_id: str, place_id: str, render_prefs: dict) -> None:
    """Sync wrapper for background task"""
    # Use print() with flush to bypass logging issues in background tasks
    print(f"\n{'='*80}", flush=True)
    print(f"[BACKGROUND TASK START] Session: {session_id}, Place ID: {place_id}", flush=True)
    print(f"{'='*80}\n", flush=True)
    
    logger.info(f"[BACKGROUND TASK] Starting build for session {session_id}")
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        print("[BACKGROUND TASK] Creating new event loop...", flush=True)
        loop.run_until_complete(_run_build(session_id, place_id, render_prefs))
        print("[BACKGROUND TASK] ✓ Build completed successfully", flush=True)
    except Exception as e:
        print(f"[BACKGROUND TASK] ✗ ERROR: {e}", flush=True)
        logger.error(f"Sync wrapper error: {e}", exc_info=True)
    finally:
        loop.close()


async def cleanup_old_sessions() -> None:
    """Periodically clean up terminal sessions older than 1 hour"""
    while True:
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

@router.post("/build", response_model=BuildResponse, status_code=202)
async def start_build(
    request: BuildRequest,
    background_tasks: BackgroundTasks
) -> BuildResponse:
    """Start a new build for a place_id"""
    logger.info(f"POST /api/build received for place_id: {request.place_id}")
    
    # Clean old artifacts
    _cleanup_old_artifacts()
    
    # Generate session
    session_id = str(uuid.uuid4())
    session_store[session_id] = BuildState(session_id)
    
    # Set render prefs
    render_prefs = request.render_prefs.model_dump() if request.render_prefs else _get_default_render_prefs()
    
    # Start background build
    background_tasks.add_task(_run_build_sync, session_id, request.place_id, render_prefs)
    logger.info(f"Background task started for session {session_id}")
    
    return BuildResponse(session_id=session_id, cached=False)

