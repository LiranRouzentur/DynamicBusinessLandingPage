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
        max_iterations = 1200  # Timeout after 20 minutes (1200 * 1s) - increased for long builds
        iteration = 0
        
        # Send all existing events immediately
        # Deduplicate events by ts+phase+detail to prevent duplicates (include timestamp for uniqueness)
        logger.debug(f"SSE: Sending {len(state.event_log)} existing events for session {session_id}")
        
        # Create a copy of event_log to avoid race conditions during iteration
        # Access state from session_store each time to get fresh reference
        state_snapshot = session_store.get(session_id)
        if not state_snapshot:
            logger.warning(f"SSE: Session {session_id} removed during stream initialization")
            return
        
        event_log_snapshot = state_snapshot.event_log.copy()  # Shallow copy for safety
        last_event_count = len(event_log_snapshot)
        
        # Track sent events to prevent duplicates - use ts+phase+detail for uniqueness
        sent_event_keys = set()
        
        for event in event_log_snapshot:
            # Create unique key for deduplication including timestamp
            event_ts = event.get("ts", "")
            event_key = f"{event_ts}-{event['phase']}-{event.get('detail', '').strip().lower()}"
            
            # Skip if we've already sent this exact event
            if event_key in sent_event_keys:
                logger.debug(f"SSE: Skipping duplicate event: {event.get('detail', '')[:50]}...")
                continue
                
            sent_event_keys.add(event_key)
            
            e = ProgressEvent(
                ts=event["ts"],
                session_id=session_id,
                phase=event["phase"],
                step="",
                detail=event.get("detail", ""),
                progress=0.0
            )
            yield f"data: {e.model_dump_json()}\n\n"
        
        while iteration < max_iterations:
            iteration += 1
            
            # Re-check state from session_store to handle removal
            current_state = session_store.get(session_id)
            if not current_state:
                logger.warning(f"SSE: Session {session_id} removed during streaming")
                break
            
            # Check if in terminal state
            if current_state.is_terminal():
                logger.info(f"SSE: Stream closing for session {session_id} - terminal state: {current_state.phase.value}")
                # Send final state event before closing
                final_event = ProgressEvent(
                    ts=datetime.utcnow().isoformat() + "Z",
                    session_id=session_id,
                    phase=current_state.phase.value,
                    step="",
                    detail=f"Build {'completed' if current_state.phase.value == 'READY' else 'failed'}",
                    progress=1.0 if current_state.phase.value == 'READY' else 0.0
                )
                yield f"data: {final_event.model_dump_json()}\n\n"
                break
            
            # Check if new events were added (create snapshot to avoid race conditions)
            current_event_log = current_state.event_log.copy()  # Snapshot
            current_event_count = len(current_event_log)
            if current_event_count > last_event_count:
                # Send only new events
                new_events = current_event_log[last_event_count:]
                logger.debug(f"SSE: Sending {len(new_events)} new events for session {session_id}")
                
                for event in new_events:
                    # Deduplicate: Check if we've already sent this event (include ts for uniqueness)
                    event_ts = event.get("ts", "")
                    event_key = f"{event_ts}-{event['phase']}-{event.get('detail', '').strip().lower()}"
                    if event_key in sent_event_keys:
                        logger.debug(f"SSE: Skipping duplicate new event: {event.get('detail', '')[:50]}...")
                        continue
                    
                    sent_event_keys.add(event_key)
                    
                    e = ProgressEvent(
                        ts=event["ts"],
                        session_id=session_id,
                        phase=event["phase"],
                        step="",
                        detail=event.get("detail", ""),
                        progress=0.0
                    )
                    yield f"data: {e.model_dump_json()}\n\n"
                
                last_event_count = current_event_count
            
            await asyncio.sleep(1.0)  # Poll every 1 second
        
        if iteration >= max_iterations:
            logger.warning(f"SSE: Timeout after 20min for session {session_id}")
            # Send timeout event before closing
            timeout_event = ProgressEvent(
                ts=datetime.utcnow().isoformat() + "Z",
                session_id=session_id,
                phase="ERROR",
                step="",
                detail="Build timeout - stream closed after 20 minutes",
                progress=0.0
            )
            yield f"data: {timeout_event.model_dump_json()}\n\n"
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )

