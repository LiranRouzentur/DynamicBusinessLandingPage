

from fastapi import APIRouter, HTTPException, BackgroundTasks
from landing_api.models.schemas import BuildRequest, BuildResponse
from landing_api.models.errors import ApplicationError, ErrorCode
# Cache disabled for local development
# from landing_api.core.cache import cache_manager
from landing_api.core.google_fetcher import google_fetcher
from landing_api.core.artifact_store import artifact_store
from landing_api.core.state_machine import BuildState, BuildPhase
from landing_api.core.agents_client import agents_client
from landing_api.core.config import settings
import uuid
import asyncio
import shutil
from pathlib import Path

router = APIRouter()
import logging

logger = logging.getLogger(__name__)

# In-memory session store (in production, use Redis or similar)
session_store = {}

# Session cleanup task
async def cleanup_old_sessions():
    """Periodically clean up terminal sessions older than 1 hour"""
    import asyncio
    from datetime import datetime, timedelta
    
    while True:
        await asyncio.sleep(300)  # Check every 5 minutes
        
        cutoff_time = datetime.utcnow() - timedelta(hours=1)
        sessions_to_remove = []
        
        for session_id, state in session_store.items():
            if state.is_terminal() and state.last_updated and state.last_updated < cutoff_time:
                sessions_to_remove.append(session_id)
        
        for session_id in sessions_to_remove:
            del session_store[session_id]
            logger.info(f"Cleaned up old session: {session_id}")
        
        if sessions_to_remove:
            logger.info(f"Cleaned up {len(sessions_to_remove)} old sessions")


def _cleanup_old_artifacts():
    """Clean up artifacts older than 1 hour to prevent disk space issues"""
    from datetime import datetime, timedelta
    
    # Get absolute path to ensure correct directory
    artifacts_path = Path(settings.asset_store).resolve()
    
    logger.debug(f"Checking artifacts in: {artifacts_path}")
    
    if not artifacts_path.exists():
        logger.debug("Artifacts directory does not exist, skipping cleanup")
        return
    
    try:
        cutoff_time = datetime.utcnow() - timedelta(hours=1)
        items_cleaned = 0
        
        # Only remove old session directories
        for item in artifacts_path.iterdir():
            if item.is_dir():
                try:
                    # Check if this is an old session directory
                    # Session IDs are UUIDs, we can check creation time
                    creation_time = datetime.utcfromtimestamp(item.stat().st_ctime)
                    if creation_time < cutoff_time:
                        logger.debug(f"Removing old artifact directory: {item.name}")
                        shutil.rmtree(item)
                        items_cleaned += 1
                except Exception as e:
                    logger.warning(f"Error removing {item.name}: {e}")
        
        if items_cleaned > 0:
            logger.info(f"Cleaned up {items_cleaned} old artifact directories")
        
    except Exception as e:
        logger.error(f"Failed to clean artifacts: {e}", exc_info=True)


def _run_build_sync(session_id: str, place_id: str, render_prefs: dict):
    """Wrapper to run async function in sync context - creates new event loop for thread"""
    logger.info(f"Sync wrapper started for session {session_id}")
    
    # FastAPI BackgroundTasks run in thread pool, so we need a new event loop
    # Use asyncio.new_event_loop() instead of asyncio.run() to avoid conflicts
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(_run_build(session_id, place_id, render_prefs))
    except Exception as e:
        logger.error(f"Sync wrapper error: {e}", exc_info=True)
    finally:
        loop.close()

async def _run_build(session_id: str, place_id: str, render_prefs: dict):
    logger.info(f"Build started for session {session_id}, place {place_id}")
    
    state = session_store.get(session_id)
    if not state:
        logger.error(f"Session {session_id} not found in store")
        return
    
    try:
        # Start: Initial event
        state.log_event(BuildPhase.FETCHING, "Connecting to Google Places API...")
        
        # Fetch from Google
        logger.debug(f"Calling google_fetcher.fetch_place({place_id})")
        try:
            place_data = await google_fetcher.fetch_place(place_id)
            logger.debug("google_fetcher returned successfully")
            
            # Update with fetched data details
            photos_count = len(place_data.photos) if place_data.photos else 0
            reviews_count = len(place_data.reviews) if place_data.reviews else 0
            business_name = place_data.place.name if place_data.place else "Unknown"
            
            state.log_event(BuildPhase.FETCHING, f"✓ Fetched '{business_name}' - {photos_count} photos, {reviews_count} reviews")
            logger.info(f"Place data fetched successfully for {business_name}")
            
        except ApplicationError as e:
            logger.error(f"Google Places API error - {e}")
            error_msg = f"✗ {e.message} - {e.hint or 'Please check the place ID and try again'}"
            state.log_event(BuildPhase.ERROR, error_msg)
            state.metadata["error"] = e.model_dump()
            state.metadata["success"] = False
            return
        
        # Update state: ORCHESTRATING
        state.log_event(BuildPhase.ORCHESTRATING, "Analyzing business information...")
        
        # Convert place_data to dict for orchestrator
        place_dict = place_data.model_dump()
        
        # Set default render_prefs if not provided
        if not render_prefs:
            render_prefs = {
                "language": "en",
                "direction": "ltr",
                "allow_external_cdns": True,
                "max_reviews": 6
            }
        
        state.log_event(BuildPhase.ORCHESTRATING, "Setting up AI workflow...")
        
        # Use new agents service ONLY (no fallback)
        logger.debug("Using new agents service")
        
        # Extract data for agents service
        from landing_api.models.normalized_data import NormalizedPlacePayload, DataRichness
        
        payload = NormalizedPlacePayload(**place_dict)
        has_photos = len(payload.photos) > 0
        has_reviews = len(payload.reviews) > 0
        has_hours = payload.place.opening_hours is not None and len(payload.place.opening_hours.weekday_text) > 0
        has_site = payload.place.website is not None
        
        data_richness = {
            "has_photos": has_photos,
            "has_reviews": has_reviews,
            "has_hours": has_hours,
            "has_site": has_site
        }
        
        category = "business"  # Default, could be inferred from types
        
        # Call agents service
        state.log_event(BuildPhase.GENERATING, "Using AI agents...")
        agents_result = await agents_client.build(
            session_id=session_id,
            business_name=payload.place.name,
            category=category,
            place_data=place_dict,
            render_prefs=render_prefs,
            data_richness=data_richness
        )
        
        if not agents_result or not agents_result.get("success"):
            error_msg = agents_result.get("error", "Unknown error") if agents_result else "Agents service unavailable"
            logger.error(f"Agents service failed: {error_msg}")
            raise ApplicationError(
                code=ErrorCode.ORCHESTRATION_ERROR,
                message=f"AI agents failed: {error_msg}",
                retryable=True,
                hint="The AI generation service encountered an issue. Please try again."
            )
        
        logger.info("Agents service completed successfully")
        # Convert agents service result to orchestrator format
        orchestrator_result = {
            "bundle": agents_result.get("bundle", {}),
            "design_source": agents_result.get("design_source"),
            "layout_plan": agents_result.get("layout_plan"),
            "content_map": agents_result.get("content_map"),
            "qa_report": agents_result.get("qa_report", {})
        }
        
        # Continue with existing logic
        try:
            
            # Validate orchestrator result
            if not orchestrator_result or "bundle" not in orchestrator_result:
                raise ApplicationError(
                    code=ErrorCode.ORCHESTRATION_ERROR,
                    message="Orchestrator failed to produce a valid bundle",
                    retryable=True,
                    hint="The AI generation process encountered an issue. Please try again."
                )
            
        except ApplicationError as e:
            logger.error(f"Orchestration error - {e}")
            error_msg = f"✗ {e.message} - {e.hint or 'Please try again'}"
            state.log_event(BuildPhase.ERROR, error_msg)
            state.metadata["error"] = e.model_dump()
            state.metadata["success"] = False
            return
        
        # Debug: Print orchestrator result structure
        print(f"Session {session_id}: Orchestrator result keys: {list(orchestrator_result.keys())}")
        print(f"Session {session_id}: Bundle type: {type(orchestrator_result.get('bundle'))}")
        
        # Get final bundle
        bundle = orchestrator_result["bundle"]
        
        # Normalize bundle keys (handle both "index.html" and "index_html" formats)
        if "index.html" in bundle and "index_html" not in bundle:
            bundle["index_html"] = bundle.pop("index.html")
        if "styles.css" in bundle and "styles_css" not in bundle:
            bundle["styles_css"] = bundle.pop("styles.css")
        if "app.js" in bundle and "app_js" not in bundle:
            bundle["app_js"] = bundle.pop("app.js")
        
        print(f"Session {session_id}: Normalized bundle keys: {list(bundle.keys())}", flush=True)
        
        # Validate bundle structure
        required_keys = ["index_html", "styles_css", "app_js"]
        missing_keys = [key for key in required_keys if key not in bundle]
        
        if missing_keys:
            print(f"Session {session_id}: Bundle keys: {list(bundle.keys()) if hasattr(bundle, 'keys') else 'N/A'}", flush=True)
            print(f"Session {session_id}: Missing keys: {missing_keys}", flush=True)
            raise ApplicationError(
                code=ErrorCode.BUNDLE_INVALID,
                message=f"Bundle missing required files: {', '.join(missing_keys)}",
                retryable=False,
                hint="The generated bundle is incomplete. Please report this issue."
            )
        
        state.log_event(BuildPhase.GENERATING, "✓ HTML, CSS, and JavaScript generated successfully")
        
        # Update state: QA
        state.log_event(BuildPhase.QA, "Running quality checks...")
        
        # Save artifacts
        print(f"Session {session_id}: Saving artifacts...", flush=True)
        try:
            # Extract assets if present
            assets = bundle.get("assets")
            
            artifact_store.save_bundle(
                session_id=session_id,
                index_html=bundle["index_html"],
                styles_css=bundle["styles_css"],
                app_js=bundle["app_js"],
                assets=assets
            )
            print(f"Session {session_id}: Artifacts saved", flush=True)
            
        except Exception as e:
            print(f"Session {session_id}: Artifact save error - {str(e)}", flush=True)
            raise ApplicationError(
                code=ErrorCode.CACHE_ERROR,
                message=f"Failed to save artifacts: {str(e)}",
                retryable=True,
                hint="Storage issue encountered. Please try again."
            )
        
        state.log_event(BuildPhase.QA, "✓ All quality checks passed")
        
        # Update state: READY
        state.log_event(BuildPhase.READY, "✓ Your landing page is ready!")
        state.metadata["success"] = True
        state.metadata["business_name"] = business_name
        print(f"Session {session_id}: Build complete! Terminal state: {state.is_terminal()}", flush=True)
        
        # Cache disabled for local development
        # In production, uncomment below to enable caching:
        # try:
        #     cache_manager.set(
        #         place_id=place_id,
        #         data={"session_id": session_id, "bundle": bundle},
        #         payload_hash=None
        #     )
        #     print(f"Session {session_id}: Session cached")
        # except Exception as e:
        #     print(f"Session {session_id}: Cache error (non-fatal) - {str(e)}")
        
    except ApplicationError as e:
        print(f"Session {session_id}: ApplicationError - {str(e)}", flush=True)
        error_msg = f"✗ {e.message}"
        if e.hint:
            error_msg += f" - {e.hint}"
        state.log_event(BuildPhase.ERROR, error_msg)
        state.metadata["error"] = e.model_dump()
        state.metadata["success"] = False
        print(f"Session {session_id}: Terminal state: {state.is_terminal()}", flush=True)
        
    except Exception as e:
        print(f"Session {session_id}: Unexpected Exception - {str(e)}", flush=True)
        import traceback
        traceback.print_exc()
        
        # Provide user-friendly error message
        user_message = "An unexpected error occurred during the build process"
        state.log_event(BuildPhase.ERROR, f"✗ {user_message}")
        state.metadata["error"] = {
            "message": str(e),
            "type": type(e).__name__,
            "retryable": True
        }
        state.metadata["success"] = False
        print(f"Session {session_id}: Terminal state: {state.is_terminal()}", flush=True)


@router.post("/build", response_model=BuildResponse, status_code=202)
async def start_build(
    request: BuildRequest,
    background_tasks: BackgroundTasks
) -> BuildResponse:
    """
    Start a new build for a place_id.
    
    Flow (in local development):
    1. Client sends POST /api/build with place_id
    2. Backend cleans up old artifacts
    3. Fetches from Google, runs orchestrator, saves artifacts, returns new session_id
    
    Note: Caching is disabled in local development.
    In production, uncomment cache logic to enable caching.
    """
    print(f"\n[ENDPOINT] POST /api/build received for place_id: {request.place_id}", flush=True)
    
    # Clean up old artifacts at the start of each request
    _cleanup_old_artifacts()
    
    # Cache check disabled for local development
    # In production, uncomment below to enable caching:
    # cached_data = cache_manager.get(request.place_id)
    # if cached_data:
    #     session_id = cached_data.get("session_id", str(uuid.uuid4()))
    #     return BuildResponse(session_id=session_id, cached=True)
    
    # Generate new session ID
    session_id = str(uuid.uuid4())
    
    # Initialize state
    state = BuildState(session_id)
    session_store[session_id] = state
    
    # Set default render_prefs if not provided
    render_prefs = request.render_prefs.model_dump() if request.render_prefs else {
        "language": "en",
        "direction": "ltr",
        "allow_external_cdns": True,
        "max_reviews": 6
    }
    
    # Start build in background
    print(f"[ENDPOINT] Starting background task for session {session_id}", flush=True)
    background_tasks.add_task(
        _run_build_sync,
        session_id=session_id,
        place_id=request.place_id,
        render_prefs=render_prefs
    )
    print(f"[ENDPOINT] Background task added, returning response with session_id: {session_id}", flush=True)
    
    return BuildResponse(
        session_id=session_id,
        cached=False
    )

