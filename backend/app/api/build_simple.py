"""Simplified _run_build to test if background tasks work"""

import os
from pathlib import Path

async def _run_build_simple(session_id: str, place_id: str, render_prefs: dict):
    """Simplified version to test if background task executes"""
    
    # Write to log file immediately
    log_file = Path("backend/build.log")
    log_file.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(f"\n{'='*60}\n")
            f.write(f"TASK EXECUTING!\n")
            f.write(f"Session: {session_id}\n")
            f.write(f"Place: {place_id}\n")
            f.write(f"{'='*60}\n")
            f.flush()
        
        # Import here to avoid circular dependency
        from app.api.build import session_store
        from app.core.state_machine import BuildPhase
        
        state = session_store.get(session_id)
        if not state:
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(f"ERROR: Session {session_id} not found\n")
                f.flush()
            return
        
        state.transition_to(BuildPhase.FETCHING, "Testing...")
        state.set_progress(0.5)
        
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(f"Build completed for {session_id}\n")
            f.flush()
            
    except Exception as e:
        import traceback
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(f"ERROR: {str(e)}\n")
            f.write(traceback.format_exc())
            f.flush()

