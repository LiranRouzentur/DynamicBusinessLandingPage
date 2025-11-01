"""Pydantic schemas for corpus data structures"""
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional, Literal
from datetime import datetime
from enum import Enum


class ErrorClass(str, Enum):
    """Validation error classes"""
    SCHEMA_ERROR = "SCHEMA_ERROR"
    BROKEN_LINK = "BROKEN_LINK"
    MISSING_REQUIRED = "MISSING_REQUIRED"
    OUT_OF_RANGE = "OUT_OF_RANGE"
    SAFETY_VIOLATION = "SAFETY_VIOLATION"
    TOOL_FAILURE = "TOOL_FAILURE"


class ValidatorError(BaseModel):
    """Single validator error entry"""
    code: str = Field(..., description="Error code (e.g., URL_UNREACHABLE, FIELD_MISSING)")
    field: Optional[str] = Field(None, description="Field name if applicable")
    message: str = Field(..., description="Error message")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")


class ExpectedFix(BaseModel):
    """Expected fix metadata"""
    type: Literal["JSON_PATCH", "RULE_REF", "PROMPT_PATCH"]
    ref: Optional[str] = Field(None, description="Reference to patch file (e.g., schema_missing_field.yaml)")
    notes: Optional[str] = Field(None, description="Human-readable notes about the fix")


class Incident(BaseModel):
    """Incident file schema"""
    id: str = Field(..., pattern=r"^INC-\d{4}-\d{2}-\d{2}-\d{6}$", description="Incident ID: INC-YYYY-MM-DD-hhmmss")
    timestamp: str = Field(..., description="ISO 8601 timestamp")
    agent: str = Field(..., description="Agent name: mapper|designer|orchestrator|<name>")
    error_class: ErrorClass = Field(..., description="Error class enum")
    input_fingerprint: str = Field(..., pattern=r"^sha256-[a-f0-9]{64}$", description="SHA256 hash of input")
    input_excerpt: str = Field(..., max_length=500, description="Short text excerpt of input")
    candidate_output: Dict[str, Any] = Field(default_factory=dict, description="Candidate output (JSON)")
    validator_errors: List[ValidatorError] = Field(default_factory=list, description="List of validator errors")
    expected_fix: Optional[ExpectedFix] = Field(None, description="Expected fix metadata")
    tags: List[str] = Field(default_factory=list, description="Tags for categorization")

