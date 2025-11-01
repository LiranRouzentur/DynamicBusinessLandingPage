"""MCP validator_errors endpoint"""

import logging
import os
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import httpx

router = APIRouter()
logger = logging.getLogger(__name__)


class ValidationError(BaseModel):
    id: str
    severity: str  # 'error' | 'warning'
    category: str  # 'security' | 'accessibility' | 'layout' | 'project-specific'
    message: str
    hint: str
    where: Optional[str] = None


class ValidatorErrorsRequest(BaseModel):
    html: str
    errors: List[ValidationError]
    session_id: str


class ValidatorErrorsResponse(BaseModel):
    fixed_html: Optional[str] = None
    remaining_errors: Optional[List[ValidationError]] = None
    success: bool
    message: Optional[str] = None


@router.post("/mcp/validator_errors", response_model=ValidatorErrorsResponse)
async def validator_errors(request: ValidatorErrorsRequest) -> ValidatorErrorsResponse:
    """
    Send validation errors to MCP validator_errors tool for automatic fixing.
    
    This endpoint:
    1. Takes HTML and validation errors
    2. Calls MCP validator_errors tool
    3. Returns fixed HTML and any remaining errors
    """
    try:
        logger.info(f"[MCP Validator] Received {len(request.errors)} errors for session {request.session_id}")
        
        # Call MCP validator_errors tool via HTTP
        mcp_url = os.getenv("MCP_SERVER_URL", "http://localhost:8003")
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{mcp_url}/mcp/tools/validator_errors",
                    json={
                        "html": request.html,
                        "errors": [err.dict() for err in request.errors]
                    }
                )
                response.raise_for_status()
                result = response.json()
                
                return ValidatorErrorsResponse(
                    success=result.get("success", False),
                    fixed_html=result.get("fixed_html"),
                    remaining_errors=[ValidationError(**e) for e in (result.get("remaining_errors") or [])],
                    message=result.get("message")
                )
        except httpx.RequestError as e:
            logger.error(f"[MCP Validator] Request error: {e}")
            return ValidatorErrorsResponse(
                success=False,
                message=f"MCP server connection error: {str(e)}",
            )
        except httpx.HTTPStatusError as e:
            logger.error(f"[MCP Validator] HTTP error {e.response.status_code}: {e}")
            return ValidatorErrorsResponse(
                success=False,
                message=f"MCP server returned {e.response.status_code}: {str(e)}",
            )
            
    except Exception as e:
        logger.error(f"[MCP Validator] Unexpected error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


