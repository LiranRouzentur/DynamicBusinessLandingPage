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

# Configure logging - console only by default, file logging optional
log_to_file = os.getenv("LOG_TO_FILE", "false").lower() == "true"
handlers = [logging.StreamHandler(sys.stdout)]

if log_to_file:
    log_dir = Path(__file__).resolve().parent.parent.parent / "logs"
    log_dir.mkdir(exist_ok=True)
    log_file = log_dir / "agents.log"
    handlers.append(logging.FileHandler(log_file, mode='a', encoding='utf-8'))

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    force=True,
    handlers=handlers
)

# Force immediate flush on all handlers for better debugging
for handler in logging.root.handlers:
    handler.flush()

logger = logging.getLogger(__name__)
if log_to_file:
    logger.info(f"[AGENTS] Logging to file: {log_file}")
else:
    logger.info("[AGENTS] Logging to console only")

# Backend URL for sending events
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

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
    stop_after: Optional[str] = None  # "mapper", "generator", or "validator" for testing


@app.get("/health")
async def health():
    """Health check"""
    return {"status": "healthy", "service": "new-agents"}


async def _send_event_to_backend(session_id: str, phase: str, detail: str) -> None:
    """Send event to backend /api/events endpoint"""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
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


# Thread pool for event callbacks to prevent thread accumulation
_event_thread_pool = None
_event_thread_lock = threading.Lock()

def _get_event_thread_pool():
    """Get or create thread pool for event callbacks"""
    global _event_thread_pool
    if _event_thread_pool is None:
        from concurrent.futures import ThreadPoolExecutor
        _event_thread_pool = ThreadPoolExecutor(max_workers=5, thread_name_prefix="event-callback")
    return _event_thread_pool

def _create_event_callback(session_id: str) -> Callable[[str, str], None]:
    """Create an event callback that sends events to backend"""
    def event_callback(phase: str, message: str):
        """Event callback for progress - sends to backend and logs locally"""
        logger.info(f"[{phase}] {message}")
        # Send to backend asynchronously (fire and forget) using thread pool
        def run_in_thread():
            """Run async function in a new thread with its own event loop"""
            new_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(new_loop)
            try:
                new_loop.run_until_complete(_send_event_to_backend(session_id, phase, message))
            except Exception as e:
                logger.debug(f"Event sending failed (non-critical): {e}")
            finally:
                new_loop.close()
        
        # Use thread pool to prevent thread accumulation
        try:
            pool = _get_event_thread_pool()
            pool.submit(run_in_thread)
        except Exception as e:
            logger.warning(f"Failed to submit event callback to thread pool: {e}")
            # Fallback to direct thread if pool fails
        thread = threading.Thread(target=run_in_thread, daemon=True)
        thread.start()
    
    return event_callback


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
            stop_after=build_request.stop_after,
            session_id=build_request.session_id  # Pass session_id for proper artifact storage
        )
        
        # Handle test mode (stop_after parameter)
        if result.get("test_mode"):
            return {
                "session_id": build_request.session_id,
                "success": True,
                "test_mode": True,
                "stopped_after": result.get("stopped_after"),
                "mapper_out": result.get("mapper_out"),
                "generator_out": result.get("generator_out"),
                "validator_result": result.get("validator_result"),
                "orchestration_log": result.get("orchestration_log")
            }
        
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
        
        # Read bundle files from workdir (before zipping)
        bundle_data = {}
        if result.get("success"):
            # The orchestrator should return bundle content directly, but if not, try to read from expected location
            # Check if bundle content is in the result first
            if "bundle" in result:
                bundle_data = result["bundle"]
            elif result.get("bundle_path"):
                # Fallback: try to extract from zip or read from workdir
                bundle_path = Path(result["bundle_path"])
                # If it's a zip, extract it; otherwise read from directory
                if bundle_path.suffix == ".zip":
                    import tempfile
                    import zipfile
                    with tempfile.TemporaryDirectory() as tmpdir:
                        with zipfile.ZipFile(bundle_path, 'r') as zip_ref:
                            zip_ref.extractall(tmpdir)
                            extracted_dir = Path(tmpdir)
                            bundle_data = {
                                "index_html": (extracted_dir / "index.html").read_text(encoding="utf-8") if (extracted_dir / "index.html").exists() else "",
                                "styles_css": (extracted_dir / "styles.css").read_text(encoding="utf-8") if (extracted_dir / "styles.css").exists() else "",
                                "app_js": (extracted_dir / "script.js").read_text(encoding="utf-8") if (extracted_dir / "script.js").exists() else ""
                            }
                else:
                    # Assume it's a directory
                    workdir = bundle_path
                    bundle_data = {
                        "index_html": (workdir / "index.html").read_text(encoding="utf-8") if (workdir / "index.html").exists() else "",
                        "styles_css": (workdir / "styles.css").read_text(encoding="utf-8") if (workdir / "styles.css").exists() else "",
                        "app_js": (workdir / "script.js").read_text(encoding="utf-8") if (workdir / "script.js").exists() else ""
                    }
        
        # Normalize bundle to backend format - if we have html field, use it
        # Prioritize html field from orchestrator result
        if result.get("html"):
            # Single-file HTML mode - backend expects html field
            final_bundle = {"html": result["html"]}
            if "meta" in result:
                final_bundle["meta"] = result["meta"]
        elif bundle_data:
            # Multi-file mode - backend expects index_html, styles_css, app_js
            final_bundle = bundle_data
        else:
            # No bundle data found
            final_bundle = {}
        
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

