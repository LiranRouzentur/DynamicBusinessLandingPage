"""
HTML Fixer - Automatically fixes validation errors in HTML
"""
from typing import Dict, Any, List, Optional
from bs4 import BeautifulSoup
import re
import logging

logger = logging.getLogger(__name__)


class HTMLFixer:
    """Automatically fixes common HTML validation errors"""
    
    def __init__(self, html: str):
        self.html = html
        self.soup = BeautifulSoup(html, 'html.parser')
        self.fixes_applied = []
        self.remaining_errors = []
    
    def fix(self, errors: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Apply fixes for validation errors.
        
        Args:
            errors: List of validation errors with id, severity, category, hint, where, etc.
            
        Returns:
            Dict with fixed_html, fixes_applied, and remaining_errors
        """
        # Filter to only error-level issues (warnings are informative)
        critical_errors = [e for e in errors if e.get('severity') == 'error']
        
        for error in critical_errors:
            error_id = error.get('id', '')
            
            try:
                if error_id == 'TARGET_BLANK_NO_NOOPENER':
                    self._fix_target_blank_noopener()
                elif error_id == 'MISSING_ALT_TEXT':
                    self._fix_missing_alt_text()
                elif error_id == 'MISSING_VIEWPORT':
                    self._fix_missing_viewport()
                elif error_id == 'MISSING_TITLE':
                    self._fix_missing_title()
                elif error_id == 'EVAL_USAGE':
                    self._fix_eval_usage()
                elif error_id == 'MISSING_HEAD':
                    self._fix_missing_head()
                elif error_id == 'MISSING_BODY':
                    self._fix_missing_body()
                elif error_id == 'INVALID_HTML_STRUCTURE':
                    self._fix_invalid_html_structure()
                else:
                    # Unknown error - mark as remaining
                    self.remaining_errors.append(error)
                    
            except Exception as e:
                logger.warning(f"Failed to fix error {error_id}: {e}")
                self.remaining_errors.append(error)
        
        # Get fixed HTML
        fixed_html = str(self.soup)
        
        return {
            'fixed_html': fixed_html,
            'fixes_applied': self.fixes_applied,
            'remaining_errors': self.remaining_errors
        }
    
    def _fix_target_blank_noopener(self):
        """Fix links with target="_blank" missing rel="noopener noreferrer" """
        links = self.soup.find_all('a', target='_blank')
        for link in links:
            rel = link.get('rel', [])
            if isinstance(rel, str):
                rel_list = rel.split()
            elif isinstance(rel, list):
                rel_list = rel
            else:
                rel_list = []
            
            rel_lower = ' '.join(rel_list).lower()
            if 'noopener' not in rel_lower or 'noreferrer' not in rel_lower:
                if rel_list:
                    rel_list.extend(['noopener', 'noreferrer'])
                else:
                    rel_list = ['noopener', 'noreferrer']
                link['rel'] = rel_list
                self.fixes_applied.append('TARGET_BLANK_NO_NOOPENER')
    
    def _fix_missing_alt_text(self):
        """Add empty alt text to images missing alt attribute"""
        images = self.soup.find_all('img')
        for img in images:
            if img.get('alt') is None:
                img['alt'] = ''  # Empty alt for decorative images
                self.fixes_applied.append('MISSING_ALT_TEXT')
    
    def _fix_missing_viewport(self):
        """Add viewport meta tag if missing"""
        head = self.soup.find('head')
        if not head:
            head = self.soup.new_tag('head')
            if self.soup.html:
                self.soup.html.insert(0, head)
            else:
                self.soup.insert(0, head)
        
        viewport = head.find('meta', attrs={'name': 'viewport'})
        if not viewport:
            viewport = self.soup.new_tag('meta', attrs={
                'name': 'viewport',
                'content': 'width=device-width, initial-scale=1'
            })
            head.insert(0, viewport)
            self.fixes_applied.append('MISSING_VIEWPORT')
    
    def _fix_missing_title(self):
        """Add or fix title tag"""
        head = self.soup.find('head')
        if not head:
            head = self.soup.new_tag('head')
            if self.soup.html:
                self.soup.html.insert(0, head)
            else:
                self.soup.insert(0, head)
        
        title = head.find('title')
        if not title or not title.string or not title.string.strip():
            if title:
                title.string = 'Business Landing Page'
            else:
                title = self.soup.new_tag('title')
                title.string = 'Business Landing Page'
                head.insert(0, title)
            self.fixes_applied.append('MISSING_TITLE')
    
    def _fix_eval_usage(self):
        """Remove or comment out eval() and Function() usage in scripts"""
        scripts = self.soup.find_all('script')
        for script in scripts:
            if script.string:
                content = script.string
                # Check for eval or Function
                if 'eval(' in content or 'Function(' in content:
                    # Comment out dangerous code
                    script.string = f"/* SECURITY FIX: eval/Function removed */\n{content}"
                    self.fixes_applied.append('EVAL_USAGE')
    
    def _fix_missing_head(self):
        """Ensure head tag exists"""
        if not self.soup.find('head'):
            head = self.soup.new_tag('head')
            if self.soup.html:
                self.soup.html.insert(0, head)
            else:
                self.soup.insert(0, head)
            self.fixes_applied.append('MISSING_HEAD')
    
    def _fix_missing_body(self):
        """Ensure body tag exists"""
        if not self.soup.find('body'):
            body = self.soup.new_tag('body')
            if self.soup.html:
                self.soup.html.append(body)
                # Move any content that's outside body into body
                for element in list(self.soup.html.children):
                    if element.name != 'head' and element.name is not None:
                        body.append(element.extract())
            else:
                self.soup.append(body)
            self.fixes_applied.append('MISSING_BODY')
    
    def _fix_invalid_html_structure(self):
        """Ensure proper HTML5 structure"""
        # Ensure html tag exists
        if not self.soup.find('html'):
            # Create proper structure
            html_tag = self.soup.new_tag('html')
            html_tag['lang'] = 'en'
            
            # Move existing content
            existing_content = []
            for element in list(self.soup.children):
                if element.name is not None:
                    existing_content.append(element.extract())
            
            self.soup.clear()
            self.soup.append(html_tag)
            
            # Ensure head and body
            head = self.soup.find('head') or self.soup.new_tag('head')
            body = self.soup.find('body') or self.soup.new_tag('body')
            
            html_tag.append(head)
            html_tag.append(body)
            
            # Move content appropriately
            for element in existing_content:
                if element.name in ['meta', 'title', 'link', 'style', 'script']:
                    head.append(element)
                else:
                    body.append(element)
            
            self.fixes_applied.append('INVALID_HTML_STRUCTURE')


def prepare_visual_validation_prompt(screenshot_base64: str, errors: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Prepare visual validation prompt with screenshot for agent review.
    
    Args:
        screenshot_base64: Base64-encoded PNG screenshot
        errors: List of validation errors that were fixed
        
    Returns:
        Dict with prompt and screenshot for agent to validate visual alignment
    """
    error_summary = "\n".join([
        f"- {err.get('id', 'UNKNOWN')}: {err.get('message', err.get('hint', 'No description'))}"
        for err in errors[:10]
    ])
    
    if len(errors) > 10:
        error_summary += f"\n- ...and {len(errors) - 10} more issues"
    
    prompt = f"""Visual Validation Required

The following issues were automatically fixed:
{error_summary}

Please review the attached screenshot of the rendered page and confirm:
1. All page elements are properly aligned
2. Images load correctly and are positioned as intended
3. Text is readable and not overlapping
4. Colors and styling look correct
5. Layout is responsive and professional

If you see any visual issues, describe them clearly so they can be fixed."""

    return {
        "prompt": prompt,
        "screenshot_base64": screenshot_base64,
        "errors_fixed": len(errors)
    }


def fix_html_errors(html: str, errors: List[Dict[str, Any]], screenshot_base64: Optional[str] = None) -> Dict[str, Any]:
    """
    Main entry point for fixing HTML validation errors.
    
    Args:
        html: HTML content to fix
        errors: List of validation errors
        screenshot_base64: Optional screenshot of rendered page for visual validation
        
    Returns:
        Dict with fixed_html, fixes_applied, remaining_errors, and visual_validation_prompt
    """
    fixer = HTMLFixer(html)
    result = fixer.fix(errors)
    
    # Add visual validation prompt with screenshot if available
    if screenshot_base64:
        result['visual_validation'] = prepare_visual_validation_prompt(screenshot_base64, errors)
        logger.info(f"[Fixer] Prepared visual validation prompt with screenshot ({len(screenshot_base64)} chars base64)")
    
    return result

