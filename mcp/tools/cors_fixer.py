"""
CORS Fixer - Deterministic HTML rewriting to fix CORS/XFO/CSP issues
Applies minimal changes based on structured findings from sandbox renderer
"""
from typing import Dict, Any, List
from bs4 import BeautifulSoup
import re
import logging

logger = logging.getLogger(__name__)

# Known CDNs with permissive CORS
CORS_FRIENDLY_CDNS = {
    'fonts': {
        'Inter': 'https://cdnjs.cloudflare.com/ajax/libs/inter-ui/4.0.2/inter.css',
        'Roboto': 'https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;500;700&display=swap',
        'Open Sans': 'https://fonts.googleapis.com/css2?family=Open+Sans:wght@300;400;600;700&display=swap',
        'Lato': 'https://fonts.googleapis.com/css2?family=Lato:wght@300;400;700&display=swap',
    },
    'fallback_cdn': 'https://cdnjs.cloudflare.com'
}


class CORSFixer:
    """Apply deterministic fixes to HTML based on findings"""
    
    def __init__(self, html: str):
        self.html = html
        self.soup = BeautifulSoup(html, 'html.parser')
        self.changes: List[str] = []
    
    def rewrite_html(self, findings: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Apply fixes for all findings.
        Returns fixed HTML and list of changes made.
        """
        # Group findings by code for efficient processing
        findings_by_code = {}
        for finding in findings:
            code = finding.get('code', 'UNKNOWN')
            if code not in findings_by_code:
                findings_by_code[code] = []
            findings_by_code[code].append(finding)
        
        # Apply fixes in order (most critical first)
        if 'MISSING_NOOPENER' in findings_by_code:
            self._fix_target_blank()
        
        if 'FORBIDDEN_MAPS_LINK' in findings_by_code:
            self._remove_maps_links()
        
        if 'MISSING_CROSSORIGIN' in findings_by_code:
            self._add_crossorigin()
        
        if 'CORS_FONT_NO_ACAO' in findings_by_code:
            self._fix_font_cors(findings_by_code['CORS_FONT_NO_ACAO'])
        
        if 'MIXED_CONTENT' in findings_by_code:
            self._fix_mixed_content(findings_by_code['MIXED_CONTENT'])
        
        if 'HTTP_ERROR' in findings_by_code:
            self._replace_broken_resources(findings_by_code['HTTP_ERROR'])
        
        # CSP meta tag normalization
        self._normalize_csp()
        
        # Remove inline event handlers
        self._remove_inline_handlers()
        
        return {
            'html': str(self.soup),
            'changes': self.changes
        }
    
    def _fix_target_blank(self):
        """Add rel="noopener noreferrer" to all target="_blank" links"""
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
                rel_list.extend(['noopener', 'noreferrer'])
                link['rel'] = rel_list
                self.changes.append(f'Added rel="noopener noreferrer" to link: {link.get("href", "")[:50]}')
    
    def _remove_maps_links(self):
        """Remove all Google Maps links"""
        maps_selectors = [
            'a[href*="google.com/maps"]',
            'a[href*="maps.google."]'
        ]
        for selector in maps_selectors:
            links = self.soup.select(selector)
            for link in links:
                link.decompose()
                self.changes.append('Removed Google Maps link')
    
    def _add_crossorigin(self):
        """Add crossorigin="anonymous" to cross-origin resources"""
        # Stylesheets
        for link in self.soup.find_all('link', rel='stylesheet'):
            href = link.get('href', '')
            if href.startswith('http') and not link.get('crossorigin'):
                link['crossorigin'] = 'anonymous'
                self.changes.append(f'Added crossorigin to stylesheet: {href[:50]}')
        
        # Preload links
        for link in self.soup.find_all('link', rel='preload'):
            href = link.get('href', '')
            if href.startswith('http') and not link.get('crossorigin'):
                link['crossorigin'] = 'anonymous'
                self.changes.append(f'Added crossorigin to preload: {href[:50]}')
        
        # Scripts
        for script in self.soup.find_all('script', src=True):
            src = script.get('src', '')
            if src.startswith('http') and not script.get('crossorigin'):
                script['crossorigin'] = 'anonymous'
                self.changes.append(f'Added crossorigin to script: {src[:50]}')
    
    def _fix_font_cors(self, findings: List[Dict[str, Any]]):
        """Fix font CORS issues by switching to CORS-friendly CDNs"""
        head = self.soup.find('head')
        if not head:
            return
        
        # Add preconnect to CORS-friendly CDN
        preconnect = self.soup.new_tag('link', rel='preconnect', 
                                       href=CORS_FRIENDLY_CDNS['fallback_cdn'],
                                       attrs={'crossorigin': ''})
        head.insert(0, preconnect)
        self.changes.append('Added preconnect to CORS-friendly CDN')
        
        # Try to detect and replace font families
        for finding in findings:
            url = finding.get('url', '')
            # Extract font family name from URL
            for font_name, cors_url in CORS_FRIENDLY_CDNS['fonts'].items():
                if font_name.lower().replace(' ', '-') in url.lower():
                    # Find and replace stylesheet
                    for link in self.soup.find_all('link', rel='stylesheet'):
                        if font_name.lower() in link.get('href', '').lower():
                            link['href'] = cors_url
                            link['crossorigin'] = 'anonymous'
                            self.changes.append(f'Switched {font_name} to CORS-friendly CDN')
                            break
    
    def _fix_mixed_content(self, findings: List[Dict[str, Any]]):
        """Upgrade http:// to https:// for all resources"""
        for finding in findings:
            url = finding.get('url', '')
            if url.startswith('http://'):
                https_url = url.replace('http://', 'https://', 1)
                
                # Replace in all relevant tags
                for tag in self.soup.find_all(['link', 'script', 'img', 'a', 'iframe']):
                    for attr in ['href', 'src']:
                        if tag.get(attr) == url:
                            tag[attr] = https_url
                            self.changes.append(f'Upgraded to HTTPS: {url[:50]}')
    
    def _replace_broken_resources(self, findings: List[Dict[str, Any]]):
        """Replace broken resources with placeholders"""
        for finding in findings:
            url = finding.get('url', '')
            status = finding.get('status', 0)
            
            # Images: replace with data URI placeholder
            if any(ext in url.lower() for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg']):
                # 1x1 transparent PNG data URI
                placeholder = 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII='
                for img in self.soup.find_all('img', src=url):
                    img['src'] = placeholder
                    img['alt'] = f'Image unavailable (HTTP {status})'
                    self.changes.append(f'Replaced broken image: {url[:50]}')
            
            # CSS: remove broken stylesheet links
            elif '.css' in url.lower():
                for link in self.soup.find_all('link', href=url):
                    link.decompose()
                    self.changes.append(f'Removed broken stylesheet: {url[:50]}')
            
            # JS: remove broken scripts
            elif '.js' in url.lower():
                for script in self.soup.find_all('script', src=url):
                    script.decompose()
                    self.changes.append(f'Removed broken script: {url[:50]}')
    
    def _normalize_csp(self):
        """Normalize CSP meta tag to allow common CDNs"""
        csp_meta = self.soup.find('meta', attrs={'http-equiv': re.compile('Content-Security-Policy', re.I)})
        
        # Default CSP for generated landing pages
        default_csp = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdnjs.cloudflare.com https://cdn.jsdelivr.net https://unpkg.com https://code.jquery.com https://stackpath.bootstrapcdn.com; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://cdnjs.cloudflare.com https://cdn.jsdelivr.net https://unpkg.com https://stackpath.bootstrapcdn.com; "
            "font-src 'self' data: https://fonts.gstatic.com https://cdnjs.cloudflare.com https://cdn.jsdelivr.net; "
            "img-src 'self' data: https: http:; "
            "connect-src 'self'; "
        )
        
        if csp_meta:
            csp_meta['content'] = default_csp
            self.changes.append('Normalized CSP meta tag')
        else:
            # Add CSP meta if missing
            head = self.soup.find('head')
            if head:
                new_csp = self.soup.new_tag('meta', attrs={
                    'http-equiv': 'Content-Security-Policy',
                    'content': default_csp
                })
                head.insert(0, new_csp)
                self.changes.append('Added CSP meta tag')
    
    def _remove_inline_handlers(self):
        """Remove inline event handlers and log them"""
        inline_attrs = ['onclick', 'onload', 'onerror', 'onmouseover', 'onmouseout', 'onchange', 'onsubmit']
        
        for tag in self.soup.find_all():
            for attr in inline_attrs:
                if tag.has_attr(attr):
                    del tag[attr]
                    self.changes.append(f'Removed inline {attr} handler from {tag.name}')


def rewrite_html(html: str, findings: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Main entry point for CORS fixer.
    
    Args:
        html: HTML content to fix
        findings: List of findings from sandbox renderer
        
    Returns:
        Dict with 'html' and 'changes' keys
    """
    fixer = CORSFixer(html)
    return fixer.rewrite_html(findings)

