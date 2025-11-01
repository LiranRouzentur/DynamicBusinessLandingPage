"""Iframe validator - loads HTML in sandboxed iframe and checks for CORS/rendering errors"""
import asyncio
import logging
from typing import Dict, Any, List, Optional
import base64

logger = logging.getLogger(__name__)

# Try to import playwright, but gracefully degrade if not available
try:
    from playwright.async_api import async_playwright, Browser, Page
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    logger.warning("[IframeValidator] Playwright not installed - iframe validation will be skipped")
    PLAYWRIGHT_AVAILABLE = False
    Browser = None
    Page = None


# Loads HTML in headless Chrome via Playwright, validates rendering, images, and collects errors.
# Returns {passed, errors, screenshot (base64 PNG), console_logs, image_validation}; gracefully degrades if Playwright missing.
async def validate_in_iframe(html_content: str, timeout_ms: int = 10000) -> Dict[str, Any]:
    """
    Validate HTML by loading it in a sandboxed iframe
    
    Args:
        html_content: The HTML string to validate
        timeout_ms: Max time to wait for page load (default 10s)
        
    Returns:
        Dict with:
            - passed: bool
            - errors: List[str] - CORS errors, console errors, rendering issues
            - screenshot: Optional[str] - Base64 encoded screenshot of rendered page
            - console_logs: List[str] - All console messages
    """
    # Graceful degradation if Playwright not installed
    if not PLAYWRIGHT_AVAILABLE:
        logger.warning("[IframeValidator] Skipping iframe validation - Playwright not installed")
        return {
            "passed": True,  # Don't block build
            "errors": [],
            "page_snippet": None,
            "image_validation": None,
            "screenshot": None,
            "console_logs": ["Playwright not installed - iframe validation skipped"]
        }
    
    browser: Optional[Browser] = None
    page: Optional[Page] = None
    
    try:
        # Launch browser
        playwright = await async_playwright().start()
        browser = await playwright.chromium.launch(headless=True)
        page = await browser.new_page()
        
        # Track errors
        console_errors = []
        network_errors = []
        page_errors = []
        console_logs = []
        
        # Listen to console events
        page.on("console", lambda msg: (
            console_errors.append(f"{msg.type}: {msg.text}") if msg.type in ["error", "warning"] else
            console_logs.append(f"{msg.type}: {msg.text}")
        ))
        
        # Listen to page errors
        page.on("pageerror", lambda exc: page_errors.append(str(exc)))
        
        # Listen to network errors (CORS, 404, etc.)
        page.on("requestfailed", lambda request: 
            network_errors.append(f"{request.url}: {request.failure}")
        )
        
        # Load HTML content via data URL
        logger.info("[IframeValidator] Loading HTML in sandboxed iframe...")
        data_url = f"data:text/html;charset=utf-8;base64,{base64.b64encode(html_content.encode()).decode()}"
        
        try:
            await page.goto(data_url, wait_until="networkidle", timeout=timeout_ms)
        except Exception as load_err:
            logger.warning(f"[IframeValidator] Page load timeout/error: {load_err}")
            # Continue anyway - we still want to capture errors
        
        # Wait a bit for any lazy-loaded content
        await asyncio.sleep(2)
        
        # Wait for images to load or fail (give them time to complete)
        try:
            await page.evaluate("""
                () => {
                    return new Promise((resolve) => {
                        const images = Array.from(document.querySelectorAll('img'));
                        if (images.length === 0) {
                            resolve();
                            return;
                        }
                        
                        let loadedCount = 0;
                        const checkComplete = () => {
                            loadedCount++;
                            if (loadedCount === images.length) {
                                resolve();
                            }
                        };
                        
                        images.forEach(img => {
                            if (img.complete) {
                                checkComplete();
                            } else {
                                img.addEventListener('load', checkComplete);
                                img.addEventListener('error', checkComplete);
                                // Timeout per image after 5 seconds
                                setTimeout(checkComplete, 5000);
                            }
                        });
                    });
                }
            """)
            logger.debug("[IframeValidator] All images loaded or timed out")
        except Exception as img_wait_err:
            logger.warning(f"[IframeValidator] Image wait failed: {img_wait_err}")
        
        # Extract page structure (better than screenshot for AI analysis)
        page_snippet = None
        try:
            # Get structured page content (semantic elements with text)
            page_snippet = await page.evaluate("""
                () => {
                    const elements = document.body.querySelectorAll('h1, h2, h3, h4, p, button, a, nav, footer, header, section, article');
                    return Array.from(elements).slice(0, 50).map(el => ({
                        tag: el.tagName.toLowerCase(),
                        text: el.textContent?.trim().substring(0, 150) || '',
                        classes: el.className,
                        visible: el.offsetParent !== null
                    })).filter(item => item.text.length > 0);
                }
            """)
            logger.info(f"[IframeValidator] Page snippet captured ({len(page_snippet)} elements)")
        except Exception as snippet_err:
            logger.warning(f"[IframeValidator] Page snippet extraction failed: {snippet_err}")
        
        # Comprehensive image validation
        image_validation = None
        try:
            image_validation = await page.evaluate("""
                () => {
                    const images = Array.from(document.querySelectorAll('img'));
                    const viewport = {
                        width: window.innerWidth,
                        height: window.innerHeight
                    };
                    
                    const results = images.map(img => {
                        const rect = img.getBoundingClientRect();
                        const computedStyle = window.getComputedStyle(img);
                        
                        // Check if image loaded successfully
                        const loaded = img.complete && img.naturalWidth > 0;
                        
                        // Get actual dimensions
                        const naturalWidth = img.naturalWidth;
                        const naturalHeight = img.naturalHeight;
                        const displayWidth = rect.width;
                        const displayHeight = rect.height;
                        
                        // Check if image is oversized (much larger than display size)
                        const isOversized = naturalWidth > displayWidth * 2 || naturalHeight > displayHeight * 2;
                        
                        // Check if image is too small (pixelated)
                        const isTooSmall = naturalWidth < displayWidth * 0.8 && displayWidth > 100;
                        
                        // Check if image breaks layout (overflows viewport)
                        const overflowsViewport = displayWidth > viewport.width * 1.1;
                        
                        // Check aspect ratio preservation
                        const naturalAspect = naturalWidth / naturalHeight;
                        const displayAspect = displayWidth / displayHeight;
                        const aspectRatioDistorted = Math.abs(naturalAspect - displayAspect) > 0.15;
                        
                        // Check if text overlay exists and get contrast info
                        let hasTextOverlay = false;
                        let textOverlayInfo = null;
                        const parent = img.parentElement;
                        if (parent) {
                            const parentStyle = window.getComputedStyle(parent);
                            const siblings = Array.from(parent.children);
                            const hasTextSiblings = siblings.some(el => 
                                el !== img && el.textContent?.trim().length > 0
                            );
                            
                            if (hasTextSiblings || parentStyle.position === 'relative') {
                                hasTextOverlay = true;
                                // Get text elements that might be overlaying
                                const textElements = siblings.filter(el => 
                                    el !== img && 
                                    el.textContent?.trim().length > 0 &&
                                    window.getComputedStyle(el).position === 'absolute'
                                );
                                if (textElements.length > 0) {
                                    textOverlayInfo = {
                                        count: textElements.length,
                                        colors: textElements.map(el => window.getComputedStyle(el).color),
                                        backgrounds: textElements.map(el => window.getComputedStyle(el).backgroundColor)
                                    };
                                }
                            }
                        }
                        
                        return {
                            src: img.src.substring(0, 100),
                            alt: img.alt || '(no alt text)',
                            loaded,
                            naturalWidth,
                            naturalHeight,
                            displayWidth: Math.round(displayWidth),
                            displayHeight: Math.round(displayHeight),
                            isOversized,
                            isTooSmall,
                            overflowsViewport,
                            aspectRatioDistorted,
                            hasTextOverlay,
                            textOverlayInfo,
                            visible: rect.width > 0 && rect.height > 0,
                            position: {
                                top: Math.round(rect.top),
                                left: Math.round(rect.left)
                            }
                        };
                    });
                    
                    // Summary statistics
                    const summary = {
                        total: images.length,
                        loaded: results.filter(r => r.loaded).length,
                        failed: results.filter(r => !r.loaded).length,
                        oversized: results.filter(r => r.isOversized).length,
                        tooSmall: results.filter(r => r.isTooSmall).length,
                        overflowing: results.filter(r => r.overflowsViewport).length,
                        distorted: results.filter(r => r.aspectRatioDistorted).length,
                        withTextOverlay: results.filter(r => r.hasTextOverlay).length
                    };
                    
                    return {
                        viewport,
                        summary,
                        images: results
                    };
                }
            """)
            logger.info(
                f"[IframeValidator] Image validation complete | "
                f"total: {image_validation['summary']['total']} | "
                f"loaded: {image_validation['summary']['loaded']} | "
                f"failed: {image_validation['summary']['failed']}"
            )
        except Exception as img_err:
            logger.warning(f"[IframeValidator] Image validation failed: {img_err}")
        
        # Take screenshot for visual validation (PNG for better quality)
        screenshot_base64 = None
        try:
            # Use PNG for text-heavy UI, full_page=False for viewport only (faster)
            screenshot_bytes = await page.screenshot(full_page=False, type="png")
            screenshot_base64 = base64.b64encode(screenshot_bytes).decode()
            logger.info(f"[IframeValidator] Screenshot captured for visual validation ({len(screenshot_base64)} bytes)")
        except Exception as screenshot_err:
            logger.warning(f"[IframeValidator] Screenshot failed: {screenshot_err}")
        
        # Collect all errors
        all_errors = []
        
        # Check for CSP (Content Security Policy) violations - CRITICAL
        csp_errors = [
            err for err in console_errors + network_errors 
            if "content security policy" in err.lower() or 
               "csp" in err.lower() or
               "refused to load" in err.lower() or
               "refused to apply" in err.lower() or
               "refused to execute" in err.lower() or
               "blocked by content security policy" in err.lower()
        ]
        if csp_errors:
            all_errors.extend([f"🔴 CSP Violation: {err}" for err in csp_errors[:10]])  # Show more CSP errors
        
        # Check for CORS errors specifically - CRITICAL
        cors_errors = [
            err for err in console_errors + network_errors 
            if "cors" in err.lower() or 
               "cross-origin" in err.lower() or
               "no 'access-control-allow-origin'" in err.lower()
        ]
        if cors_errors:
            all_errors.extend([f"🔴 CORS Error: {err}" for err in cors_errors[:5]])
        
        # Check for stylesheet/style loading errors - MAJOR
        style_errors = [
            err for err in console_errors + network_errors
            if "stylesheet" in err.lower() or
               "failed to load.*css" in err.lower() or
               ("refused to apply" in err.lower() and "style" in err.lower())
        ]
        if style_errors:
            all_errors.extend([f"⚠️ Style Error: {err}" for err in style_errors[:5]])
        
        # Check for other critical console errors
        critical_console_errors = [
            err for err in console_errors 
            if "error:" in err.lower() and 
               err not in csp_errors and 
               err not in cors_errors and
               err not in style_errors
        ]
        if critical_console_errors:
            all_errors.extend([f"❌ Console Error: {err}" for err in critical_console_errors[:5]])
        
        # Check for page JavaScript errors
        if page_errors:
            all_errors.extend([f"❌ Page Error: {err}" for err in page_errors[:5]])
        
        # Check if page is blank (no visible content)
        try:
            body_text = await page.inner_text("body")
            if not body_text or len(body_text.strip()) < 50:
                all_errors.append("Page appears blank or has minimal content")
        except Exception:
            all_errors.append("Failed to read page content - page may not have loaded")
        
        # Image validation errors
        if image_validation:
            summary = image_validation['summary']
            
            # Failed to load images
            if summary['failed'] > 0:
                failed_imgs = [img for img in image_validation['images'] if not img['loaded']]
                # Show first 3 failed images with their URLs
                failed_urls = [img['src'][:100] + '...' if len(img['src']) > 100 else img['src'] for img in failed_imgs[:3]]
                all_errors.append(
                    f"❌ {summary['failed']} image(s) failed to load. Check these URLs are valid and accessible:\n"
                    + "\n".join([f"  • {url}" for url in failed_urls])
                )
            
            # Oversized images (performance issue)
            if summary['oversized'] > 0:
                oversized_imgs = [img for img in image_validation['images'] if img['isOversized']]
                all_errors.append(
                    f"⚠️ {summary['oversized']} image(s) are oversized (source is 2x+ larger than display). "
                    f"Example: {oversized_imgs[0]['src']}... is {oversized_imgs[0]['naturalWidth']}x{oversized_imgs[0]['naturalHeight']} "
                    f"but displayed at {oversized_imgs[0]['displayWidth']}x{oversized_imgs[0]['displayHeight']}. "
                    f"Use smaller images or add responsive srcset."
                )
            
            # Too small images (quality issue)
            if summary['tooSmall'] > 0:
                small_imgs = [img for img in image_validation['images'] if img['isTooSmall']]
                all_errors.append(
                    f"⚠️ {summary['tooSmall']} image(s) are too small (will appear pixelated). "
                    f"Example: {small_imgs[0]['src']}... is {small_imgs[0]['naturalWidth']}x{small_imgs[0]['naturalHeight']} "
                    f"but displayed at {small_imgs[0]['displayWidth']}x{small_imgs[0]['displayHeight']}. "
                    f"Use higher resolution images."
                )
            
            # Images breaking layout
            if summary['overflowing'] > 0:
                overflow_imgs = [img for img in image_validation['images'] if img['overflowsViewport']]
                all_errors.append(
                    f"🔴 {summary['overflowing']} image(s) overflow the viewport (breaking layout). "
                    f"Example: {overflow_imgs[0]['src']}... is {overflow_imgs[0]['displayWidth']}px wide "
                    f"(viewport: {image_validation['viewport']['width']}px). "
                    f"Add max-width: 100% or use responsive CSS."
                )
            
            # Distorted aspect ratios
            if summary['distorted'] > 0:
                distorted_imgs = [img for img in image_validation['images'] if img['aspectRatioDistorted']]
                all_errors.append(
                    f"⚠️ {summary['distorted']} image(s) have distorted aspect ratios. "
                    f"Use object-fit: cover or object-fit: contain to preserve aspect ratio."
                )
            
            # Text overlays (potential readability issues)
            if summary['withTextOverlay'] > 0:
                overlay_imgs = [img for img in image_validation['images'] if img['hasTextOverlay'] and img['textOverlayInfo']]
                if overlay_imgs:
                    first = overlay_imgs[0]
                    all_errors.append(
                        f"💬 {summary['withTextOverlay']} image(s) have text overlays. "
                        f"Ensure sufficient contrast for readability. "
                        f"Consider adding text shadows, dark overlays, or ensuring text color contrasts with image."
                    )
        
        passed = len(all_errors) == 0
        
        logger.info(
            f"[IframeValidator] Validation complete | "
            f"passed: {passed} | "
            f"errors: {len(all_errors)} | "
            f"console_logs: {len(console_logs)} | "
            f"has_screenshot: {screenshot_base64 is not None}"
        )
        
        return {
            "passed": passed,
            "errors": all_errors,
            "page_snippet": page_snippet,  # Structured page content (better for AI)
            "image_validation": image_validation,  # Comprehensive image analysis
            "screenshot": screenshot_base64,  # Optional debug screenshot
            "console_logs": console_logs[:20],  # Limit console logs
            "console_errors": console_errors,
            "network_errors": network_errors,
            "page_errors": page_errors
        }
        
    except Exception as e:
        logger.warning(f"[IframeValidator] Skipping iframe validation due to error: {e}")
        # Don't block build - gracefully degrade
        return {
            "passed": True,  # Don't fail the build
            "errors": [],
            "page_snippet": None,
            "image_validation": None,
            "screenshot": None,
            "console_logs": [f"Iframe validation skipped: {str(e)}"],
            "console_errors": [],
            "network_errors": [],
            "page_errors": []
        }
    
    finally:
        # Cleanup
        if page:
            try:
                await page.close()
            except Exception:
                pass
        if browser:
            try:
                await browser.close()
            except Exception:
                pass
        try:
            await playwright.stop()
        except Exception:
            pass

