"""Main entry point for new agents service"""
import os
import sys
import logging
import httpx
import asyncio
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any, Optional, Callable
from dotenv import load_dotenv
from agents.orchestrator.orchestrator_agent import OrchestratorAgent

# Load .env
_env_path = Path(__file__).resolve().parent.parent / '.env'
load_dotenv(_env_path)

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    force=True
)
logger = logging.getLogger(__name__)

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
    render_prefs: Optional[Dict[str, Any]] = {}
    interactivity_tier: Optional[str] = "enhanced"
    max_attempts: Optional[int] = 3
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


def _create_event_callback(session_id: str) -> Callable[[str, str], None]:
    """Create an event callback that sends events to backend"""
    def event_callback(phase: str, message: str):
        """Event callback for progress - sends to backend and logs locally"""
        logger.info(f"[{phase}] {message}")
        # Send to backend asynchronously (fire and forget)
        import threading
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
        
        # Always run in a separate thread to avoid blocking
        thread = threading.Thread(target=run_in_thread, daemon=True)
        thread.start()
    
    return event_callback


@app.post("/build")
async def build(build_request: BuildRequest):
    """
    Build landing page using new agent structure
    """
    try:
        orchestrator = OrchestratorAgent()
        
        # Create event callback that sends events to backend
        event_callback = _create_event_callback(build_request.session_id)
        
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
        
        if not result["success"]:
            raise HTTPException(
                status_code=500,
                detail=result.get("error", "Build failed")
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
        
        return {
            "session_id": build_request.session_id,
            "success": True,
            "bundle": bundle_data,
            "qa_report": result.get("qa_report"),
            "mapper_out": result.get("mapper_out")
        }
        
    except Exception as e:
        logger.exception("Build failed")
        raise HTTPException(
            status_code=500,
            detail=f"Build failed: {str(e)}"
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

