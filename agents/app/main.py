"""Main entry point for new agents service"""
import os
import sys
import logging
import httpx
import asyncio
import threading
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any, Optional, Callable
from dotenv import load_dotenv
from app.orchestrator.orchestrator_agent import OrchestratorAgent

# Load .env
_env_path = Path(__file__).resolve().parent.parent / '.env'
load_dotenv(_env_path)

# Configure logging - console only
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    force=True,
    handlers=[logging.StreamHandler(sys.stdout)]
)

# Force immediate flush on all handlers for better debugging
for handler in logging.root.handlers:
    handler.flush()

logger = logging.getLogger(__name__)
logger.info("[AGENTS] Logging to console only")

# Backend URL for sending events
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

# Persistent HTTP client for event sending (reuse connections)
_http_client: Optional[httpx.AsyncClient] = None

# Gets or creates persistent HTTP client for event sending with 5s timeout.
# Reuses connections to backend /api/events endpoint for efficiency.
def _get_http_client() -> httpx.AsyncClient:
    """Get or create persistent HTTP client"""
    global _http_client
    if _http_client is None:
        _http_client = httpx.AsyncClient(timeout=5.0)
    return _http_client

# Background event loop for async operations (created once at startup)
_event_loop: Optional[asyncio.AbstractEventLoop] = None
_event_thread: Optional[threading.Thread] = None

# Starts background event loop in daemon thread for async event sending without blocking main thread.
# Created once at startup, runs forever until process exit; enables fire-and-forget event emission.
def _start_event_loop():
    """Start background event loop for async operations"""
    global _event_loop, _event_thread
    if _event_loop is None:
        _event_loop = asyncio.new_event_loop()
        _event_thread = threading.Thread(
            target=_event_loop.run_forever,
            daemon=True,
            name="event-loop"
        )
        _event_thread.start()
        logger.info("✓ Background event loop started")

app = FastAPI(
    title="New Agents Service",
    version="1.0.0",
    description="Recreated agents based on markdown specifications"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class BuildRequest(BaseModel):
    """Request to start a build"""
    session_id: str
    place_data: Dict[str, Any]
    business_name: Optional[str] = None
    category: Optional[str] = None
    render_prefs: Optional[Dict[str, Any]] = {}
    data_richness: Optional[Dict[str, bool]] = {}
    interactivity_tier: Optional[str] = "enhanced"
    max_attempts: Optional[int] = 3  # Increased to 3 to handle edge cases
    asset_budget: Optional[int] = 3


# Startup handler: initializes background event loop for async operations.
# Ensures event emission infrastructure is ready before accepting build requests.
@app.on_event("startup")
async def startup_event():
    """Initialize background services"""
    _start_event_loop()
    logger.info("✓ Agents service startup complete")


# Shutdown handler: closes HTTP client and stops background event loop gracefully.
# Ensures proper cleanup of async resources on service termination.
@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    global _http_client, _event_loop
    
    # Close HTTP client
    if _http_client:
        await _http_client.aclose()
        _http_client = None
    
    # Stop event loop
    if _event_loop:
        _event_loop.call_soon_threadsafe(_event_loop.stop)
        _event_loop = None
    
    logger.info("✓ Agents service shutdown complete")


# Health check endpoint for monitoring and service discovery.
# Returns 200 OK with service name; used by backend to verify agents service availability.
@app.get("/health")
async def health():
    """Health check"""
    return {"status": "healthy", "service": "new-agents"}


# Sends progress event to backend /api/events endpoint via persistent HTTP client.
# Non-blocking operation - logs warning if fails but doesn't break build; enables real-time SSE updates.
async def _send_event_to_backend(session_id: str, phase: str, detail: str) -> None:
    """Send event to backend /api/events endpoint"""
    try:
        client = _get_http_client()
        payload = {
            "session_id": session_id,
            "phase": phase,
            "detail": detail
        }
        response = await client.post(
            f"{BACKEND_URL}/api/events",
            json=payload
        )
        if response.status_code != 200:
            logger.warning(f"Failed to send event to backend: {response.status_code}")
    except Exception as e:
        # Don't fail the build if event sending fails
        logger.debug(f"Event sending failed (non-critical): {e}")


# Creates event callback closure that logs events and forwards to backend via background event loop.
# Uses asyncio.run_coroutine_threadsafe for thread-safe async execution without blocking orchestrator.
def _create_event_callback(session_id: str) -> Callable[[str, str], None]:
    """Create an event callback that sends events to backend"""
    def event_callback(phase: str, message: str):
        """Event callback for progress - sends to backend and logs locally"""
        logger.info(f"[{phase}] {message}")
        
        # Send to backend asynchronously using persistent event loop
        # This avoids creating new event loops and threads for each event
        try:
            if _event_loop and _event_loop.is_running():
                # Submit coroutine to background event loop (fire and forget)
                asyncio.run_coroutine_threadsafe(
                    _send_event_to_backend(session_id, phase, message),
                    _event_loop
                )
            else:
                logger.warning("Event loop not running, event not sent")
        except Exception as e:
            logger.debug(f"Event sending failed (non-critical): {e}")
    
    return event_callback


# Main build endpoint: orchestrates mapper → generator → validators workflow.
# Creates session-specific artifact directory and event callback; returns {success, html, meta}.
@app.post("/build")
async def build(build_request: BuildRequest):
    """
    Build landing page using new agent structure
    """
    logger.info(
        f"[BUILD] Starting build | "
        f"session_id={build_request.session_id} | "
        f"business={build_request.business_name} | "
        f"tier={build_request.interactivity_tier} | "
        f"max_attempts={build_request.max_attempts}"
    )
    
    try:
        orchestrator = OrchestratorAgent()
        
        # Create event callback that sends events to backend
        event_callback = _create_event_callback(build_request.session_id)
        
        logger.info(f"[BUILD] Calling orchestrator.orchestrate...")
        result = await orchestrator.orchestrate(
            google_data=build_request.place_data,
            interactivity_tier=build_request.interactivity_tier,
            max_attempts=build_request.max_attempts,
            asset_budget=build_request.asset_budget,
            event_callback=event_callback,
            session_id=build_request.session_id  # Pass session_id for proper artifact storage
        )
        
        logger.info(
            f"[BUILD] Orchestrator completed | "
            f"success={result.get('success')} | "
            f"session_id={build_request.session_id} | "
            f"has_html={bool(result.get('html'))} | "
            f"has_bundle_path={bool(result.get('bundle_path'))}"
        )
        
        # Force flush logs before returning
        for handler in logging.root.handlers:
            handler.flush()
        
        if not result.get("success"):
            error_msg = result.get("error", "Build failed")
            logger.error(
                f"[BUILD] Build failed | "
                f"session_id={build_request.session_id} | "
                f"error={error_msg}"
            )
            # Force flush before raising
            for handler in logging.root.handlers:
                handler.flush()
            raise HTTPException(
                status_code=500,
                detail=error_msg
            )
        
        # Extract bundle from orchestrator result
        # Orchestrator always returns single-file HTML in result["html"]
        final_bundle = {}
        if result.get("html"):
            final_bundle = {"html": result["html"]}
            if "meta" in result:
                final_bundle["meta"] = result["meta"]
        
        response_data = {
            "session_id": build_request.session_id,
            "success": True,
            "bundle": final_bundle,
            "qa_report": result.get("qa_report"),
            "mapper_out": result.get("mapper_out")
        }
        
        logger.info(
            f"[BUILD] Returning response | "
            f"session_id={build_request.session_id} | "
            f"bundle_keys={list(final_bundle.keys())} | "
            f"has_html={bool(final_bundle.get('html'))}"
        )
        
        # Force flush before returning
        for handler in logging.root.handlers:
            handler.flush()
        
        return response_data
        
    except Exception as e:
        error_type = type(e).__name__
        error_msg = str(e)
        logger.error(
            f"[BUILD] Build exception | "
            f"session_id={build_request.session_id} | "
            f"error_type={error_type} | "
            f"error={error_msg}",
            exc_info=True
        )
        # Force flush logs immediately
        for handler in logging.root.handlers:
            handler.flush()
        raise HTTPException(
            status_code=500,
            detail=f"Build failed: {error_msg}"
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=8002,  # Different port from old service
        log_level="debug",
        reload=True
    )

