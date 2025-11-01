"""FastAPI application entry point"""

import os
import sys
import logging
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from landing_api.core.config import settings
from landing_api.api import build, result, progress, events, mcp

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

# Set up static assets path early
assets_path = Path(__file__).parent.parent / "assets"
assets_path = assets_path.resolve()  # Convert to absolute path

# Define route handler for logo EARLY (before mounts) to ensure it takes precedence
@app.get("/assets/images/logo.png")
async def get_logo():
    """Serve the logo image - defined early to take precedence over static mount"""
    logo_path = assets_path / "images" / "logo.png"
    if logo_path.exists():
        return FileResponse(str(logo_path), media_type="image/png")
    logger.warning(f"Logo not found at: {logo_path}")
    raise HTTPException(status_code=404, detail="Logo not found")


@app.on_event("startup")
async def startup_event():
    """Log startup diagnostic information and start background tasks"""
    import asyncio
    from landing_api.api.build import cleanup_old_sessions
    
    logger.info("=" * 60)
    logger.info("BACKEND SERVICE STARTING")
    logger.info("=" * 60)
    logger.info(f"PID: {os.getpid()}")
    logger.info(f"Python: {sys.executable}")
    logger.info(f"Module: {__file__}")
    logger.info(f"CWD: {os.getcwd()}")
    logger.info(f"Python Path[0]: {sys.path[0]}")
    logger.info("=" * 60)
    
    # Start background cleanup task
    asyncio.create_task(cleanup_old_sessions())
    logger.info("✓ Background cleanup task started")


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
app.include_router(mcp.router, prefix="/api", tags=["mcp"])

# Mount static assets directory for other files (logo.png is handled by route handler above)
if assets_path.exists():
    try:
        app.mount("/assets", StaticFiles(directory=str(assets_path)), name="assets")
        logger.info(f"Static assets mounted from: {assets_path}")
    except Exception as e:
        logger.error(f"Failed to mount static assets: {e}", exc_info=True)
else:
    logger.warning(f"Assets directory not found at: {assets_path}")

