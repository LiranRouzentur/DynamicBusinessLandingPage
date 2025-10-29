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
    
    # Load bundle from artifact store
    bundle = artifact_store.load_bundle(session_id)
    if not bundle:
        raise HTTPException(status_code=404, detail="Bundle not found")
    
    # Check if should inline CSS/JS
    should_inline = artifact_store.should_inline(bundle)
    
    # Get base URL for assets
    base_url = f"/api/result/{session_id}"
    assets_base = f"/assets/{session_id}"
    
    # Prepare HTML response
    html = bundle["index_html"]
    
    if should_inline:
        # Inline CSS and JS
        html = html.replace("</head>", f"<style>\n{bundle['styles_css']}\n</style></head>")
        html = html.replace("</body>", f"<script>\n{bundle['app_js']}\n</script></body>")
    else:
        # Update existing href/src attributes to point to correct asset paths
        # Update CSS link href - handle any attribute order
        html = re.sub(
            r'(<link[^>]*href=["\'])([^"\']*styles\.css)(["\'][^>]*>)',
            fr'\g<1>{assets_base}/styles.css\g<3>',
            html,
            flags=re.IGNORECASE
        )
        # Update JS script src
        html = re.sub(
            r'(<script[^>]*src=["\'])([^"\']*app\.js)(["\'][^>]*>)',
            fr'\g<1>{assets_base}/app.js\g<3>',
            html,
            flags=re.IGNORECASE
        )
    
    return Response(
        content=html,
        media_type="text/html",
        headers={
            "Cache-Control": "public, max-age=3600",
            "X-Content-Type-Options": "nosniff"
        }
    )

