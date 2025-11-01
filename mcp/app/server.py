"""
FastMCP Server - Official Python MCP SDK Implementation

This server exposes MCP tools via HTTP using FastMCP + Starlette REST API.
FastMCP tools are wrapped in REST endpoints for the agents client.
"""
import os
import sys
import pathlib
import logging
from typing import Dict, Any, Optional
from contextlib import asynccontextmanager

from fastmcp import FastMCP
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request

# Add tools directory to path
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / "tools"))

from bundle import Bundle
from qa import QA
from net import Net
from util import Util
from adaptive_manager import AdaptiveManager
from fixer import fix_html_errors
from cors_fixer import rewrite_html as cors_rewrite_html

# Configure logging - console only
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s - %(name)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stderr)]
)

# Force immediate flush on all handlers for better debugging
for handler in logging.root.handlers:
    handler.flush()

logger = logging.getLogger(__name__)
logger.info("[MCP] Logging to console only")

# Initialize FastMCP server
mcp = FastMCP("landing-page-mcp")

# Global state for tool instances
_bundle: Optional[Bundle] = None
_qa: Optional[QA] = None
_net: Optional[Net] = None
_util: Optional[Util] = None


# Gets workspace root directory from WORKSPACE_ROOT env var (supports per-session workspaces).
# Defaults to mcp/storage/workspace; creates directory if missing; critical for file operations.
def _get_workspace_root() -> pathlib.Path:
    """Get workspace root - supports per-session workspaces via env var"""
    default_workspace = pathlib.Path(__file__).parent.parent / "storage" / "workspace"
    root = pathlib.Path(os.getenv("WORKSPACE_ROOT", str(default_workspace))).resolve()
    root.mkdir(parents=True, exist_ok=True)
    return root


def _get_cache_root() -> pathlib.Path:
    """Get cache root"""
    root = pathlib.Path(os.getenv("CACHE_ROOT", "./mcp/storage/cache")).resolve()
    root.mkdir(parents=True, exist_ok=True)
    return root


# Initializes all MCP tool instances (Bundle, QA, Net, Util) with workspace and policy configs.
# Loads image limits, CSP template, domain allowlist; sets up adaptive manager for runtime policy updates.
def _init_tools():
    """Initialize tool instances"""
    global _bundle, _qa, _net, _util
    
    root = _get_workspace_root()
    cache_dir = _get_cache_root()
    
    # Initialize adaptive manager
    mcp_dir = pathlib.Path(__file__).parent.parent.resolve()
    policies_dir = mcp_dir / "policies"
    adaptive_manager = AdaptiveManager(policies_dir)
    
    # Get allowed domains
    allowed_domains = adaptive_manager.get_allowed_domains()
    
    # Initialize network layer
    _net = Net(
        allowlist=allowed_domains,
        cache_root=cache_dir,
        adaptive_manager=adaptive_manager,
        circuit_threshold=5,
        cooldown_s=60
    )
    
    # Load policies
    image_limits_path = os.getenv("IMAGE_LIMITS_JSON", str(policies_dir / "image_limits.json"))
    csp_template_path = os.getenv("CSP_TEMPLATE", str(policies_dir / "csp_default.txt"))
    
    _util = Util(root)
    image_limits = _util.load_json(image_limits_path)
    csp_template = _util.read_text(csp_template_path)
    
    # Initialize tools
    _bundle = Bundle(root, _util, csp_template, adaptive_manager)
    _qa = QA(root, _util, image_limits, adaptive_manager, cache_dir)
    
    logger.info("✓ MCP tools initialized")


# =====================================================
# Internal Tool Functions (shared by REST and FastMCP)
# =====================================================

# Internal: writes files to workspace via Bundle tool; shared by REST and FastMCP endpoints.
# Returns {written: [paths]} listing successfully written files; validates tool initialization.
def _write_files_impl(files: list[dict[str, str]]) -> dict[str, Any]:
    """Internal implementation of write_files"""
    if _bundle is None:
        raise RuntimeError("Tools not initialized")
    return _bundle.write_files({"files": files})


def _inject_comment_impl(index_path: str, comment: str) -> dict[str, Any]:
    """Internal implementation of inject_comment"""
    if _bundle is None:
        raise RuntimeError("Tools not initialized")
    return _bundle.inject_comment({"indexPath": index_path, "comment": comment})


# Internal: validates HTML bundle structure, security, images, SEO via QA tool.
# Returns {status: PASS/FAIL, violations, metrics}; enforces quality gates before deployment.
def _validate_static_bundle_impl() -> dict[str, Any]:
    """Internal implementation of validate_static_bundle"""
    if _qa is None:
        raise RuntimeError("Tools not initialized")
    return _qa.validate_static_bundle({})


def _head_request_impl(url: str, timeout_ms: int = 2500) -> dict[str, Any]:
    """Internal implementation of head_request"""
    if _net is None:
        raise RuntimeError("Tools not initialized")
    return _net.head({"url": url, "timeoutMs": timeout_ms})


def _hash_directory_impl() -> dict[str, Any]:
    """Internal implementation of hash_directory"""
    if _util is None:
        raise RuntimeError("Tools not initialized")
    return _util.hash_dir({})


# Internal: fixes HTML validation errors automatically using fixer tool; optional visual validation with screenshot.
# Returns {success, fixed_html, fixes_applied, remaining_errors}; uses AI for complex fixes when screenshot provided.
def _validator_errors_impl(html: str, errors: list[dict[str, Any]], screenshot_base64: Optional[str] = None) -> dict[str, Any]:
    """Internal implementation of validator_errors with optional screenshot for visual validation"""
    try:
        logger.info(
            f"[MCP] validator_errors | "
            f"errors_count={len(errors)} | "
            f"html_length={len(html)} | "
            f"has_screenshot={screenshot_base64 is not None}"
        )
        
        result = fix_html_errors(html, errors, screenshot_base64)
        response = {
            "success": True,
            "fixed_html": result.get("fixed_html", html),
            "fixes_applied": result.get("fixes_applied", []),
            "remaining_errors": result.get("remaining_errors", [])
        }
        
        # Include visual validation prompt if screenshot was provided
        if "visual_validation" in result:
            response["visual_validation"] = result["visual_validation"]
            logger.info(
                f"[MCP] Visual validation ready | "
                f"errors_fixed={len(errors)} | "
                f"screenshot_size={len(screenshot_base64) if screenshot_base64 else 0}"
            )
        
        logger.info(
            f"[MCP] validator_errors complete | "
            f"fixes_applied={len(response['fixes_applied'])} | "
            f"remaining_errors={len(response['remaining_errors'])}"
        )
        
        return response
    except Exception as e:
        logger.error(
            f"[MCP] ✗ validator_errors FAILED | "
            f"error_type={type(e).__name__} | "
            f"error={str(e)} | "
            f"errors_count={len(errors)} | "
            f"html_length={len(html)}",
            exc_info=True
        )
        return {
            "success": False,
            "message": str(e),
            "error_type": type(e).__name__,
            "fixed_html": None,
            "remaining_errors": errors
        }


def _cors_fixer_impl(html: str, findings: list[dict[str, Any]]) -> dict[str, Any]:
    """Internal implementation of CORS fixer"""
    try:
        result = cors_rewrite_html(html, findings)
        return {
            "success": True,
            "html": result.get("html", html),
            "changes": result.get("changes", [])
        }
    except Exception as e:
        logger.error(f"cors_fixer implementation error: {e}", exc_info=True)
        return {
            "success": False,
            "message": str(e),
            "html": html,
            "changes": []
        }


def _sandbox_render_impl(html: str, timeout_ms: int = 8000, capture_screenshot: bool = False) -> dict[str, Any]:
    """Internal implementation of sandbox renderer"""
    try:
        logger.info(
            f"[MCP] sandbox_render | "
            f"html_length={len(html)} | "
            f"timeout_ms={timeout_ms} | "
            f"capture_screenshot={capture_screenshot}"
        )
        
        # Attempt to use Playwright renderer
        try:
            from sandbox_renderer import render_html as sandbox_render
            result = sandbox_render(html, timeout_ms, capture_screenshot)
            
            logger.info(
                f"[MCP] sandbox_render complete | "
                f"run_id={result.get('run_id', 'unknown')}"
            )
            
            return result
        except ImportError:
            logger.warning("[MCP] Playwright not available, using basic validation")
            # Fallback to basic validation
            return {
                "run_id": "fallback",
                "note": "Playwright not installed. Using basic validation. Install with: pip install playwright && playwright install chromium"
            }
    except Exception as e:
        logger.error(
            f"[MCP] ✗ sandbox_render FAILED | "
            f"error_type={type(e).__name__} | "
            f"error={str(e)} | "
            f"html_length={len(html)} | "
            f"timeout_ms={timeout_ms}",
            exc_info=True
        )
        return {
            "run_id": "error",
            "error": str(e),
            "error_type": type(e).__name__
        }


def _collect_findings_impl(run_id: str) -> dict[str, Any]:
    """Internal implementation of collect findings"""
    try:
        try:
            from sandbox_renderer import collect_findings
            return collect_findings(run_id)
        except ImportError:
            # Fallback
            return {
                "ok": True,
                "errors": [],
                "warnings": [],
                "note": "Playwright not available"
            }
    except Exception as e:
        logger.error(f"collect_findings implementation error: {e}", exc_info=True)
        return {
            "ok": False,
            "errors": [{"code": "ERROR", "text": str(e)}],
            "warnings": []
        }


# =====================================================
# MCP Tools - FastMCP Decorators
# =====================================================

# FastMCP tool: writes files to workspace from agents; files is list of {path, content} dicts.
# Returns {written: [paths]}; exposed via both MCP protocol and REST API at /mcp/tools/write_files.
@mcp.tool()
def write_files(files: list[dict[str, str]]) -> dict[str, Any]:
    """
    Write files to workspace.
    
    Args:
        files: List of dicts with 'path' and 'content' keys
        
    Returns:
        Dict with 'written' list of written file paths
    """
    return _write_files_impl(files)


@mcp.tool()
def inject_comment(index_path: str, comment: str) -> dict[str, Any]:
    """
    Inject a comment into HTML file.
    
    Args:
        index_path: Path to index.html (e.g., "index.html")
        comment: HTML comment string to inject
        
    Returns:
        Dict with 'applied' boolean
    """
    return _inject_comment_impl(index_path, comment)


# FastMCP tool: validates HTML bundle for security, structure, accessibility, SEO compliance.
# Returns {passed, violations, metrics}; critical quality gate before serving pages to users.
@mcp.tool()
def validate_static_bundle() -> dict[str, Any]:
    """
    Validate static HTML bundle structure and content.
    
    Returns:
        Dict with validation results including 'passed', 'violations', and 'metrics'
    """
    return _validate_static_bundle_impl()


@mcp.tool()
def head_request(url: str, timeout_ms: int = 2500) -> dict[str, Any]:
    """
    Perform HTTP HEAD request to check URL accessibility.
    
    Args:
        url: URL to check
        timeout_ms: Timeout in milliseconds (default: 2500)
        
    Returns:
        Dict with 'status', 'headers', and other response metadata
    """
    return _head_request_impl(url, timeout_ms)


@mcp.tool()
def hash_directory() -> dict[str, Any]:
    """
    Compute hash of workspace directory.
    
    Returns:
        Dict with 'tree_hash' and file metadata
    """
    return _hash_directory_impl()


@mcp.tool()
def validator_errors(html: str, errors: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Fix HTML validation errors automatically.
    
    Args:
        html: HTML content to fix
        errors: List of validation errors with id, severity, category, hint, etc.
        
    Returns:
        Dict with 'fixed_html', 'fixes_applied', and 'remaining_errors'
    """
    return _validator_errors_impl(html, errors)


@mcp.tool()
def cors_fixer(html: str, findings: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Fix CORS/XFO/CSP issues in HTML.
    
    Args:
        html: HTML content to fix
        findings: List of findings from sandbox_renderer
        
    Returns:
        Dict with 'html' and 'changes' keys
    """
    return _cors_fixer_impl(html, findings)


@mcp.tool()
def sandbox_render(html: str, timeout_ms: int = 8000) -> dict[str, Any]:
    """
    Render HTML in sandbox and audit for CORS/XFO/CSP issues.
    
    Args:
        html: HTML content to render
        timeout_ms: Timeout in milliseconds (default: 8000)
        
    Returns:
        Dict with 'run_id' for collecting findings
    """
    return _sandbox_render_impl(html, timeout_ms)


@mcp.tool()
def collect_findings(run_id: str) -> dict[str, Any]:
    """
    Collect audit findings from a sandbox render.
    
    Args:
        run_id: Run ID from sandbox_render
        
    Returns:
        Dict with 'ok', 'errors', and 'warnings' keys
    """
    return _collect_findings_impl(run_id)


# =====================================================
# REST API Endpoints (for agents client)
# =====================================================

async def handle_write_files(request: Request):
    """REST endpoint for write_files tool"""
    try:
        data = await request.json()
        files = data.get("files", [])
        result = _write_files_impl(files)
        return JSONResponse(result)
    except Exception as e:
        logger.error(f"write_files error: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


async def handle_inject_comment(request: Request):
    """REST endpoint for inject_comment tool"""
    try:
        data = await request.json()
        index_path = data.get("indexPath", data.get("index_path", ""))
        comment = data.get("comment", "")
        result = _inject_comment_impl(index_path, comment)
        return JSONResponse(result)
    except Exception as e:
        logger.error(f"inject_comment error: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


async def handle_validate_static_bundle(request: Request):
    """REST endpoint for validate_static_bundle tool"""
    try:
        result = _validate_static_bundle_impl()
        return JSONResponse(result)
    except Exception as e:
        logger.error(f"validate_static_bundle error: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


async def handle_head_request(request: Request):
    """REST endpoint for head_request tool"""
    try:
        data = await request.json()
        url = data.get("url", "")
        timeout_ms = data.get("timeoutMs", data.get("timeout_ms", 2500))
        result = _head_request_impl(url, timeout_ms)
        return JSONResponse(result)
    except Exception as e:
        logger.error(f"head_request error: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


async def handle_hash_directory(request: Request):
    """REST endpoint for hash_directory tool"""
    try:
        result = _hash_directory_impl()
        return JSONResponse(result)
    except Exception as e:
        logger.error(f"hash_directory error: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


async def handle_validator_errors(request: Request):
    """REST endpoint for validator_errors tool"""
    try:
        data = await request.json()
        html = data.get("html", "")
        errors = data.get("errors", [])
        result = _validator_errors_impl(html, errors)
        return JSONResponse(result)
    except Exception as e:
        logger.error(f"validator_errors error: {e}", exc_info=True)
        return JSONResponse({"error": str(e), "success": False}, status_code=500)


async def handle_cors_fixer(request: Request):
    """REST endpoint for cors_fixer tool"""
    try:
        data = await request.json()
        html = data.get("html", "")
        findings = data.get("findings", [])
        result = _cors_fixer_impl(html, findings)
        return JSONResponse(result)
    except Exception as e:
        logger.error(f"cors_fixer error: {e}", exc_info=True)
        return JSONResponse({"error": str(e), "success": False}, status_code=500)


async def handle_sandbox_render(request: Request):
    """REST endpoint for sandbox_render tool"""
    try:
        data = await request.json()
        html = data.get("html", "")
        timeout_ms = data.get("timeout_ms", 8000)
        result = _sandbox_render_impl(html, timeout_ms)
        return JSONResponse(result)
    except Exception as e:
        logger.error(f"sandbox_render error: {e}", exc_info=True)
        return JSONResponse({"error": str(e)}, status_code=500)


async def handle_collect_findings(request: Request):
    """REST endpoint for collect_findings tool"""
    try:
        data = await request.json()
        run_id = data.get("run_id", "")
        result = _collect_findings_impl(run_id)
        return JSONResponse(result)
    except Exception as e:
        logger.error(f"collect_findings error: {e}", exc_info=True)
        return JSONResponse({"error": str(e), "ok": False}, status_code=500)


# Health check endpoint: returns service status and available tools list.
# Used by agents/backend to verify MCP server availability before validation calls.
async def health_check(request: Request):
    """Health check endpoint"""
    return JSONResponse({
        "status": "healthy",
        "service": "landing-page-mcp",
        "tools": [
            "write_files", 
            "inject_comment", 
            "validate_static_bundle", 
            "head_request", 
            "hash_directory", 
            "validator_errors",
            "cors_fixer",
            "sandbox_render",
            "collect_findings"
        ]
    })


# =====================================================
# Starlette Application
# =====================================================

# Lifespan context manager: initializes tools on startup, logs readiness; handles graceful shutdown.
# Ensures all MCP tools (Bundle, QA, Net, Util) are configured before accepting requests.
@asynccontextmanager
async def lifespan(app):
    """Lifespan context manager for app startup/shutdown"""
    logger.info("🚀 Starting MCP server...")
    _init_tools()
    logger.info("✓ MCP server ready")
    yield
    logger.info("🛑 Shutting down MCP server...")


# Create Starlette app with REST endpoints
app = Starlette(
    debug=False,
    routes=[
        Route("/health", health_check, methods=["GET"]),
        Route("/mcp/tools/write_files", handle_write_files, methods=["POST"]),
        Route("/mcp/tools/inject_comment", handle_inject_comment, methods=["POST"]),
        Route("/mcp/tools/validate_static_bundle", handle_validate_static_bundle, methods=["POST"]),
        Route("/mcp/tools/head_request", handle_head_request, methods=["POST"]),
        Route("/mcp/tools/hash_directory", handle_hash_directory, methods=["POST"]),
        Route("/mcp/tools/validator_errors", handle_validator_errors, methods=["POST"]),
        Route("/mcp/tools/cors_fixer", handle_cors_fixer, methods=["POST"]),
        Route("/mcp/tools/sandbox_render", handle_sandbox_render, methods=["POST"]),
        Route("/mcp/tools/collect_findings", handle_collect_findings, methods=["POST"]),
    ],
    middleware=[
        Middleware(
            CORSMiddleware,
            allow_origins=[
                "http://localhost:8000",    # Backend API
                "http://127.0.0.1:8000",    # Backend API (alternative)
                "http://localhost:8002",    # Agents service
                "http://127.0.0.1:8002",    # Agents service (alternative)
                "http://localhost:5173",    # Frontend dev server
                "http://127.0.0.1:5173",    # Frontend dev server (alternative)
                # Add production URLs via environment variable
                os.getenv("BACKEND_URL", ""),
                os.getenv("AGENTS_URL", ""),
                os.getenv("FRONTEND_URL", ""),
            ],
            allow_credentials=True,
            allow_methods=["GET", "POST"],
            allow_headers=["Content-Type", "X-API-Key", "Authorization"]
        )
    ],
    lifespan=lifespan
)


if __name__ == "__main__":
    import uvicorn
    
    port = int(os.getenv("MCP_PORT", "8003"))
    host = os.getenv("MCP_HOST", "0.0.0.0")
    
    logger.info(f"Starting MCP REST API server on {host}:{port}")
    
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info",
        access_log=False
    )

