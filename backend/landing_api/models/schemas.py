"""API request/response schemas"""

from typing import Optional, List
from pydantic import BaseModel, Field


class RenderPrefs(BaseModel):
    """Rendering preferences"""
    language: str = "en"
    direction: str = "ltr"
    brand_colors: Optional[dict] = None
    font_stack: str = "system-ui"
    allow_external_cdns: bool = True
    max_reviews: int = 6


class BuildRequest(BaseModel):
    """POST /api/build request"""
    place_id: str = Field(..., description="Google Maps place_id")
    render_prefs: Optional[RenderPrefs] = None


class BuildResponse(BaseModel):
    """POST /api/build response
    
    Note: Caching is disabled in local development.
    The 'cached' field always returns False.
    """
    session_id: str
    cached: bool = False  # Always False in local dev (caching disabled)


class ProgressEvent(BaseModel):
    """SSE progress event"""
    ts: str
    session_id: str
    phase: str = Field(..., description="FETCHING|ORCHESTRATING|GENERATING|QA|READY|ERROR")
    step: str
    detail: str
    progress: float = Field(ge=0.0, le=1.0)


class ErrorResponse(BaseModel):
    """Error response"""
    error_id: str
    code: str
    message: str
    hint: Optional[str] = None
    retryable: bool = False
    session_id: Optional[str] = None


