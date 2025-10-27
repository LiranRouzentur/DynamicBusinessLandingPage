"""Build state machine - Product.md > Section 3, lines 644-649"""

from enum import Enum
from typing import Dict, Any, Optional
from datetime import datetime


class BuildPhase(str, Enum):
    """Build phases - Product.md lines 644-649
    
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
        now = datetime.utcnow()
        
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
        
        print(f"[BuildState] Logged event: {event} (phase: {phase.value})", flush=True)
    
    def get_latest_event(self):
        """Get the most recent event"""
        if not self.event_log:
            return None
        return self.event_log[-1]
    
    def is_terminal(self) -> bool:
        """Check if build is in terminal state"""
        return self.phase in (BuildPhase.READY, BuildPhase.ERROR)

