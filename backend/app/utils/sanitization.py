"""HTML sanitization - Ref: Product.md > Section 6"""

import bleach


def sanitize_html(text: str) -> str:
    """
    Sanitize HTML text.
    Ref: Product.md lines 798-800
    
    Allows only <a> tags with href + rel=noopener noreferrer
    """
    # Configure allowed tags
    allowed_tags = ["a"]
    allowed_attributes = {
        "a": ["href", "rel", "target"]
    }
    
    # Sanitize
    clean = bleach.clean(
        text,
        tags=allowed_tags,
        attributes=allowed_attributes,
        protocols=["http", "https"]
    )
    
    return clean


def escape_html(text: str) -> str:
    """Escape HTML entities"""
    return bleach.clean(text, tags=[], attributes=[])


