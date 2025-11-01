"""Build state machine"""

from enum import Enum
from typing import Dict, Any, Optional, Set
from datetime import datetime
import logging
import uuid

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
    
    # Initializes build state machine for session; tracks phase, events, metadata, and sent event IDs.
    # Prevents duplicate events via content tracking; terminal states (READY/ERROR) are immutable.
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.phase = BuildPhase.IDLE
        self.started_at: Optional[datetime] = None
        self.metadata: Dict[str, Any] = {}
        self.event_log: list = []  # List of all events for the UI
        self.last_updated: Optional[datetime] = None
        self.sent_event_ids: Set[str] = set()  # Track sent events to prevent duplicates
        self.logged_event_content: Set[str] = set()  # Track event content to prevent duplicates
    
    # Logs event with timestamp and unique ID; updates phase and deduplicates content.
    # Terminal states (READY/ERROR) prevent phase changes except for error updates.
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
        
        # Check for duplicate content (phase + detail combination)
        # This prevents duplicate events from being logged
        event_content = f"{phase.value}:{event.strip()}"
        if event_content in self.logged_event_content:
            logger.debug(f"Skipping duplicate event: {event[:50]}")
            return
        
        # Add to logged content set
        self.logged_event_content.add(event_content)
        
        # Generate unique event ID using UUID (no collisions)
        event_id = str(uuid.uuid4())
        
        # Add event to log with unique ID and timestamp
        self.event_log.append({
            "id": event_id,
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
    
    # Returns events not yet sent to client (tracked via sent_event_ids set).
    # Used by SSE endpoint to stream only new events without duplicates.
    def get_unsent_events(self) -> list:
        """Get events that haven't been sent to the client yet"""
        unsent = []
        for event in self.event_log:
            event_id = event.get("id")
            if event_id and event_id not in self.sent_event_ids:
                unsent.append(event)
        return unsent
    
    def mark_events_sent(self, event_ids: list[str]):
        """Mark events as sent to prevent re-sending"""
        self.sent_event_ids.update(event_ids)
    
    def is_terminal(self) -> bool:
        """Check if build is in terminal state"""
        # SPDX-License-Identifier: Proprietary
        # Copyright © 2025 Liran Rouzentur. All rights reserved.
        # כל הזכויות שמורות © 2025 לירן רויזנטור.
        # קוד זה הינו קנייני וסודי. אין להעתיק, לערוך, להפיץ או לעשות בו שימוש ללא אישור מפורש.
        # © 2025 Лиран Ройзентур. Все права защищены.
        # Этот программный код является собственностью владельца.
        # Запрещается копирование, изменение, распространение или использование без явного разрешения.
        return self.phase in (BuildPhase.READY, BuildPhase.ERROR)

