# Manual Server Startup Commands

Run each server in its own terminal window to see all logs directly.

## Terminal 1: Agents Server (Port 8001)

```powershell
cd agents
$env:PYTHONDONTWRITEBYTECODE=1
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8001
```

Expected output:

```
INFO:     Will watch for changes in these directories: ['C:\\DynamicBusinessLandingPage\\agents']
INFO:     Uvicorn running on http://127.0.0.1:8001
[Orchestrator] Calling Designer...
[Designer] Calling gpt-4o
```

## Terminal 2: Backend Server (Port 8000)

```powershell
cd backend
$env:PYTHONDONTWRITEBYTECODE=1
.\.venv\Scripts\Activate.ps1
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Expected output:

```
INFO:     Will watch for changes in these directories: ['C:\\DynamicBusinessLandingPage\\backend']
INFO:     Uvicorn running on http://127.0.0.1:8000
[BUILD] Session abc123: Calling google_fetcher...
```

## Terminal 3: Frontend Server (Port 5173)

```powershell
cd client
npm run dev
```

Expected output:

```
VITE v5.4.21  ready
➜  Local:   http://localhost:5173/
```

## Quick Copy-Paste Commands

### Agents (run first)

```powershell
cd C:\DynamicBusinessLandingPage\agents && $env:PYTHONDONTWRITEBYTECODE=1 && .\.venv\Scripts\Activate.ps1 && python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8001
```

### Backend (run second)

```powershell
cd C:\DynamicBusinessLandingPage\backend && $env:PYTHONDONTWRITEBYTECODE=1 && .\.venv\Scripts\Activate.ps1 && python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

### Frontend (run third)

```powershell
cd C:\DynamicBusinessLandingPage\client && npm run dev
```

## What You'll See

- **Agents Terminal**: All AI agent activity, validation errors, OpenAI API calls
- **Backend Terminal**: Build progress, SSE events, Google Places API calls
- **Frontend Terminal**: Vite compilation, React errors

## To Stop

Press `Ctrl+C` in each terminal to stop that server.
