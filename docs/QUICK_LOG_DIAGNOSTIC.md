# Quick Log Diagnostic - Why You Don't See Logs

## 5 Most Common Reasons

### 1. Watching the Wrong Process (Reload/Worker Mismatch)

**Problem:** uvicorn --reload spawns supervisor + child. You're viewing the wrong one.

**Check:**

```powershell
Get-Process python | Format-Table Id, ProcessName, StartTime -Auto
```

**Fix:**

```bash
uvicorn landing_api.main:app --reload --log-level debug
```

---

### 2. Stdout Gets Replaced or Muted

**Problem:** Some library changes sys.stdout after startup.

**Check:**

```python
import sys
print("stdout id:", id(sys.stdout), flush=True)
```

**Fix:**

```python
import sys
if sys.stdout != sys.__stdout__:
    sys.stdout = sys.__stdout__

import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    force=True  # ← KEY
)
logger = logging.getLogger(__name__)
logger.info("Use logger, not print()")
```

---

### 3. Running Wrong Code (Wrong venv/path)

**Problem:** Another checkout or different venv is imported.

**Check:**

```python
import os, sys
print(f"PID: {os.getpid()}", flush=True)
print(f"Python: {sys.executable}", flush=True)
print(f"Module: {__file__}", flush=True)
```

**Fix:**

```bash
# Clear caches
Remove-Item -Recurse -Force **/__pycache__
Remove-Item -Recurse -Force *.egg-info

# Explicit module path
uvicorn landing_api.main:app --host 127.0.0.1 --port 8000
```

---

### 4. Container Swallows Output

**Problem:** Docker/K8s logging driver not collecting.

**Check:**

```bash
docker inspect <container> --format='{{json .HostConfig.LogConfig}}'
```

**Fix:**

```yaml
services:
  api:
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```

---

### 5. Background Task Never Runs

**Problem:** Task dies before first print or exception occurs.

**Check:**

```python
from pathlib import Path
Path("debug.log").write_text("task started")

def _run_build_sync(...):
    Path("debug.log").write_text("enter _run_build_sync", mode="a")
    print("enter _run_build_sync", flush=True)
```

**Fix:**

```python
try:
    print("Starting background task", flush=True)
    # ... your code ...
except Exception as e:
    logger.exception("Background task failed")
    raise
```

---

## Quick Checklist

```powershell
# 1. Which Python?
python --version
where.exe python

# 2. Running processes
Get-Process python | Format-Table Id, ProcessName, Path -Auto

# 3. Correct imports?
python -c "import landing_api; print(landing_api.__file__)"

# 4. Test flush
python -c "print('TEST', flush=True)"
```

---

## The Fix Applied to Your Project

✅ **Logging configured early:**

```python
import logging
logging.basicConfig(level=logging.INFO, force=True)
logger = logging.getLogger(__name__)
```

✅ **Startup diagnostics:**

```python
@app.on_event("startup")
async def startup_event():
    logger.info(f"PID: {os.getpid()}")
    logger.info(f"Python: {sys.executable}")
    logger.info(f"Module: {__file__}")
```

✅ **Use logger instead of print:**

```python
# OLD
print("message")

# NEW
logger.info("message")
```

**Key:** Always use `flush=True` with print(), or better yet, use `logger.info()`.
