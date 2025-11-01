"""
Telemetry and structured logging utilities for improved debugging and monitoring.

This module provides:
1. Correlation ID tracking across services
2. Performance timing metrics
3. Token usage tracking
4. Structured logging helpers
5. Error context enrichment
"""

import time
import uuid
import logging
from typing import Dict, Any, Optional, List
from contextlib import contextmanager
from dataclasses import dataclass, field, asdict
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class RequestContext:
    """
    Request context that flows through all agents/services.
    Provides correlation for debugging and monitoring.
    """
    correlation_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    session_id: Optional[str] = None
    phase: str = "unknown"
    agent: str = "unknown"
    attempt: int = 1
    parent_span_id: Optional[str] = None
    span_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def child(self, agent: str, phase: Optional[str] = None) -> 'RequestContext':
        """Create child context for sub-operations"""
        return RequestContext(
            correlation_id=self.correlation_id,
            session_id=self.session_id,
            phase=phase or self.phase,
            agent=agent,
            attempt=1,
            parent_span_id=self.span_id,
            span_id=str(uuid.uuid4())[:8],
            metadata=self.metadata.copy()
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict for logging"""
        return {
            k: v for k, v in asdict(self).items()
            if v is not None and k != 'metadata'
        }
    
    def log_prefix(self) -> str:
        """Generate consistent log prefix"""
        parts = [
            f"[{self.agent}]",
            f"session={self.session_id[:8] if self.session_id else 'none'}",
            f"corr={self.correlation_id[:8]}",
            f"span={self.span_id}",
        ]
        if self.attempt > 1:
            parts.append(f"attempt={self.attempt}")
        return " ".join(parts)


@dataclass
class TokenUsage:
    """Track token usage per operation"""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    estimated_cost_usd: float = 0.0
    
    def add(self, prompt: int, completion: int, model: str = "gpt-4.1"):
        """Add token usage and calculate cost"""
        self.prompt_tokens += prompt
        self.completion_tokens += completion
        self.total_tokens += (prompt + completion)
        
        # GPT-4o pricing (as of 2024)
        prompt_cost_per_m = 2.50  # $2.50 per 1M input tokens
        completion_cost_per_m = 10.00  # $10.00 per 1M output tokens
        
        self.estimated_cost_usd += (
            (prompt / 1_000_000) * prompt_cost_per_m +
            (completion / 1_000_000) * completion_cost_per_m
        )
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class PerformanceMetrics:
    """Track performance timing for operations"""
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    duration_ms: Optional[float] = None
    
    def complete(self):
        """Mark operation as complete"""
        self.end_time = time.time()
        self.duration_ms = (self.end_time - self.start_time) * 1000
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "duration_ms": round(self.duration_ms, 2) if self.duration_ms else None,
            "start_time": datetime.fromtimestamp(self.start_time).isoformat(),
            "end_time": datetime.fromtimestamp(self.end_time).isoformat() if self.end_time else None
        }


class PhaseTracker:
    """
    Track metrics for a complete build phase (Mapper, Generator, etc.)
    Accumulates token usage, timing, and errors.
    """
    
    def __init__(self, context: RequestContext):
        self.context = context
        self.metrics = PerformanceMetrics()
        self.token_usage = TokenUsage()
        self.errors: List[Dict[str, Any]] = []
        self.cache_hits = 0
        self.cache_misses = 0
        self.attempts = 0
        self.success = False
        
    def record_attempt(self, 
                      prompt_tokens: int, 
                      completion_tokens: int,
                      used_cache: bool,
                      error: Optional[str] = None):
        """Record an attempt with token usage"""
        self.attempts += 1
        self.token_usage.add(prompt_tokens, completion_tokens)
        
        if used_cache:
            self.cache_hits += 1
        else:
            self.cache_misses += 1
            
        if error:
            self.errors.append({
                "attempt": self.attempts,
                "error": error,
                "timestamp": datetime.utcnow().isoformat()
            })
    
    def complete(self, success: bool = True):
        """Mark phase as complete"""
        self.success = success
        self.metrics.complete()
        self._log_summary()
    
    def _log_summary(self):
        """Log comprehensive phase summary"""
        log_data = {
            **self.context.to_dict(),
            "success": self.success,
            "attempts": self.attempts,
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "tokens": self.token_usage.to_dict(),
            "timing": self.metrics.to_dict(),
            "error_count": len(self.errors)
        }
        
        logger.info(
            f"{self.context.log_prefix()} PHASE_COMPLETE | "
            f"success={self.success} | "
            f"attempts={self.attempts} | "
            f"tokens={self.token_usage.total_tokens} | "
            f"cost=${self.token_usage.estimated_cost_usd:.4f} | "
            f"duration={self.metrics.duration_ms:.0f}ms | "
            f"cache_hit_rate={self.cache_hits}/{self.attempts if self.attempts > 0 else 1} | "
            f"details={log_data}"
        )


@contextmanager
def track_phase(context: RequestContext):
    """
    Context manager for tracking a complete phase.
    
    Usage:
        with track_phase(context) as tracker:
            result = await agent.run(...)
            tracker.record_attempt(prompt_tokens, completion_tokens, used_cache=True)
            tracker.complete(success=True)
    """
    tracker = PhaseTracker(context)
    try:
        yield tracker
    except Exception as e:
        tracker.errors.append({
            "error": str(e),
            "type": type(e).__name__,
            "timestamp": datetime.utcnow().isoformat()
        })
        tracker.complete(success=False)
        raise
    finally:
        if not tracker.metrics.end_time:
            tracker.complete(success=False)


def enrich_error_context(
    error: Exception,
    context: RequestContext,
    additional_context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Enrich error with full context for debugging.
    
    Returns a structured error dict with all relevant context.
    """
    error_data = {
        "error_type": type(error).__name__,
        "error_message": str(error),
        "timestamp": datetime.utcnow().isoformat(),
        **context.to_dict()
    }
    
    if additional_context:
        error_data["additional_context"] = additional_context
    
    # Log structured error
    logger.error(
        f"{context.log_prefix()} ERROR | "
        f"type={error_data['error_type']} | "
        f"message={error_data['error_message'][:200]} | "
        f"context={error_data}",
        exc_info=True
    )
    
    return error_data


def log_token_savings(
    context: RequestContext,
    actual_tokens: int,
    estimated_without_cache: int,
    previous_response_id: str
):
    """Log token savings from using stateful context"""
    savings = estimated_without_cache - actual_tokens
    savings_pct = (savings / estimated_without_cache * 100) if estimated_without_cache > 0 else 0
    
    logger.info(
        f"{context.log_prefix()} TOKEN_SAVINGS | "
        f"actual={actual_tokens} | "
        f"estimated_without_cache={estimated_without_cache} | "
        f"saved={savings} ({savings_pct:.1f}%) | "
        f"response_id={previous_response_id[:20]}..."
    )


def log_cache_usage(
    context: RequestContext,
    cache_key: str,
    hit: bool,
    response_id: Optional[str] = None
):
    """Log cache hit/miss for response_id lookups"""
    logger.debug(
        f"{context.log_prefix()} CACHE_{'HIT' if hit else 'MISS'} | "
        f"cache_key={cache_key} | "
        f"response_id={response_id[:20] if response_id else 'none'}..."
    )

