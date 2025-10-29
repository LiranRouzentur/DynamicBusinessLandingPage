"""Validator agent response schemas based on validator_agent.md"""
from pydantic import BaseModel
from typing import List, Dict, Any, Optional


class Violation(BaseModel):
    """Validation violation"""
    id: str  # e.g., "STRUCTURE.MISSING_INDEX"
    severity: str  # "error" or "warn"
    where: str  # Location of violation
    hint: str  # Actionable fix hint
    owner: str  # "generator", "mapper", or "orchestrator"


class QASection(BaseModel):
    """QA section result"""
    name: str
    passed: bool
    details: List[str] = []


class QAMetrics(BaseModel):
    """QA metrics"""
    js_gzip_kb: Optional[float] = None
    css_size_kb: Optional[float] = None
    image_count: Optional[int] = None
    total_image_weight_mb: Optional[float] = None
    dom_node_count: Optional[int] = None


class QAReport(BaseModel):
    """QA report"""
    attempts_used: int = 0
    metrics: QAMetrics
    sections: List[QASection]


class RepairSuggestions(BaseModel):
    """Repair suggestions by agent"""
    needs_structural_fix: bool = False
    needs_brand_fix: bool = False
    needs_security_fix: bool = False
    messages_for_generator: List[str] = []
    messages_for_mapper: List[str] = []
    messages_for_orchestrator: List[str] = []


class ValidatorOutput(BaseModel):
    """Validator agent output"""
    status: str  # "PASS" or "FAIL"
    violations: List[Violation] = []
    qa_report: QAReport
    repair_suggestions: RepairSuggestions


# JSON Schema for OpenAI structured output
VALIDATOR_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "status": {
            "type": "string",
            "enum": ["PASS", "FAIL"],
            "description": "Validation status - FAIL if any error-level violations exist"
        },
        "violations": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "severity": {
                        "type": "string",
                        "enum": ["error", "warn"]
                    },
                    "where": {"type": "string"},
                    "hint": {"type": "string"},
                    "owner": {
                        "type": "string",
                        "enum": ["generator", "mapper", "orchestrator"]
                    }
                },
                "required": ["id", "severity", "where", "hint", "owner"]
            }
        },
        "qa_report": {
            "type": "object",
            "properties": {
                "attempts_used": {"type": "integer"},
                "metrics": {
                    "type": "object",
                    "properties": {
                        "js_gzip_kb": {"type": ["number", "null"]},
                        "css_size_kb": {"type": ["number", "null"]},
                        "image_count": {"type": ["integer", "null"]},
                        "total_image_weight_mb": {"type": ["number", "null"]},
                        "dom_node_count": {"type": ["integer", "null"]}
                    }
                },
                "sections": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "passed": {"type": "boolean"},
                            "details": {
                                "type": "array",
                                "items": {"type": "string"}
                            }
                        },
                        "required": ["name", "passed"]
                    }
                }
            },
            "required": ["metrics", "sections"]
        },
        "repair_suggestions": {
            "type": "object",
            "properties": {
                "needs_structural_fix": {"type": "boolean"},
                "needs_brand_fix": {"type": "boolean"},
                "needs_security_fix": {"type": "boolean"},
                "messages_for_generator": {
                    "type": "array",
                    "items": {"type": "string"}
                },
                "messages_for_mapper": {
                    "type": "array",
                    "items": {"type": "string"}
                },
                "messages_for_orchestrator": {
                    "type": "array",
                    "items": {"type": "string"}
                }
            },
            "required": ["needs_structural_fix", "needs_brand_fix", "needs_security_fix"]
        }
    },
    "required": ["status", "violations", "qa_report", "repair_suggestions"]
}
