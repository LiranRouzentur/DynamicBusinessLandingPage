

from fastapi import APIRouter, HTTPException, BackgroundTasks
from app.models.schemas import BuildRequest, BuildResponse
from app.models.errors import ApplicationError, ErrorCode
from app.core.cache import cache_manager
from app.core.google_fetcher import google_fetcher
from app.core.artifact_store import artifact_store
from app.core.state_machine import BuildState, BuildPhase
from app.agents.orchestrator import orchestrate_build
import uuid
import asyncio

router = APIRouter()

# In-memory session store (in production, use Redis or similar)
session_store = {}


def _run_build_sync(session_id: str, place_id: str, render_prefs: dict):
    """Wrapper to run async function in sync context"""
    asyncio.run(_run_build(session_id, place_id, render_prefs))

async def _run_build(session_id: str, place_id: str, render_prefs: dict):
    print(f"[BUILD] Build started for session {session_id}, place {place_id}", flush=True)
    state = session_store.get(session_id)
    if not state:
        print(f"[BUILD] ERROR: Session {session_id} not found in store", flush=True)
        return
    
    try:
        # Start: Initial event
        state.log_event(BuildPhase.FETCHING, "Connecting to Google Places API...")
        
        # Fetch from Google
        print(f"[BUILD] Session {session_id}: Calling google_fetcher.fetch_place({place_id})...", flush=True)
        try:
            place_data = await google_fetcher.fetch_place(place_id)
            print(f"[BUILD] Session {session_id}: google_fetcher returned successfully")
            
            # Update with fetched data details
            photos_count = len(place_data.photos) if place_data.photos else 0
            reviews_count = len(place_data.reviews) if place_data.reviews else 0
            business_name = place_data.place.name if place_data.place else "Unknown"
            
            state.log_event(BuildPhase.FETCHING, f"✓ Fetched '{business_name}' - {photos_count} photos, {reviews_count} reviews")
            print(f"Session {session_id}: Place data fetched successfully for {business_name}")
            
        except ApplicationError as e:
            print(f"Session {session_id}: Google Places API error - {str(e)}")
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
                "allow_external_cdns": False,
                "max_reviews": 6
            }
        
        state.log_event(BuildPhase.ORCHESTRATING, "Setting up AI workflow...")
        
        # Run orchestrator
        state.log_event(BuildPhase.GENERATING, "Selecting design template...")
        
        try:
            print(f"Session {session_id}: Running orchestrator...")
            orchestrator_result = await orchestrate_build(place_dict, render_prefs, state)
            print(f"Session {session_id}: Orchestrator completed")
            
            # Validate orchestrator result
            if not orchestrator_result or "bundle" not in orchestrator_result:
                raise ApplicationError(
                    code=ErrorCode.ORCHESTRATION_ERROR,
                    message="Orchestrator failed to produce a valid bundle",
                    retryable=True,
                    hint="The AI generation process encountered an issue. Please try again."
                )
            
        except ApplicationError as e:
            print(f"Session {session_id}: Orchestration error - {str(e)}")
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
        
        print(f"Session {session_id}: Normalized bundle keys: {list(bundle.keys())}")
        
        # Validate bundle structure
        required_keys = ["index_html", "styles_css", "app_js"]
        missing_keys = [key for key in required_keys if key not in bundle]
        
        if missing_keys:
            print(f"Session {session_id}: Bundle keys: {list(bundle.keys()) if hasattr(bundle, 'keys') else 'N/A'}")
            print(f"Session {session_id}: Missing keys: {missing_keys}")
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
        print(f"Session {session_id}: Saving artifacts...")
        try:
            artifact_store.save_bundle(
                session_id=session_id,
                index_html=bundle["index_html"],
                styles_css=bundle["styles_css"],
                app_js=bundle["app_js"]
            )
            print(f"Session {session_id}: Artifacts saved")
            
        except Exception as e:
            print(f"Session {session_id}: Artifact save error - {str(e)}")
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
        print(f"Session {session_id}: Build complete! Terminal state: {state.is_terminal()}")
        
        # Cache the session_id by place_id
        try:
            cache_manager.set(
                place_id=place_id,
                data={"session_id": session_id, "bundle": bundle},
                payload_hash=None
            )
            print(f"Session {session_id}: Session cached")
        except Exception as e:
            print(f"Session {session_id}: Cache error (non-fatal) - {str(e)}")
            # Non-fatal error, don't fail the build
        
    except ApplicationError as e:
        print(f"Session {session_id}: ApplicationError - {str(e)}")
        error_msg = f"✗ {e.message}"
        if e.hint:
            error_msg += f" - {e.hint}"
        state.log_event(BuildPhase.ERROR, error_msg)
        state.metadata["error"] = e.model_dump()
        state.metadata["success"] = False
        print(f"Session {session_id}: Terminal state: {state.is_terminal()}")
        
    except Exception as e:
        print(f"Session {session_id}: Unexpected Exception - {str(e)}")
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
        print(f"Session {session_id}: Terminal state: {state.is_terminal()}")


@router.post("/build", response_model=BuildResponse, status_code=202)
async def start_build(
    request: BuildRequest,
    background_tasks: BackgroundTasks
) -> BuildResponse:
    """
    Start or replay a build for a place_id.
    
    Product.md > Section 4, lines 663-697
    
    Flow (Product.md lines 635-642):
    1. Client sends POST /api/build with place_id
    2. Backend checks cache by place_id
    3. If cached → return cached session_id
    4. If not → fetch from Google, run orchestrator, cache, return new session_id
    """
    print(f"\n[ENDPOINT] POST /api/build received for place_id: {request.place_id}", flush=True)
    
    # Check cache first
    cached_data = cache_manager.get(request.place_id)
    
    if cached_data:
        # Return cached session_id
        session_id = cached_data.get("session_id", str(uuid.uuid4()))
        return BuildResponse(
            session_id=session_id,
            cached=True
        )
    
    # Generate new session ID
    session_id = str(uuid.uuid4())
    
    # Initialize state
    state = BuildState(session_id)
    session_store[session_id] = state
    
    # Set default render_prefs if not provided
    render_prefs = request.render_prefs.model_dump() if request.render_prefs else {
        "language": "en",
        "direction": "ltr",
        "allow_external_cdns": False,
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

