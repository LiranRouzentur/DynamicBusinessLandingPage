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
        self.timeout = 300.0  # Longer timeout for agent operations (5 minutes) - agents can take time for multiple retries
        self._client: Optional[httpx.AsyncClient] = None
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client with connection pooling"""
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=self.timeout,
                limits=httpx.Limits(max_connections=10, max_keepalive_connections=5)
            )
            logger.info("Created new HTTP client with connection pooling")
        return self._client
    
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
        try:
            client = await self._get_client()
            
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
            
            logger.debug(f"Sending POST to {self.base_url}/build")
            response = await client.post(
                f"{self.base_url}/build",
                json=payload
            )
            
            logger.debug(f"Received response: status={response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                logger.debug(f"Response parsed, success={result.get('success')}")
                
                # Convert agent service bundle format to backend format
                if result.get("success") and result.get("bundle"):
                    bundle = result["bundle"]
                    
                    # Normalize keys
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
                logger.error(f"Build failed: {response.status_code}")
                return None
                
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
        try:
            client = await self._get_client()
            response = await client.get(f"{self.base_url}/health", timeout=5.0)
            return response.status_code == 200
        except Exception:
            return False
    
    async def close(self):
        """Close the HTTP client"""
        if self._client:
            await self._client.aclose()
            logger.info("Closed HTTP client")
            self._client = None


# Global client instance
agents_client = AgentsServiceClient()

