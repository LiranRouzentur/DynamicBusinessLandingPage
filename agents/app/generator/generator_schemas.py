"""Generator agent response schemas based on landing-page-agent-with-qa.md"""
from pydantic import BaseModel
from typing import Dict, Any, List, Optional


class QACheckResult(BaseModel):
    """QA check result"""
    name: str
    passed: bool
    details: Optional[str] = None


class GeneratorQAReport(BaseModel):
    """Generator QA report"""
    status: str  # "PASS" or "FAIL"
    tier: str  # interactivity tier
    fixed: List[str] = []  # List of fixes applied
    checks: List[QACheckResult] = []


class GeneratorOutput(BaseModel):
    """Single-file HTML output only"""
    html: str  # Complete inlined HTML
    meta: Optional[Dict[str, Any]] = None  # e.g., external_image_urls, notes

GENERATOR_RESPONSE_SCHEMA = {
    "title": "GeneratorResponse",  # CRITICAL: Required for structured outputs
    "type": "object",
    "properties": {
        "html": {
            "type": "string",
            "description": "Complete HTML5 document as a single string with inlined <style> and <script>"
        },
        "meta": {
            "type": "object",
            "properties": {
                "external_image_urls": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of external image URLs used in the HTML"
                },
                "design_rationale": {
                    "type": "string",
                    "description": "Brief explanation of design decisions"
                }
            },
            "required": ["external_image_urls", "design_rationale"],
            "additionalProperties": False
        }
    },
    "required": ["html", "meta"],
    "additionalProperties": False  # CRITICAL: Required for strict mode
}

# Input envelope additions (documented for the generator prompt and orchestrator use)
# Note: The JSON schema contract for the LLM call is defined in the prompt; this
# module records the expected keys for clarity. Both fields are null on first run.
GENERATOR_INPUT_EXTENSIONS_SCHEMA = {
    "tamplate": {
        "type": ["string", "null"],
        "description": "HTML generated in the previous attempt. Null on first run."
    },
    "validator_errors": {
        "type": ["array", "null"],
        "items": {"type": "string"},
        "description": "List of validation errors from MCP that the generator must fix. Null on first run."
    }
}

