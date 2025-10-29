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
    """Generator agent output"""
    index_html: str  # Complete HTML5 document with QA REPORT comment
    styles_css: str  # All CSS styles
    script_js: str  # JavaScript for interactivity
    assets: Optional[Dict[str, Any]] = None  # Assets structure
    qa_report: Optional[GeneratorQAReport] = None


# JSON Schema for OpenAI structured output
GENERATOR_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "index_html": {
            "type": "string",
            "description": "Complete HTML5 document with QA REPORT comment at top"
        },
        "styles_css": {
            "type": "string",
            "description": "All CSS styles for the landing page"
        },
        "script_js": {
            "type": "string",
            "description": "JavaScript for interactivity (within tier limits, <10KB gzipped)"
        },
        "assets": {
            "type": ["object", "null"],
            "description": "Assets structure (images, etc.)"
        },
        "qa_report": {
            "type": ["object", "null"],
            "properties": {
                "status": {
                    "type": "string",
                    "enum": ["PASS", "FAIL"],
                    "description": "QA validation status"
                },
                "tier": {
                    "type": "string",
                    "enum": ["basic", "enhanced", "highend"],
                    "description": "Interactivity tier used"
                },
                "fixed": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of fixes applied during QA loop"
                },
                "checks": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "passed": {"type": "boolean"},
                            "details": {"type": ["string", "null"]}
                        },
                        "required": ["name", "passed"]
                    }
                }
            },
            "required": ["status", "tier"]
        }
    },
    "required": ["index_html", "styles_css", "script_js"]
}

