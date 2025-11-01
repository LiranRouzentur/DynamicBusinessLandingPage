"""API Authentication"""

from fastapi import Security, HTTPException, status
from fastapi.security import APIKeyHeader
from landing_api.core.config import settings
import logging

logger = logging.getLogger(__name__)

# Define API key header scheme
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def verify_api_key(api_key: str = Security(api_key_header)) -> str:
    """
    Verify API key from request header.
    
    Args:
        api_key: API key from X-API-Key header
        
    Returns:
        The validated API key
        
    Raises:
        HTTPException: If API key is missing or invalid
    """
    # Check if API key is configured
    if not settings.api_key:
        logger.warning("API_KEY not configured in environment - authentication disabled")
        return None  # Allow requests when no API key is configured (dev mode)
    
    # Check if API key was provided
    if not api_key:
        logger.warning("Request missing X-API-Key header")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Missing API key. Please provide X-API-Key header.",
        )
    
    # Verify API key matches
    if api_key != settings.api_key:
        logger.warning(f"Invalid API key attempt: {api_key[:8]}...")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API key",
        )
    
    return api_key

