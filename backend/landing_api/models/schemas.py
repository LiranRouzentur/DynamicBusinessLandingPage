"""API request/response schemas"""

from typing import Optional, List
from pydantic import BaseModel, Field, validator
import re


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
    
    @validator('place_id')
    def validate_place_id(cls, v):
        """
        Validate place_id format to prevent injection attacks.
        
        Google Place IDs follow specific formats:
        - Legacy format: ChIJ... or ChIX... (27+ chars)
        - New API format: places/... (variable length)
        """
        if not v or not isinstance(v, str):
            raise ValueError("place_id must be a non-empty string")
        
        v = v.strip()
        
        # Check valid prefixes
        if not (v.startswith('ChI') or v.startswith('places/')):
            raise ValueError(
                "Invalid place_id format. Must start with 'ChI' (legacy) or 'places/' (new API)"
            )
        
        # Length validation (Place IDs are typically 10-200 chars)
        if len(v) < 10 or len(v) > 200:
            raise ValueError(
                f"Invalid place_id length: {len(v)} chars. Expected 10-200 chars."
            )
        
        # Character whitelist: alphanumeric + underscore + hyphen + forward slash only
        # This prevents XSS, SQL injection, and path traversal attempts
        if not re.match(r'^[a-zA-Z0-9_\-\/]+$', v):
            raise ValueError(
                "place_id contains invalid characters. Only alphanumeric, underscore, hyphen, and forward slash allowed."
            )
        
        return v


class BuildResponse(BaseModel):
    """POST /api/build response
    
    Returns session_id for tracking build progress via SSE.
    No caching - every request generates a fresh landing page.
    """
    session_id: str


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


