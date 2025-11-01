"""
Generator Agent Configuration
Defines retry strategy, model selection, and validation parameters
"""

from typing import Dict, List, Optional
from enum import Enum


class ErrorSeverity(Enum):
    """Error severity levels for validation"""
    CRITICAL = "critical"  # Must fix (security, broken functionality, CORS)
    MAJOR = "major"        # Should fix (accessibility, layout issues)
    MINOR = "minor"        # Nice to fix (cosmetic, minor inconsistencies)


class ModelTier(Enum):
    """Model selection tiers for different attempt stages"""
    PREMIUM = "gpt-4.1"  # GPT-4.1 - Premium OpenAI model


# Retry Strategy Configuration
MAX_GENERATOR_ATTEMPTS = 7  # Increased to allow more validation cycles
RETRY_STRATEGY = {
    "attempt_1": {
        "model": ModelTier.PREMIUM.value,
        "temperature": 1.05,
        "top_p": 0.95,
        "max_output_tokens": 12000,  # Increased for large HTML responses (40-60KB)
        "description": "Initial generation with GPT-4.1 for best quality"
    },
    "attempt_2": {
        "model": ModelTier.PREMIUM.value,
        "temperature": 0.95,  # Slightly lower for focused fixes
        "top_p": 0.92,
        "max_output_tokens": 12000,
        "description": "First retry with GPT-4.1, focused on critical errors"
    },
    "attempt_3": {
        "model": ModelTier.PREMIUM.value,
        "temperature": 0.85,
        "top_p": 0.9,
        "max_output_tokens": 12000,
        "description": "Second retry with GPT-4.1, stricter validation focus"
    },
    "attempt_4": {
        "model": ModelTier.PREMIUM.value,
        "temperature": 0.8,
        "top_p": 0.88,
        "max_output_tokens": 12000,
        "description": "Third retry with GPT-4.1, precision fixes"
    },
    "attempt_5": {
        "model": ModelTier.PREMIUM.value,
        "temperature": 0.75,
        "top_p": 0.85,
        "max_output_tokens": 12000,
        "description": "Fourth retry with GPT-4.1, error-only mode"
    },
    "attempt_6": {
        "model": ModelTier.PREMIUM.value,
        "temperature": 0.7,
        "top_p": 0.82,
        "max_output_tokens": 12000,
        "description": "Fifth retry with GPT-4.1, strict error elimination"
    },
    "attempt_7": {
        "model": ModelTier.PREMIUM.value,
        "temperature": 0.65,
        "top_p": 0.8,
        "max_output_tokens": 12000,
        "description": "Final retry with GPT-4.1, minimal changes only"
    }
}


# Error Severity Classification Patterns
ERROR_SEVERITY_PATTERNS = {
    ErrorSeverity.CRITICAL: [
        "CORS",
        "security",
        "TARGET_BLANK_NO_NOOPENER",
        "failed to load",
        "syntax error",
        "undefined",
        "console error",
        "network error",
        "CSP violation"
    ],
    ErrorSeverity.MAJOR: [
        "accessibility",
        "image.*oversized",
        "image.*too small",
        "aspect ratio",
        "layout overflow",
        "missing alt",
        "contrast",
        "text overlay"
    ],
    ErrorSeverity.MINOR: [
        "cosmetic",
        "minor spacing",
        "suggestion",
        "consider"
    ]
}


def classify_error_severity(error_msg: str) -> ErrorSeverity:
    """
    Classify an error message by severity based on pattern matching
    
    Args:
        error_msg: Error message string
        
    Returns:
        ErrorSeverity enum value
    """
    error_lower = error_msg.lower()
    
    # Check critical patterns first
    for pattern in ERROR_SEVERITY_PATTERNS[ErrorSeverity.CRITICAL]:
        if pattern.lower() in error_lower:
            return ErrorSeverity.CRITICAL
    
    # Then major
    for pattern in ERROR_SEVERITY_PATTERNS[ErrorSeverity.MAJOR]:
        if pattern.lower() in error_lower:
            return ErrorSeverity.MAJOR
    
    # Default to minor
    return ErrorSeverity.MINOR


def get_retry_config(attempt_number: int) -> Dict:
    """
    Get retry configuration for a specific attempt
    
    Args:
        attempt_number: 1, 2, or 3
        
    Returns:
        Configuration dict with model, temperature, etc.
    """
    key = f"attempt_{min(attempt_number, MAX_GENERATOR_ATTEMPTS)}"
    return RETRY_STRATEGY.get(key, RETRY_STRATEGY["attempt_1"])


def format_errors_by_severity(errors: List[str]) -> Dict[str, List[str]]:
    """
    Group errors by severity level
    
    Args:
        errors: List of error messages
        
    Returns:
        Dict mapping severity -> list of errors
    """
    categorized = {
        "critical": [],
        "major": [],
        "minor": []
    }
    
    for error in errors:
        severity = classify_error_severity(error)
        categorized[severity.value].append(error)
    
    return categorized


def should_continue_retrying(attempt_number: int, errors_by_severity: Dict[str, List[str]]) -> bool:
    """
    Decide if we should continue retrying based on attempt and error severity
    Goal: Pass validation as quickly as possible, but allow up to 7 attempts for stubborn errors
    
    Args:
        attempt_number: Current attempt (1-7)
        errors_by_severity: Errors grouped by severity
        
    Returns:
        True if should retry, False otherwise
    """
    # If no errors at all, don't retry
    if not any(errors_by_severity.values()):
        return False
    
    # Attempts 1-5: Always retry if there are critical or major errors
    if attempt_number < 6 and (errors_by_severity["critical"] or errors_by_severity["major"]):
        return True
    
    # Attempt 6: Only retry if there are critical errors (allow major errors to pass)
    if attempt_number == 6 and errors_by_severity["critical"]:
        return True
    
    # Attempt 7: This is the last attempt, no more retries after this
    if attempt_number >= 7:
        return False
    
    # If only minor errors remain, accept the result
    if not errors_by_severity["critical"] and not errors_by_severity["major"]:
        return False
    
    # Default: retry if we haven't hit max attempts
    return attempt_number < MAX_GENERATOR_ATTEMPTS

