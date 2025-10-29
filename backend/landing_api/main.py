"""FastAPI application entry point"""

import os
import sys
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from landing_api.core.config import settings
from landing_api.api import build, result, progress, events

# Configure logging early with force=True to override any existing config
logging.basicConfig(
    level=logging.DEBUG,  # Set to DEBUG to see all logs
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    force=True,
    handlers=[
        logging.StreamHandler(sys.stdout)  # Explicitly use stdout handler
    ]
)
# Ensure stdout is unbuffered for immediate output
sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)

logger = logging.getLogger(__name__)
# Ensure handler level is also DEBUG
for handler in logger.handlers:
    handler.setLevel(logging.DEBUG)

# CRITICAL: Configure uvicorn's loggers to use DEBUG level
logging.getLogger("uvicorn").setLevel(logging.DEBUG)
logging.getLogger("uvicorn.access").setLevel(logging.DEBUG)
logging.getLogger("uvicorn.error").setLevel(logging.DEBUG)

# Create FastAPI app
app = FastAPI(
    title=settings.api_title,
    version=settings.api_version,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    """Log startup diagnostic information"""
    logger.info("=" * 60)
    logger.info("BACKEND SERVICE STARTING")
    logger.info("=" * 60)
    logger.info(f"PID: {os.getpid()}")
    logger.info(f"Python: {sys.executable}")
    logger.info(f"Module: {__file__}")
    logger.info(f"CWD: {os.getcwd()}")
    logger.info(f"Python Path[0]: {sys.path[0]}")
    logger.info("=" * 60)


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("Shutting down backend service...")
    try:
        from landing_api.core.agents_client import agents_client
        await agents_client.close()
    except Exception as e:
        logger.warning(f"Error during shutdown: {e}")
    try:
        from landing_api.core.google_fetcher import google_fetcher
        await google_fetcher.close()
    except Exception as e:
        logger.warning(f"Error closing google_fetcher: {e}")
    logger.info("Backend service shutdown complete")


@app.get("/")
async def root():
    """Health check endpoint"""
    return {"status": "healthy", "version": settings.api_version}


@app.get("/health")
async def health():
    """Health check for monitoring"""
    return {"status": "healthy"}


# Register API routes
app.include_router(build.router, prefix="/api", tags=["build"])
app.include_router(result.router, prefix="/api", tags=["result"])
app.include_router(progress.router, prefix="/sse", tags=["progress"])
app.include_router(events.router, prefix="/api", tags=["events"])

# Add asset serving route
from fastapi.responses import FileResponse
from pathlib import Path

@app.get("/assets/{session_id}/{file_path:path}")
async def serve_asset(session_id: str, file_path: str):
    """Serve assets from the artifacts folder"""
    from landing_api.core.config import settings
    from fastapi import HTTPException
    
    asset_path = Path(settings.asset_store) / session_id / file_path
    
    # Security check: ensure path is within session directory
    try:
        asset_path.resolve().relative_to(Path(settings.asset_store).resolve())
    except ValueError:
        raise HTTPException(status_code=403, detail="Access denied")
    
    if not asset_path.exists() or not asset_path.is_file():
        raise HTTPException(status_code=404, detail="Asset not found")
    
    # Determine media type
    media_type = "application/octet-stream"
    if file_path.endswith(".css"):
        media_type = "text/css"
    elif file_path.endswith(".js"):
        media_type = "application/javascript"
    elif file_path.endswith((".jpg", ".jpeg")):
        media_type = "image/jpeg"
    elif file_path.endswith(".png"):
        media_type = "image/png"
    elif file_path.endswith(".webp"):
        media_type = "image/webp"
    
    return FileResponse(
        asset_path,
        media_type=media_type,
        headers={
            "Cache-Control": "public, max-age=31536000, immutable" if file_path.endswith((".webp", ".jpg", ".jpeg", ".png")) else "public, max-age=3600"
        }
    )

