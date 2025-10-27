"""API request/response schemas - Ref: Product.md > Section 4"""

from typing import Optional, List
from pydantic import BaseModel, Field


class RenderPrefs(BaseModel):
    """Rendering preferences - Ref: Product.md lines 675-686"""
    language: str = "en"
    direction: str = "ltr"
    brand_colors: Optional[dict] = None
    font_stack: str = "system-ui"
    allow_external_cdns: bool = False
    max_reviews: int = 6


class BuildRequest(BaseModel):
    """POST /api/build request - Ref: Product.md lines 666-674"""
    place_id: str = Field(..., description="Google Maps place_id")
    render_prefs: Optional[RenderPrefs] = None


class BuildResponse(BaseModel):
    """POST /api/build response - Ref: Product.md lines 688-697"""
    session_id: str
    cached: bool = False


class ProgressEvent(BaseModel):
    """SSE progress event - Ref: Product.md lines 728-739"""
    ts: str
    session_id: str
    phase: str = Field(..., description="FETCHING|ORCHESTRATING|GENERATING|QA|READY|ERROR")
    step: str
    detail: str
    progress: float = Field(ge=0.0, le=1.0)


class ErrorResponse(BaseModel):
    """Error response - Ref: Product.md lines 815-824"""
    error_id: str
    code: str
    message: str
    hint: Optional[str] = None
    retryable: bool = False
    session_id: Optional[str] = None


