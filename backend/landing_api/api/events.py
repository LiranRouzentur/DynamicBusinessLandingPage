"""Event endpoint for agents service to send progress updates"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from landing_api.core.state_machine import BuildState, BuildPhase
from landing_api.api.build import session_store


router = APIRouter()


class EventRequest(BaseModel):
    """Event message from agents service"""
    session_id: str
    phase: str
    detail: str


@router.post("/events")
async def receive_event(event: EventRequest):
    """
    Receive event from agents service and forward to session state
    
    This allows the agents service to send progress updates
    that will be streamed to the frontend via SSE.
    """
    # Get the session state
    state = session_store.get(event.session_id)
    
    if not state:
        # Session not found, return success anyway (non-blocking)
        print(f"[Events] Session {event.session_id} not found")
        return {"status": "accepted", "session_found": False}
    
    # Map phase string to BuildPhase enum
    phase_map = {
        "FETCHING": BuildPhase.FETCHING,
        "ORCHESTRATING": BuildPhase.ORCHESTRATING,
        "GENERATING": BuildPhase.GENERATING,
        "QA": BuildPhase.QA,
        "READY": BuildPhase.READY,
        "ERROR": BuildPhase.ERROR
    }
    
    phase = phase_map.get(event.phase, BuildPhase.IDLE)
    
    # Log the event
    print(f"[Events] Received event from agents: phase={event.phase}, detail='{event.detail}', session={event.session_id}", flush=True)
    state.log_event(phase, event.detail)
    
    return {"status": "accepted", "session_found": True}


@router.get("/health")
async def health():
    """Health check for agents service"""
    return {"status": "healthy"}

