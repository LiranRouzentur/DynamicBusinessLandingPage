"""GET /api/result/{sessionId} endpoint"""

from fastapi import APIRouter, HTTPException, Response
from landing_api.core.artifact_store import artifact_store
from landing_api.core.state_machine import BuildPhase
from landing_api.api.build import session_store
from landing_api.core.config import settings
import os
import re

router = APIRouter()


@router.get("/result/{session_id}")
async def get_result(session_id: str) -> Response:
    """
    Get the generated landing page bundle.
    Returns index.html with inlined or linked CSS/JS
    """
    # Get state
    state = session_store.get(session_id)
    if not state:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Check if READY
    if state.phase != BuildPhase.READY:
        # Still building - could return 425 Too Early or 404
        raise HTTPException(
            status_code=404, 
            detail=f"Build not ready. Current phase: {state.phase}"
        )
    
    # Load the HTML from artifact store (now just one field/file)
    html = artifact_store.load_html(session_id)
    if not html:
        raise HTTPException(status_code=404, detail="Bundle not found")
    return Response(
        content=html,
        media_type="text/html",
        headers={
            "Cache-Control": "public, max-age=3600",
            "X-Content-Type-Options": "nosniff"
        }
    )

