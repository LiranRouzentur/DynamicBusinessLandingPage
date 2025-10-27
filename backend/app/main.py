"""FastAPI application entry point - Product.md > Section 9"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api import build, result, progress

# Create FastAPI app
app = FastAPI(
    title=settings.api_title,
    version=settings.api_version,
)

# Configure CORS - Product.md > Section 9
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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

