# Agents Service Integration Summary

## Overview

A new AI agents service has been created using the OpenAI Agents SDK pattern, separate from the main backend. This provides a clean, modular architecture for AI agent orchestration.

## Architecture

### Components

1. **Agents Service** (`ai/`) - Runs on port 8001

   - Clean OpenAI Agents SDK implementation
   - FastAPI-based REST API
   - Modular agent architecture (Designer, Mapper, Generator, QA)

2. **Backend Service** (`backend/`) - Runs on port 8000

   - Updated to call agents service when available
   - Falls back to old orchestrator if agents service is unavailable
   - Receives events from agents service via `/api/events` endpoint

3. **Frontend** (`client/`) - Runs on port 5173
   - No changes required
   - Continues to receive SSE events from backend

## Integration Flow

```
Frontend (5173) ←→ Backend (8000) ←→ Agents Service (8001)
                      ↓                        ↓
                 SSE Events              Event Updates
```

### Build Flow

1. Frontend sends build request to Backend
2. Backend checks if Agents Service is available
3. If available:
   - Backend extracts place data and prepares request
   - Calls Agents Service `/build` endpoint
   - Agents Service runs orchestrator workflow
   - Agents Service sends progress events to Backend `/api/events`
   - Backend forwards SSE events to Frontend
   - Result returned to Backend, artifacts saved
4. If not available:
   - Backend falls back to old orchestrator
   - Progress handled by existing logic

## Key Files

### New Files in Agents Service

- `ai/app/main.py` - FastAPI entry point
- `ai/app/agent_core.py` - All agent logic (Designer, Mapper, Generator, QA, Orchestrator)
- `ai/app/types.py` - Pydantic schemas
- `ai/app/event_bridge.py` - Communication bridge to backend

### Updated Files in Backend

- `backend/app/api/build.py` - Updated to use agents service when available
- `backend/app/core/agents_client.py` - HTTP client for agents service
- `backend/app/api/events.py` - New endpoint to receive agent events
- `backend/app/main.py` - Registered events router

### Updated Scripts

- `scripts/start-dev.ps1` - Starts agents, backend, and frontend services

## Event Communication

The agents service sends user-friendly progress messages to the backend:

```python
# Agent sends event
await event_bridge.emit_event(session_id, "GENERATING", "Designing layout...")

# Backend receives and logs to SSE
state.log_event(BuildPhase.GENERATING, "Designing layout...")

# Frontend receives via SSE
{
  "phase": "GENERATING",
  "detail": "Designing layout...",
  "ts": "2024-01-01T12:00:00Z"
}
```

## Starting the Services

### Automated (Recommended)

```powershell
cd scripts
.\start-dev.ps1
```

This will:

1. Create agents virtual environment if needed
2. Install dependencies
3. Start agents service (8001)
4. Start backend service (8000)
5. Start frontend dev server (5173)

### Manual

```powershell
# Terminal 1 - Agents Service
cd agents
python -m venv .venv
.venv\Scripts\activate
pip install -e .
uvicorn app.main:app --reload --host 127.0.0.1 --port 8001

# Terminal 2 - Backend
cd backend
.venv\Scripts\activate
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

# Terminal 3 - Frontend
cd client
npm run dev
```

## Benefits

1. **Separation of Concerns** - AI logic separated from business logic
2. **Scalability** - Agents service can be scaled independently
3. **Maintainability** - Clean, modular code structure
4. **Flexibility** - Easy to swap agent implementations
5. **Graceful Degradation** - Falls back to old orchestrator if agents service unavailable

## Testing

```bash
# Test agents service health
curl http://localhost:8001/health

# Test backend with agents service
curl http://localhost:8000/

# Run agents tests
cd agents
pytest
```

## Environment Variables

### Agents Service (`.env` in `ai/`)

```env
OPENAI_API_KEY=sk-xxxx
BACKEND_URL=http://localhost:8000
AGENTS_TRACING=0
```

### Backend (`.env` in `backend/`)

```env
OPENAI_API_KEY=sk-xxxx
GOOGLE_MAPS_API_KEY=xxxx
```

## Migration Path

The old agent files in `backend/app/ai/` are **not deleted**. This allows:

- Gradual migration
- Rollback if needed
- A/B testing of implementations
- Reference for comparison

To fully migrate:

1. Test new agents service thoroughly
2. Remove old orchestrator code from `backend/app/api/build.py`
3. Delete `backend/app/ai/` directory

## Notes

- The agents service communicates events to the backend asynchronously
- User-friendly messages are used instead of technical jargon
- All agent responses are validated with Pydantic schemas
- The system handles failures gracefully with fallbacks
