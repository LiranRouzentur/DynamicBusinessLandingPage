"""
Pre-write Validator - SECURITY & STRUCTURAL checks ONLY

RESPONSIBILITY: Fast, deterministic validation BEFORE writing files to disk

CHECKS (Critical structural/security issues that block builds):
  ✓ Inline event handlers (onclick, onload, etc.) - SECURITY CRITICAL
  ✓ eval() patterns (eval, new Function, setTimeout(string)) - SECURITY CRITICAL  
  ✓ File size limits (prevent 100MB HTML files)
  ✓ HTML parseability (valid HTML structure)
  ✓ Basic syntax sanity (balanced tags, braces)

DOES NOT CHECK (handled elsewhere):
  ✗ External URLs reachable - MCP qa.validate_static_bundle (network-dependent)
  ✗ Image dimensions/quality - MCP qa.validate_static_bundle (network-dependent)
  ✗ Business fit/SEO/Accessibility - Could use ValidatorAgent LLM (semantic)
  ✗ CSS/JS quality - MCP qa.validate_static_bundle (non-blocking)

ARCHITECTURE:
  - Runs BEFORE file write (fail-fast)
  - No network calls (deterministic)
  - No LLM calls (fast)
  - Blocks build on security violations only

See: mcp/tools/qa.py for complementary MCP validation (network checks)
"""
from typing import Dict, Any
from bs4 import BeautifulSoup
import re


# Fast deterministic pre-write validation: checks security (no inline handlers, eval), HTML parseability, CSP domains, file size.
# Returns (is_valid, errors_list); blocks build on critical issues before file I/O; complements MCP network validation.
def validate_generator_output_structure(gen_out: Dict[str, Any], mapper_data: Dict[str, Any] = None) -> tuple[bool, list[str]]:
    """
    Fast, deterministic validation of generator output BEFORE writing files.
    
    Only checks CRITICAL structural issues that would prevent files from working:
    - Schema validation (handled by Pydantic, but check keys exist)
    - HTML parseability (can be parsed, not malformed)
    - File size sanity (not too large)
    - Basic syntax checks (no obvious errors)
    - CSP domain validation (images from allowed domains only)
    
    Args:
        gen_out: Generator output dict with html (single inline HTML file)
        mapper_data: Optional mapper data containing business_page_url for dynamic CSP validation
        
    Returns:
        (is_valid, list_of_errors)
        - is_valid: True if structure is OK to write
        - list_of_errors: List of error messages if invalid
    """
    errors = []
    
    # 1. Check required key exists (single HTML file)
    if "html" not in gen_out:
        errors.append("Missing required field: html")
        return (False, errors)
    if not isinstance(gen_out["html"], str):
        errors.append("Field html must be a string")
        return (False, errors)
    if len(gen_out["html"]) == 0:
        errors.append("Field html is empty")
        return (False, errors)
    
    html = gen_out["html"]
    
    # 2. Check HTML parseability and critical security patterns (critical - malformed HTML breaks everything)
    try:
        soup = BeautifulSoup(html, "html.parser")
        # Check for basic HTML structure
        if not soup.find("html"):
            errors.append("HTML missing <html> tag")
        # Don't check for DOCTYPE, title, meta - those are quality issues, not structural
        
        # 2.1 Check for inline scripts with code (allowed for single-file HTML)
        # Note: Inline scripts are now allowed per single-file output requirement
        
        # 2.2 Check for inline event handlers (CRITICAL SECURITY - will block build)
        # IMPORTANT: Only match HTML attributes, NOT JavaScript property assignments
        # Pattern explanation: <[^>]*\s matches opening tag with whitespace before attribute
        # This prevents false positives on JavaScript like "imageLoader.onload = function()"
        inline_handlers = re.findall(r'<[^>]*\s(on(?:click|load|submit|change|focus|blur|mouseover|mouseout|keydown|keyup))\s*=', html, re.IGNORECASE)
        if inline_handlers:
            handler_types = set(inline_handlers[:3])  # Show up to 3 types
            errors.append(
                f"SECURITY VIOLATION: Inline HTML event handlers detected: {', '.join(f'{h}=' for h in handler_types)}. "
                f"FIX: Remove ALL 'on*=' attributes from HTML tags. Instead, use addEventListener in your <script> tag. "
                f"Example: Replace <button onclick='...'> with <button id='myBtn'> and add "
                f"document.getElementById('myBtn').addEventListener('click', function() {{ ... }}) in <script>."
            )
        
    except Exception as e:
        errors.append(f"HTML parse error: {str(e)}")
    
    # 2.3 Check JavaScript for eval() patterns (CRITICAL SECURITY - will block build)
    # Check inline scripts in HTML
    eval_patterns = [
        (r'\beval\s*\(', 'eval()'),
        (r'\bnew\s+Function\s*\(', 'new Function()'),
        (r'setTimeout\s*\(\s*["\']', 'setTimeout(string)'),
        (r'setInterval\s*\(\s*["\']', 'setInterval(string)'),
    ]
    for pattern, name in eval_patterns:
        if re.search(pattern, html):
            errors.append(f"SECURITY: {name} detected in JavaScript. This will cause build failure.")
            break  # Only report first occurrence
    
    # 2.4 Check image src URLs for CSP violations (CRITICAL - blocked images break page)
    # Extract all image URLs from src attributes
    img_urls = re.findall(r'<img[^>]+src\s*=\s*["\']([^"\']+)["\']', html, re.IGNORECASE)
    
    # CSP-allowed image domains (must match the CSP in generator_prompt.py)
    # STRICT: Only Google API images and free stock images allowed
    allowed_domains = [
        'googleusercontent.com',  # Matches *.googleusercontent.com (Google Places/API images)
        'images.unsplash.com',    # Unsplash CDN
        'images.pexels.com',      # Pexels CDN
        'pixabay.com',            # Matches *.pixabay.com
        'upload.wikimedia.org',   # Wikimedia Commons
    ]
    
    # NOTE: Business website domains are NOT added to avoid CORS issues with logos and external assets
    
    # Allowed URL schemes
    allowed_schemes = ['data:', 'blob:']
    
    csp_violations = []
    for img_url in img_urls:
        # Skip data: and blob: URIs
        if any(img_url.startswith(scheme) for scheme in allowed_schemes):
            continue
        
        # Check if URL matches any allowed domain
        url_lower = img_url.lower()
        if not any(domain in url_lower for domain in allowed_domains):
            # Extract domain from URL for error message
            domain_match = re.search(r'https?://([^/]+)', img_url)
            blocked_domain = domain_match.group(1) if domain_match else 'unknown'
            csp_violations.append(f"{blocked_domain} (from: {img_url[:80]}...)")
    
    if csp_violations:
        # Limit to first 3 violations for readability
        violation_list = '; '.join(csp_violations[:3])
        errors.append(
            f"CSP VIOLATION: Image URLs from unauthorized domains detected: {violation_list}. "
            f"ONLY these domains are allowed: {', '.join(allowed_domains)}. "
            f"FIX: Use ONLY the image URLs provided in mapper_data (logo_url, business_images_urls, stock_images_urls). "
            f"Do NOT fetch images from business websites or other external domains."
        )
    
    # 2.5 Check for forms (FORBIDDEN - CTA-free requirement)
    # Check for form elements which violate the CTA-free requirement
    has_forms = re.search(r'<form[^>]*>', html, re.IGNORECASE)
    has_inputs = re.search(r'<input[^>]*>', html, re.IGNORECASE)
    has_textareas = re.search(r'<textarea[^>]*>', html, re.IGNORECASE)
    has_selects = re.search(r'<select[^>]*>', html, re.IGNORECASE)
    
    if has_forms or has_inputs or has_textareas or has_selects:
        errors.append(
            "FORBIDDEN: Forms and form fields detected. This is a CTA-free landing page. "
            "Remove ALL <form>, <input>, <textarea>, and <select> elements. "
            "The page must be purely informational with NO interactive forms or contact CTAs."
        )
    
    # 2.6 Check CSS @import rules position (must be at top of stylesheet)
    # Extract all <style> blocks
    style_blocks = re.findall(r'<style[^>]*>([\s\S]*?)</style>', html, re.IGNORECASE)
    for i, style_content in enumerate(style_blocks):
        # Find all @import statements
        import_matches = list(re.finditer(r'@import\s+', style_content, re.IGNORECASE))
        if import_matches:
            # Check if there are any non-comment, non-whitespace CSS rules before @import
            # Find position of first @import
            first_import_pos = import_matches[0].start()
            # Get content before first @import
            content_before = style_content[:first_import_pos].strip()
            # Remove comments (/* ... */)
            content_before = re.sub(r'/\*[\s\S]*?\*/', '', content_before).strip()
            # Check if there's any CSS rule before @import (look for { which indicates a rule)
            if '{' in content_before or '}' in content_before:
                errors.append(
                    f"CSS @import rules must be at the TOP of the <style> block (found in style block #{i+1}). "
                    f"All @import statements must appear BEFORE any other CSS rules. "
                    f"Move all @import url(...) statements to the very beginning of your <style> tag."
                )
                break  # Only report once
    
    # 3. Check file size (sanity check - prevent outrageously large file)
    max_html_size = 5 * 1024 * 1024  # 5MB (includes inline CSS/JS)
    
    if len(html) > max_html_size:
        errors.append(f"HTML too large: {len(html)} bytes (max {max_html_size})")
    
    # 4. Check for critical syntax errors in HTML (basic check)
    # Check for unclosed tags that would break parsing (basic heuristic)
    open_tags = re.findall(r'<(\w+)[^>]*>', html)
    close_tags = re.findall(r'</(\w+)>', html)
    # Self-closing tags
    self_closing = ['img', 'br', 'hr', 'input', 'meta', 'link', 'area', 'base', 'col', 'embed', 'source', 'track', 'wbr']
    open_tags = [tag for tag in open_tags if tag.lower() not in self_closing]
    close_tags = [tag for tag in close_tags if tag.lower() not in self_closing]
    
    # Simple check: if we have way more open than close, might be malformed
    # But don't be too strict - complex HTML might have nested structures
    # Only fail if completely unbalanced (e.g., 5x more open than close)
    if len(open_tags) > 0 and len(close_tags) > 0:
        ratio = len(open_tags) / len(close_tags) if len(close_tags) > 0 else 0
        if ratio > 5.0:  # Way too many unclosed tags
            errors.append("HTML appears to have many unclosed tags (may be malformed)")
    
    # 5. Basic inline JS syntax check - look for critical syntax errors in <script> tags
    # Check for unmatched braces/brackets/parens (basic heuristic)
    script_content = re.findall(r'<script[^>]*>([\s\S]*?)</script>', html, re.IGNORECASE)
    if script_content:
        inline_js = ' '.join(script_content)
        js_braces = inline_js.count('{') - inline_js.count('}')
        js_brackets = inline_js.count('[') - inline_js.count(']')
        js_parens = inline_js.count('(') - inline_js.count(')')
        
        if abs(js_braces) > 5 or abs(js_brackets) > 5 or abs(js_parens) > 5:
            errors.append("Inline JS appears to have many unmatched braces/brackets/parens (may be malformed)")
    
    # Return True if no critical errors
    is_valid = len(errors) == 0
    return (is_valid, errors)

