"""GET /api/result/{sessionId} endpoint - Product.md lines 698-711"""

from fastapi import APIRouter, HTTPException, Response
from app.core.artifact_store import artifact_store
from app.core.state_machine import BuildPhase
from app.api.build import session_store
from app.core.config import settings
import os

router = APIRouter()


@router.get("/result/{session_id}")
async def get_result(session_id: str) -> Response:
    """
    Get the generated landing page bundle.
    
    Product.md > Section 4, lines 698-711
    Returns index.html with inlined or linked CSS/JS
    
    Ref: Product.md lines 856-858 for artifact storage paths
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
    
    # Load bundle from artifact store
    bundle = artifact_store.load_bundle(session_id)
    if not bundle:
        raise HTTPException(status_code=404, detail="Bundle not found")
    
    # Check if should inline CSS/JS
    should_inline = artifact_store.should_inline(bundle)
    
    # Get base URL for assets
    base_url = f"/assets/{session_id}"
    
    # Prepare HTML response
    html = bundle["index_html"]
    
    if should_inline:
        # Inline CSS and JS
        html = html.replace("</head>", f"<style>\n{bundle['styles_css']}\n</style></head>")
        html = html.replace("</body>", f"<script>\n{bundle['app_js']}\n</script></body>")
    else:
        # Link external files
        html = html.replace("</head>", f'<link rel="stylesheet" href="{base_url}/styles.css"></head>')
        html = html.replace("</body>", f'<script src="{base_url}/app.js"></script></body>')
    
    return Response(
        content=html,
        media_type="text/html",
        headers={
            "Cache-Control": "public, max-age=3600",
            "X-Content-Type-Options": "nosniff"
        }
    )

