"""Error models - Product.md > Section 8"""

from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field
import uuid


class ErrorCode(str, Enum):
    """Error codes - Ref: Product.md lines 818"""
    INVALID_PLACE_ID = "INVALID_PLACE_ID"
    GOOGLE_RATE_LIMIT = "GOOGLE_RATE_LIMIT"
    GENERATION_FAILED = "GENERATION_FAILED"
    BUNDLE_INVALID = "BUNDLE_INVALID"
    NOT_FOUND = "NOT_FOUND"
    CACHE_ERROR = "CACHE_ERROR"
    ORCHESTRATION_ERROR = "ORCHESTRATION_ERROR"
    CONFIGURATION_ERROR = "CONFIGURATION_ERROR"


class ApplicationError(Exception):
    """Application error - Ref: Product.md lines 815-824"""
    def __init__(self, code: ErrorCode, message: str, retryable: bool = False, hint: Optional[str] = None, session_id: Optional[str] = None):
        self.error_id = str(uuid.uuid4())
        self.code = code
        self.message = message
        self.retryable = retryable
        self.hint = hint
        self.session_id = session_id
        super().__init__(self.message)
    
    def model_dump(self):
        """Return dict representation for API responses"""
        return {
            "error_id": self.error_id,
            "code": self.code.value,
            "message": self.message,
            "hint": self.hint,
            "retryable": self.retryable,
            "session_id": self.session_id
        }
    
    @property
    def http_status(self) -> int:
        """Map error code to HTTP status - Ref: Product.md lines 827-832"""
        mapping = {
            ErrorCode.INVALID_PLACE_ID: 400,
            ErrorCode.NOT_FOUND: 404,
            ErrorCode.GOOGLE_RATE_LIMIT: 429,
            ErrorCode.GENERATION_FAILED: 500,
            ErrorCode.BUNDLE_INVALID: 500,
            ErrorCode.CACHE_ERROR: 500,
            ErrorCode.ORCHESTRATION_ERROR: 500,
            ErrorCode.CONFIGURATION_ERROR: 500,
        }
        return mapping.get(self.code, 500)

