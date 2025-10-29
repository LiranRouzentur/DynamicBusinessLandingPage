"""Mapper agent response schemas based on mapper_agent_prompt_with_qa.md"""
from pydantic import BaseModel
from typing import List, Dict, Any, Optional


class BrandColors(BaseModel):
    """Brand color palette"""
    primary: str  # Hex color #RRGGBB
    secondary: str  # Hex color #RRGGBB


class Assets(BaseModel):
    """Business assets"""
    logo_url: Optional[str] = None  # Absolute URL to logo image
    business_images_urls: Optional[List[str]] = None  # List of business image URLs
    stock_images_urls: Optional[List[str]] = None  # List of stock image URLs (whitelisted sources only)
    brand_colors: BrandColors


class QACheck(BaseModel):
    """Individual QA check result"""
    name: str
    passed: bool
    details: str = ""


class QAReport(BaseModel):
    """QA validation report"""
    passed: bool
    checks: List[QACheck]
    retries_used: int = 0
    notes: Optional[str] = None


class MapperOutput(BaseModel):
    """Mapper agent output schema"""
    business_page_url: Optional[str] = None
    business_summary: str  # 12-240 chars
    assats: Assets  # Note: keeping typo "assats" from original spec
    qa_report: Optional[QAReport] = None


# JSON Schema for OpenAI structured output
MAPPER_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "business_page_url": {
            "type": ["string", "null"],
            "description": "Official business website URL or null"
        },
        "business_summary": {
            "type": "string",
            "description": "Concise business summary (12-240 characters)",
            "minLength": 12,
            "maxLength": 240
        },
        "assats": {
            "type": "object",
            "properties": {
                "logo_url": {
                    "type": ["string", "null"],
                    "description": "URL to business logo image (SVG/PNG preferred)"
                },
                "business_images_urls": {
                    "type": ["array", "null"],
                    "items": {"type": "string"},
                    "description": "List of business image URLs (max 12, unique)",
                    "maxItems": 12
                },
                "stock_images_urls": {
                    "type": ["array", "null"],
                    "items": {"type": "string"},
                    "description": "List of stock image URLs from whitelisted sources (Unsplash, Pexels, Pixabay), max 12",
                    "maxItems": 12
                },
                "brand_colors": {
                    "type": "object",
                    "properties": {
                        "primary": {
                            "type": "string",
                            "pattern": "^#([A-Fa-f0-9]{6})$",
                            "description": "Primary brand color in hex format #RRGGBB"
                        },
                        "secondary": {
                            "type": "string",
                            "pattern": "^#([A-Fa-f0-9]{6})$",
                            "description": "Secondary brand color in hex format #RRGGBB"
                        }
                    },
                    "required": ["primary", "secondary"]
                }
            },
            "required": ["brand_colors"]
        },
        "qa_report": {
            "type": ["object", "null"],
            "properties": {
                "passed": {"type": "boolean"},
                "checks": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "passed": {"type": "boolean"},
                            "details": {"type": "string"}
                        },
                        "required": ["name", "passed"]
                    }
                },
                "retries_used": {"type": "integer"},
                "notes": {"type": ["string", "null"]}
            }
        }
    },
    "required": ["business_summary", "assats"]
}

