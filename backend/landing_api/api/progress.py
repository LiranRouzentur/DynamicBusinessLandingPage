"""GET /sse/progress/{sessionId} endpoint"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from landing_api.models.schemas import ProgressEvent
from landing_api.core.state_machine import BuildPhase
from landing_api.api.build import session_store
from datetime import datetime
import asyncio
import json
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/progress/{session_id}")
async def stream_progress(session_id: str):
    """
    Stream build progress as Server-Sent Events.
    
    Event format:
    {
      "ts": "2025-10-27T10:00:00Z",
      "session_id": "abc123",
      "phase": "FETCHING|ORCHESTRATING|GENERATING|QA|READY|ERROR",
      "step": "Google.PlaceDetails",
      "detail": "Fetched 6 photos, 123 reviews",
      "progress": 0.42
    }
    """
    logger.info(f"SSE ENDPOINT: /sse/progress/{session_id} - Request received")
    
    state = session_store.get(session_id)
    logger.debug(f"SSE ENDPOINT: Session lookup result: {state is not None}")
    
    if not state:
        logger.warning(f"SSE ENDPOINT: Session NOT FOUND: {session_id}")
        logger.debug(f"SSE ENDPOINT: Available sessions: {list(session_store.keys())}")
        raise HTTPException(status_code=404, detail="Session not found")
    
    logger.info(f"SSE ENDPOINT: Session found, starting stream for phase: {state.phase}")
    
    async def generate():
        last_state_snapshot = None
        max_iterations = 600  # Timeout after 10 minutes (600 * 1s)
        iteration = 0
        
        # Send all existing events immediately
        logger.debug(f"SSE: Sending {len(state.event_log)} existing events for session {session_id}")
        last_event_count = len(state.event_log)
        
        for event in state.event_log:
            e = ProgressEvent(
                ts=event["ts"],
                session_id=session_id,
                phase=event["phase"],
                step="",
                detail=event["detail"],
                progress=0.0
            )
            yield f"data: {e.model_dump_json()}\n\n"
        
        while iteration < max_iterations:
            iteration += 1
            
            # Check if in terminal state
            if state.is_terminal():
                logger.info(f"SSE: Stream closing for session {session_id} - terminal state: {state.phase.value}")
                # Send final state event before closing
                final_event = ProgressEvent(
                    ts=datetime.utcnow().isoformat() + "Z",
                    session_id=session_id,
                    phase=state.phase.value,
                    step="",
                    detail=f"Build {'completed' if state.phase.value == 'READY' else 'failed'}",
                    progress=1.0 if state.phase.value == 'READY' else 0.0
                )
                yield f"data: {final_event.model_dump_json()}\n\n"
                break
            
            # Check if new events were added
            current_event_count = len(state.event_log)
            if current_event_count > last_event_count:
                # Send only new events
                new_events = state.event_log[last_event_count:]
                logger.debug(f"SSE: Sending {len(new_events)} new events for session {session_id}")
                
                for event in new_events:
                    e = ProgressEvent(
                        ts=event["ts"],
                        session_id=session_id,
                        phase=event["phase"],
                        step="",
                        detail=event["detail"],
                        progress=0.0
                    )
                    yield f"data: {e.model_dump_json()}\n\n"
                
                last_event_count = current_event_count
            
            await asyncio.sleep(1.0)  # Poll every 1 second
        
        if iteration >= max_iterations:
            logger.warning(f"SSE: Timeout after 10min for session {session_id}")
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )

