# Why You Don't See Logs in Terminal - Troubleshooting Guide

## Common Root Causes

### 1. Watching the Wrong Process (Reload/Worker Mismatch)

**Why it happens:**

- `uvicorn --reload` spawns a supervisor + child process
- `gunicorn` spawns N workers
- Your prints land in the child/worker, but you're viewing the supervisor or another replica

**Symptoms:**

- Prints work initially but stop after reload
- CPU spikes in a different PID than the logs you're viewing
- Multiple similar processes running

**Diagnostic:**

```powershell
# PowerShell (Windows)
Get-Process python | Format-Table Id, ProcessName, StartTime -Auto

# Find which process is serving your endpoint
netstat -ano | findstr :8000
```

**Solution:**

For development with a single process:

```bash
uvicorn landing_api.main:app --reload --log-level debug
```

For production with explicit logging:

```bash
gunicorn -k uvicorn.workers.UvicornWorker landing_api.main:app --workers 1 --capture-output --log-level debug
```

---

### 2. Stdout Gets Replaced or Muted (Logging Handler Override)

**Why it happens:**

- Some library calls `logging.basicConfig()` without `force=True`
- Later code swaps `sys.stdout` to StringIO or a null stream
- Your early prints show; later ones vanish

**Diagnostic:**

Add this at the very top of your background task:

```python
import sys, logging

print("BEFORE: stdout id:", id(sys.stdout), flush=True)
print("BEFORE: stdout isatty:", sys.stdout.isatty(), flush=True)
print("BEFORE: logging handlers:", logging.getLogger().handlers, flush=True)

# ... your code ...

print("AFTER: stdout id:", id(sys.stdout), flush=True)
```

**Solution:**

Force stdout to stay connected:

```python
# At module level, before any other imports
import sys
if sys.stdout != sys.__stdout__:
    sys.stdout = sys.__stdout__

# Configure logging once, early, with force=True
import logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    force=True
)
logger = logging.getLogger(__name__)

# Now use logger instead of print
logger.info("This will show up!")
```

---

### 3. You're Not Running the Code You Think (Wrong venv/path/module)

**Why it happens:**

- Another checkout or site-packages copy is imported
- Src layout mismatch, leftover `pip install -e` in a different venv
- Prints don't show because that code path doesn't execute

**Diagnostic:**

Add at the top of `main.py` and at the start of your background function:

```python
import os, sys, inspect

print(f"PID: {os.getpid()}", flush=True)
print(f"FILE: {__file__}", flush=True)
print(f"CWD: {os.getcwd()}", flush=True)
print(f"PYTHON: {sys.executable}", flush=True)
print(f"PYTHONPATH[0]: {sys.path[0]}", flush=True)

import landing_api
print(f"PKG_DIR: {os.path.dirname(inspect.getfile(landing_api))}", flush=True)
```

**Solution:**

1. Use `src` layout:

```
repo/
  pyproject.toml
  src/
    landing_api/
      __init__.py
      ...
```

2. Editable install:

```bash
pip install -e .
```

3. Clear stale caches:

```bash
Remove-Item -Recurse -Force **/__pycache__
Remove-Item -Recurse -Force *.egg-info
Remove-Item -Recurse -Force build
Remove-Item -Recurse -Force dist
```

4. Start with explicit module path:

```bash
uvicorn landing_api.main:app --reload --host 127.0.0.1 --port 8000
```

---

### 4. Container/Logging Backend Swallows Output

**Why it happens:**

- Docker/K8s logging driver set to `none`/`gelf`/`syslog` without collector
- Container not attached to a TTY
- App prints, but nothing surfaces to logs

**Diagnostic:**

```bash
docker inspect <container> --format='{{json .HostConfig.LogConfig}}'
```

**Solution:**

In `docker-compose.yml`:

```yaml
services:
  api:
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```

Run attached while testing:

```bash
docker compose up -d
docker compose logs -f api
```

---

### 5. Background Task Never Runs or Dies Early

**Why it happens:**

- `BackgroundTasks` runs after response is sent
- Worker restarts (reload) or crashes early
- Exception before your first print/log
- Event loop setup fails

**Diagnostic:**

Add first-line instrumentation:

```python
from pathlib import Path

def _dbg(tag):
    debug_file = Path("debug.log")
    debug_file.write_text(f"{tag}\n", mode="a")

def _run_build_sync(...):
    _dbg("enter _run_build_sync")
    print("enter _run_build_sync", flush=True)
    # ... rest of code

async def _run_build(...):
    _dbg("enter _run_build")
    print("enter _run_build", flush=True)
    # ... rest of code
```

**Solution:**

1. Disable reload to rule out restarts:

```bash
uvicorn landing_api.main:app --workers 1
```

2. Wrap with try/except:

```python
try:
    print("Starting background task", flush=True)
    # ... your code ...
except Exception as e:
    logger.exception("Background task failed", exc_info=e)
    raise
```

3. Prefer staying async end-to-end:

```python
@app.post("/build")
async def build(...):
    # Don't create a new loop - use asyncio.create_task
    task = asyncio.create_task(_run_build(...))
    return {"status": "started"}
```

---

## Quick Diagnostic Checklist

✅ **Run this diagnostic:**

```powershell
# 1. Verify which Python is running
python --version
where.exe python

# 2. Check for multiple uvicorn processes
Get-Process python | Format-Table Id, ProcessName, Path -Auto

# 3. Verify imports
python -c "import landing_api; print(landing_api.__file__)"
python -c "import agents_app; print(agents_app.__file__)"

# 4. Test print with flush
python -c "import sys; print('TEST', flush=True, file=sys.stdout)"
```

✅ **Best Practices for Your Project:**

1. **Use proper logging** instead of print():

```python
import logging
logger = logging.getLogger(__name__)
logger.info("This works!")
```

2. **Always flush print()** in background tasks:

```python
print("message", flush=True)
```

3. **Configure logging early** in main.py:

```python
import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    force=True
)
```

4. **Verify you're running the right code:**

```python
print(f"Running: {__file__}", flush=True)
```

---

## Your Project-Specific Setup

Based on your codebase:

### Service Structure

- `ai/agents_app/` - Agents service (port 8001)
- `backend/landing_api/` - Main API (port 8000)
- Both use FastAPI with uvicorn

### Startup Commands

**Agents Service:**

```powershell
cd ai
.venv\Scripts\Activate.ps1
$env:PYTHONPATH='C:\DynamicBusinessLandingPage\ai'
python -m uvicorn agents_app.main:app --reload --host 127.0.0.1 --port 8001
```

**Backend Service:**

```powershell
cd backend
.venv\Scripts\Activate.ps1
uvicorn landing_api.main:app --reload --host 127.0.0.1 --port 8000
```

### Current Logging Locations

Your print statements will appear in:

- The PowerShell window where you started the service
- If using scripts/start-dev-simple.ps1, separate windows for each service
- Look for title bar: "Agents Service - Port 8001" or "Backend Server - Port 8000"

### Verify Logging is Working

```python
# Add to agents_app/main.py or landing_api/main.py
@app.on_event("startup")
async def startup_event():
    import logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        force=True
    )
    logger = logging.getLogger(__name__)
    logger.info("=" * 60)
    logger.info(f"Server starting on PID: {os.getpid()}")
    logger.info(f"Python: {sys.executable}")
    logger.info(f"Module: {__file__}")
    logger.info("=" * 60)
```
