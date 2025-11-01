"""Client for the new AI agents service"""
import httpx
import asyncio
import logging
from typing import Dict, Any, Optional
from landing_api.core.config import settings

logger = logging.getLogger(__name__)


class AgentsServiceClient:
    """Client to communicate with the agents service"""
    
    def __init__(self, use_new_agents: bool = True):
        # New agents service runs on port 8002, old on 8001
        self.base_url = "http://localhost:8002" if use_new_agents else "http://localhost:8001"
        self.use_new_agents = use_new_agents
        self.timeout = 300.0  # 5 minutes timeout
    
    async def build(
        self,
        session_id: str,
        business_name: str,
        category: str,
        place_data: Dict[str, Any],
        render_prefs: Dict[str, Any],
        data_richness: Dict[str, bool],
        stop_after: Optional[str] = None  # "mapper", "generator", or "validator" for testing
    ) -> Optional[Dict[str, Any]]:
        """
        Call the agents service to build a landing page
        
        Args:
            session_id: Session identifier
            business_name: Name of the business
            category: Business category
            place_data: Normalized place data from Google
            render_prefs: Rendering preferences
            data_richness: Data availability flags
            
        Returns:
            Build result dict or None if failed
        """
        # Create fresh client for each request to avoid event loop issues
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                payload = {
                    "session_id": session_id,
                    "business_name": business_name,
                    "category": category,
                    "place_data": place_data,
                    "render_prefs": render_prefs,
                    "data_richness": data_richness
                }
                
                # Add stop_after if provided (for testing)
                if stop_after:
                    payload["stop_after"] = stop_after
                
                logger.info(
                    f"[AGENTS_CLIENT] Sending POST to {self.base_url}/build | "
                    f"session_id={session_id} | "
                    f"timeout={self.timeout}s"
                )
                
                response = await client.post(
                    f"{self.base_url}/build",
                    json=payload
                )
                
                logger.info(
                    f"[AGENTS_CLIENT] Received response | "
                    f"status={response.status_code} | "
                    f"session_id={session_id} | "
                    f"headers={dict(response.headers)}"
                )
                
                if response.status_code == 200:
                    result = response.json()
                    logger.info(
                        f"[AGENTS_CLIENT] Response parsed | "
                        f"success={result.get('success')} | "
                        f"has_bundle={bool(result.get('bundle'))} | "
                        f"session_id={session_id}"
                    )
                    
                    if not result.get("success"):
                        error_detail = result.get("error", "Unknown error")
                        logger.error(f"Build failed: {error_detail}")
                        return {"success": False, "error": error_detail}
                    
                    # Convert agent service bundle format to backend format
                    if result.get("bundle"):
                        bundle = result["bundle"]
                        
                        # Check if single-file HTML mode (html field exists)
                        if "html" in bundle:
                            # Single-file mode - pass through as-is
                            normalized = {"html": bundle["html"]}
                            if "meta" in bundle:
                                normalized["meta"] = bundle["meta"]
                        else:
                            # Multi-file mode - normalize key names
                            normalized = {}
                            if "index_html" in bundle:
                                normalized["index_html"] = bundle["index_html"]
                            elif "index.html" in bundle:
                                normalized["index_html"] = bundle["index.html"]
                            
                            if "styles_css" in bundle:
                                normalized["styles_css"] = bundle["styles_css"]
                            elif "styles.css" in bundle:
                                normalized["styles_css"] = bundle["styles.css"]
                            
                            if "app_js" in bundle:
                                normalized["app_js"] = bundle["app_js"]
                            elif "app.js" in bundle:
                                normalized["app_js"] = bundle["app.js"]
                        
                        result["bundle"] = normalized
                    
                    return result
                else:
                    # Try to extract error detail from response
                    try:
                        error_detail = response.json().get("detail", "Unknown error")
                        logger.error(f"Build failed: {response.status_code} - {error_detail}")
                    except:
                        error_detail = f"HTTP {response.status_code}"
                        logger.error(f"Build failed: {response.status_code}")
                    return {"success": False, "error": error_detail}
                    
        except httpx.ReadTimeout as e:
            logger.error(
                f"[AGENTS_CLIENT] ✗ TIMEOUT | "
                f"session_id={session_id} | "
                f"timeout={self.timeout}s | "
                f"error={e} | "
                f"NOTE: Agent may have completed but response was slow to return"
            )
            return {"success": False, "error": f"Request timed out after {int(self.timeout/60)} minutes. The AI generation is taking longer than expected. Please try again."}
        except httpx.ConnectError as e:
            logger.error(f"Cannot connect to agents service - is it running? Error: {e}")
            return None
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error: {e.response.status_code} - {e.response.text}")
            return None
        except Exception as e:
            logger.exception("Unexpected error in build request")
            return None
    
    async def health_check(self) -> bool:
        """Check if agents service is healthy"""
        # Create fresh client for health checks too
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.base_url}/health")
                return response.status_code == 200
        except Exception:
            return False


# Global client instance
agents_client = AgentsServiceClient()

