"""
Sandbox Renderer - Headless browser auditing for CORS/XFO/CSP issues
Uses Playwright to deterministically evaluate HTML and emit structured violations
"""
from typing import Dict, Any, List, Optional
import logging
import asyncio
import uuid
from datetime import datetime

logger = logging.getLogger(__name__)

# Store render results in memory (in production, use Redis)
_render_results: Dict[str, Dict[str, Any]] = {}


class SandboxRenderer:
    """Audit HTML in isolated Playwright browser"""
    
    def __init__(self):
        self.browser = None
        self.playwright = None
    
    async def initialize(self):
        """Initialize Playwright browser"""
        try:
            from playwright.async_api import async_playwright
            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.launch(
                headless=True,
                args=['--disable-dev-shm-usage', '--no-sandbox']
            )
            logger.info("[SandboxRenderer] Playwright browser initialized")
        except ImportError:
            logger.error("[SandboxRenderer] Playwright not installed. Run: pip install playwright && playwright install chromium")
            raise
        except Exception as e:
            logger.error(f"[SandboxRenderer] Failed to initialize: {e}")
            raise
    
    async def shutdown(self):
        """Cleanup browser resources"""
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
    
    async def render_html(self, html: str, timeout_ms: int = 8000, capture_screenshot: bool = False) -> str:
        """
        Render HTML in sandbox and start audit.
        Returns run_id for collecting findings.
        
        Args:
            html: HTML content to render
            timeout_ms: Maximum time to wait for page load
            capture_screenshot: If True, capture full-page screenshot for visual validation
        """
        run_id = str(uuid.uuid4())
        
        try:
            errors: List[Dict[str, Any]] = []
            warnings: List[Dict[str, Any]] = []
            
            # Create new context for isolation
            context = await self.browser.new_context(
                user_agent='Mozilla/5.0 (compatible; SandboxRenderer/1.0)',
                viewport={'width': 1280, 'height': 720}
            )
            page = await context.new_page()
            
            # Collect console messages
            def handle_console(msg):
                msg_type = msg.type
                text = msg.text
                if msg_type == 'error':
                    errors.append({
                        'code': 'CONSOLE_ERROR',
                        'text': text,
                        'hint': 'Check for JavaScript errors or CSP violations'
                    })
                elif msg_type == 'warning':
                    warnings.append({
                        'code': 'CONSOLE_WARNING',
                        'text': text
                    })
            
            page.on('console', handle_console)
            
            # Collect network responses
            async def handle_response(response):
                url = response.url
                status = response.status
                headers = await response.all_headers()
                ct = headers.get('content-type', '')
                
                # HTTP errors
                if status >= 400:
                    errors.append({
                        'code': 'HTTP_ERROR',
                        'url': url,
                        'status': status,
                        'hint': f'Resource returned {status}. Fix URL or replace with valid resource.'
                    })
                
                # CORS font check
                if any(ext in url.lower() for ext in ['.woff2', '.woff', '.otf', '.ttf']) or 'font/' in ct:
                    if 'access-control-allow-origin' not in headers:
                        warnings.append({
                            'code': 'CORS_FONT_NO_ACAO',
                            'url': url,
                            'hint': 'Font served without ACAO; add crossorigin="anonymous" and use CDN with ACAO:*'
                        })
                
                # X-Frame-Options blocking
                resource_type = response.request.resource_type
                if resource_type == 'document':
                    xfo = headers.get('x-frame-options', '')
                    if xfo and any(x in xfo.lower() for x in ['deny', 'sameorigin']):
                        errors.append({
                            'code': 'XFO_BLOCK',
                            'url': url,
                            'header': f'X-Frame-Options: {xfo}',
                            'hint': 'Document cannot be embedded due to X-Frame-Options. Remove header or use inline content.'
                        })
                    
                    # CSP frame-ancestors blocking
                    csp = headers.get('content-security-policy', '')
                    if 'frame-ancestors' in csp.lower():
                        if "'none'" in csp.lower() or 'none' in csp.lower():
                            errors.append({
                                'code': 'CSP_FRAME_ANCESTORS_BLOCK',
                                'url': url,
                                'header': f'CSP: {csp}',
                                'hint': 'Document cannot be embedded due to CSP frame-ancestors. Use inline content.'
                            })
                
                # Mixed content
                if url.startswith('http://') and not url.startswith('http://localhost'):
                    errors.append({
                        'code': 'MIXED_CONTENT',
                        'url': url,
                        'hint': 'Replace http:// with https:// to avoid mixed content warnings'
                    })
            
            context.on('response', handle_response)
            
            # Load HTML
            await page.set_content(html, wait_until='networkidle', timeout=timeout_ms)
            
            # DOM-based checks
            has_bad_targets = await page.evaluate('''() => {
                return !!document.querySelector('a[target="_blank"]:not([rel~="noopener"])')
            }''')
            if has_bad_targets:
                errors.append({
                    'code': 'MISSING_NOOPENER',
                    'hint': 'Add rel="noopener noreferrer" to all links with target="_blank"'
                })
            
            has_maps = await page.evaluate('''() => {
                return !!document.querySelector('a[href*="google.com/maps"],a[href*="maps.google."]')
            }''')
            if has_maps:
                errors.append({
                    'code': 'FORBIDDEN_MAPS_LINK',
                    'hint': 'Remove Google Maps links entirely'
                })
            
            # Check for missing crossorigin on cross-origin resources
            missing_crossorigin = await page.evaluate('''() => {
                const elements = [];
                document.querySelectorAll('link[rel="stylesheet"], link[rel="preload"], script[src]').forEach(el => {
                    const href = el.href || el.src;
                    if (href && new URL(href).origin !== window.location.origin) {
                        if (!el.hasAttribute('crossorigin')) {
                            elements.push({
                                tag: el.tagName.toLowerCase(),
                                href: href,
                                rel: el.rel || 'script'
                            });
                        }
                    }
                });
                return elements;
            }''')
            
            for elem in missing_crossorigin:
                warnings.append({
                    'code': 'MISSING_CROSSORIGIN',
                    'element': f'<{elem["tag"]} href="{elem["href"]}">',
                    'hint': 'Add crossorigin="anonymous" to cross-origin resources'
                })
            
            # Capture full-page screenshot for visual validation (if requested)
            screenshot_base64 = None
            if capture_screenshot:
                try:
                    screenshot_bytes = await page.screenshot(full_page=True, type='png')
                    import base64
                    screenshot_base64 = base64.b64encode(screenshot_bytes).decode('utf-8')
                    logger.info(f"[SandboxRenderer] Captured full-page screenshot ({len(screenshot_bytes)} bytes)")
                except Exception as e:
                    logger.warning(f"[SandboxRenderer] Screenshot capture failed: {e}")
                    warnings.append({
                        'code': 'SCREENSHOT_FAILED',
                        'hint': f'Failed to capture screenshot: {e}'
                    })
            
            await context.close()
            
            # Store results
            _render_results[run_id] = {
                'ok': len(errors) == 0,
                'errors': errors,
                'warnings': warnings,
                'timestamp': datetime.utcnow().isoformat(),
                'screenshot_base64': screenshot_base64  # Base64-encoded PNG for agent validation
            }
            
            logger.info(f"[SandboxRenderer] Audit complete: {len(errors)} errors, {len(warnings)} warnings")
            
        except Exception as e:
            logger.error(f"[SandboxRenderer] Render failed: {e}", exc_info=True)
            _render_results[run_id] = {
                'ok': False,
                'errors': [{
                    'code': 'RENDER_ERROR',
                    'text': str(e),
                    'hint': 'Failed to render HTML in sandbox'
                }],
                'warnings': [],
                'timestamp': datetime.utcnow().isoformat()
            }
        
        return run_id
    
    def collect_findings(self, run_id: str) -> Dict[str, Any]:
        """Retrieve audit results for a run_id"""
        return _render_results.get(run_id, {
            'ok': False,
            'errors': [{'code': 'RUN_NOT_FOUND', 'hint': 'Invalid run_id'}],
            'warnings': []
        })


# Synchronous wrapper for MCP tool
def render_html(html: str, timeout_ms: int = 8000, capture_screenshot: bool = False) -> Dict[str, Any]:
    """
    Render HTML and audit (synchronous wrapper).
    
    Args:
        html: HTML content to render
        timeout_ms: Maximum time to wait
        capture_screenshot: If True, capture full-page screenshot
        
    Returns:
        {'run_id': str}
    """
    loop = asyncio.get_event_loop()
    renderer = SandboxRenderer()
    
    async def _render():
        await renderer.initialize()
        try:
            run_id = await renderer.render_html(html, timeout_ms, capture_screenshot)
            return {'run_id': run_id}
        finally:
            await renderer.shutdown()
    
    return loop.run_until_complete(_render())


def collect_findings(run_id: str) -> Dict[str, Any]:
    """Collect findings for a render run"""
    renderer = SandboxRenderer()
    return renderer.collect_findings(run_id)

