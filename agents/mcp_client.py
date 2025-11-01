"""MCP client for AI server - connects to MCP server via HTTP (FastMCP)"""
import httpx
import os
import pathlib
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class MCPClient:
    """Client for MCP server via HTTP (FastMCP + Starlette)"""
    
    # Initializes HTTP client for MCP server (port 8003) with separate timeouts (5s write, 60s read).
    # Workspace_root for info only - server manages its own workspace via env var.
    def __init__(self, workspace_root: Optional[pathlib.Path] = None, 
                 base_url: Optional[str] = None):
        """
        Initialize MCP client
        
        Args:
            workspace_root: Root workspace directory (for info only; server manages its own workspace)
            base_url: MCP server base URL (default: http://localhost:8003)
        """
        self.base_url = base_url or os.getenv("MCP_BASE_URL", "http://localhost:8003")
        self.workspace_root = workspace_root or pathlib.Path("./mcp/storage/workspace")
        # Set different timeouts for different operations
        # write_files should be fast (5s), validate can be slower (60s)
        self.client = httpx.Client(
            base_url=self.base_url,
            timeout=httpx.Timeout(5.0, read=60.0)  # 5s connect/write, 60s read
        )
        logger.info(f"[MCPClient] Initialized with base_URL: {self.base_url}")
    
    # Calls MCP tool via HTTP POST to /mcp/tools/{tool_name} with retry logic (3 attempts, 2s delay).
    # Raises RuntimeError if all retries fail or if HTTP error returned; critical for validation flow.
    def _call_tool(self, tool_name: str, **kwargs) -> Dict[str, Any]:
        """
        Call MCP tool via HTTP with retry logic
        
        Args:
            tool_name: Name of the tool to call
            **kwargs: Tool arguments
            
        Returns:
            Tool result as dict
        """
        import time
        max_retries = 3
        retry_delay = 2  # seconds
        
        for attempt in range(max_retries):
            try:
                response = self.client.post(
                    f"/mcp/tools/{tool_name}",
                    json=kwargs
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                logger.error(f"[MCPClient] HTTP error calling {tool_name}: {e.response.status_code} - {e.response.text}")
                raise RuntimeError(f"MCP tool {tool_name} failed: {e.response.status_code}")
            except httpx.RequestError as e:
                if attempt < max_retries - 1:
                    logger.warning(f"[MCPClient] Request error calling {tool_name} (attempt {attempt + 1}/{max_retries}): {e}, retrying in {retry_delay}s...")
                    time.sleep(retry_delay)
                    continue
                else:
                    logger.error(f"[MCPClient] Request error calling {tool_name} after {max_retries} attempts: {e}")
                    raise RuntimeError(f"MCP server not reachable at {self.base_url}")
            except Exception as e:
                logger.error(f"[MCPClient] Unexpected error calling {tool_name}: {e}")
                raise
    
    # Bundle tools
    # Writes files to MCP workspace; files is list of {path, content} dicts.
    # Returns {written: [paths]} listing successfully written files.
    def write_files(self, files: list) -> Dict[str, Any]:
        """
        Write files to workspace.
        
        Args:
            files: List of dicts with 'path' and 'content' keys
            
        Returns:
            Dict with 'written' list
        """
        return self._call_tool("write_files", files=files)
    
    def inject_comment(self, index_path: str, comment: str) -> Dict[str, Any]:
        """
        Inject a comment into HTML file.
        
        Args:
            index_path: Path to index.html
            comment: HTML comment string
            
        Returns:
            Dict with 'applied' boolean
        """
        return self._call_tool("inject_comment", index_path=index_path, comment=comment)
    
    # QA tools
    # Validates HTML bundle structure, security (CSP, XSS), images, accessibility, SEO.
    # Returns {status: PASS/FAIL, violations: [errors], metrics}; critical for quality assurance.
    def validate_static_bundle(self) -> Dict[str, Any]:
        """
        Validate static HTML bundle.
        
        Returns:
            Dict with validation results
        """
        return self._call_tool("validate_static_bundle")
    
    # Network tools
    def head(self, url: str, timeout_ms: int = 2500) -> Dict[str, Any]:
        """
        Perform HTTP HEAD request.
        
        Args:
            url: URL to check
            timeout_ms: Timeout in milliseconds
            
        Returns:
            Dict with response metadata
        """
        return self._call_tool("head_request", url=url, timeout_ms=timeout_ms)
    
    # Utility tools
    def hash_dir(self) -> Dict[str, Any]:
        """
        Compute hash of workspace directory.
        
        Returns:
            Dict with 'tree_hash'
        """
        return self._call_tool("hash_directory")
    
    def cors_fixer(self, html: str, findings: list) -> Dict[str, Any]:
        """
        Fix CORS/XFO/CSP issues in HTML.
        
        Args:
            html: HTML content to fix
            findings: List of findings from sandbox_render
            
        Returns:
            Dict with 'html' and 'changes' keys
        """
        return self._call_tool("cors_fixer", html=html, findings=findings)
    
    def sandbox_render(self, html: str, timeout_ms: int = 8000) -> Dict[str, Any]:
        """
        Render HTML in sandbox and audit for CORS/XFO/CSP issues.
        
        Args:
            html: HTML content to render
            timeout_ms: Timeout in milliseconds
            
        Returns:
            Dict with 'run_id' for collecting findings
        """
        return self._call_tool("sandbox_render", html=html, timeout_ms=timeout_ms)
    
    def collect_findings(self, run_id: str) -> Dict[str, Any]:
        """
        Collect audit findings from a sandbox render.
        
        Args:
            run_id: Run ID from sandbox_render
            
        Returns:
            Dict with 'ok', 'errors', and 'warnings' keys
        """
        return self._call_tool("collect_findings", run_id=run_id)
    
    def health_check(self) -> Dict[str, Any]:
        """
        Check MCP server health.
        
        Returns:
            Dict with health status
        """
        try:
            response = self.client.get("/health")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"[MCPClient] Health check failed: {e}")
            raise RuntimeError(f"MCP server health check failed: {e}")
    
    def close(self):
        """Close HTTP client"""
        try:
            self.client.close()
        except Exception as e:
            logger.warning(f"[MCPClient] Error closing client: {e}")
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
