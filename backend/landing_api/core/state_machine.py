"""Build state machine"""

from enum import Enum
from typing import Dict, Any, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class BuildPhase(str, Enum):
    """Build phases
    
    
    IDLE → FETCHING → ORCHESTRATING → GENERATING → QA → READY
                      ↘───────────────ERROR────────────↗
    """
    IDLE = "IDLE"
    FETCHING = "FETCHING"
    ORCHESTRATING = "ORCHESTRATING"
    GENERATING = "GENERATING"
    QA = "QA"
    READY = "READY"
    ERROR = "ERROR"


class BuildState:
    """Manages build state transitions"""
    
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.phase = BuildPhase.IDLE
        self.started_at: Optional[datetime] = None
        self.metadata: Dict[str, Any] = {}
        self.event_log: list = []  # List of all events for the UI
        self.last_updated: Optional[datetime] = None
    
    def log_event(self, phase: BuildPhase, event: str):
        """Log a new event - adds to log and updates state"""
        # Validate input
        if not isinstance(event, str):
            logger.warning(f"log_event received non-string event: {type(event)}, converting to string")
            event = str(event) if event is not None else ""
        
        # If already in terminal state (READY or ERROR), don't allow phase changes
        # Terminal states are final - don't overwrite them
        if self.is_terminal() and phase not in (BuildPhase.ERROR,):
            # Allow ERROR phase even in terminal state (to update error message)
            # But don't allow transitioning away from terminal states
            if phase == BuildPhase.ERROR:
                # Allow updating error message
                pass
            else:
                return
        
        now = datetime.utcnow()
        
        # Deduplicate: Don't add if the exact same event (phase + detail) was logged recently (within 1 second)
        # This prevents duplicate events from rapid repeated calls
        if self.event_log and self.last_updated:
            recent_event = self.event_log[-1]
            # Normalize event text for comparison
            normalized_recent = recent_event.get("detail", "").strip().lower()
            normalized_new = event.strip().lower()
            
            # If same phase and detail, and within 1 second, skip (likely duplicate)
            try:
                time_diff = (now - self.last_updated).total_seconds()
                if (recent_event.get("phase") == phase.value and 
                    normalized_recent == normalized_new and
                    time_diff < 1.0):
                    logger.debug(f"Skipping duplicate event: {event} (phase: {phase.value})")
                    return
            except (TypeError, AttributeError):
                # If time comparison fails, proceed normally (shouldn't happen but be safe)
                pass
        
        # Add event to log
        self.event_log.append({
            "ts": now.isoformat() + "Z",
            "phase": phase.value,
            "detail": event
        })
        
        # Update current phase
        self.phase = phase
        self.last_updated = now
        
        if not self.started_at:
            self.started_at = now
        
        logger.debug(f"Logged event: {event} (phase: {phase.value})")
    
    def get_latest_event(self):
        """Get the most recent event"""
        if not self.event_log:
            return None
        return self.event_log[-1]
    
    def is_terminal(self) -> bool:
        """Check if build is in terminal state"""
        return self.phase in (BuildPhase.READY, BuildPhase.ERROR)

