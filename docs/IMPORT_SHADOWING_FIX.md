# Import Shadowing Fix

## Problem

You had a classic Python import shadowing problem. Multiple directories named `app` existed in the project:

- `ai/app/` - Agents service
- `backend/app/` - Main API backend

When Python imports a package, it searches `sys.path` and picks the **first match**. Depending on how the server was launched, different `app` packages could be imported, causing:

- Code not running where expected
- Prints/logs appearing in the wrong process
- Unpredictable behavior

## Root Causes

1. **Multiple identical package names** on sys.path
2. **Ambiguous imports** like `from app.core...` - which `app`?
3. **Stale bytecode** in `__pycache__` directories

## Solution Applied

### 1. Renamed Packages

- `ai/app/` → `ai/agents_app/`
- `backend/app/` → `backend/landing_api/`

These unique names eliminate collisions.

### 2. Updated All Imports

**AI service imports:**

```python
# Before
from app.agents.base import AgentBase

# After
from agents_app.agents.base import AgentBase
```

**Backend imports:**

```python
# Before
from app.core.config import settings

# After
from landing_api.core.config import settings
```

### 3. Updated Startup Scripts

Modified `scripts/start-dev-simple.ps1` and `scripts/start-dev.ps1`:

```powershell
# Before
uvicorn app.main:app --reload --host 127.0.0.1 --port 8001

# After
uvicorn agents_app.main:app --reload --host 127.0.0.1 --port 8001
```

### 4. Cleaned Stale Artifacts

Removed all `__pycache__` directories to clear bytecode pointing to old paths.

### 5. Added Diagnostic Tool

Created `scripts/verify-imports.py` to verify package resolution:

```bash
python scripts/verify-imports.py
```

This script:

- Verifies each package resolves to the correct location
- Checks for collision with generic `app` package
- Reports sys.path entries that could cause issues

## Verification

Run the diagnostic to verify the fix:

```bash
cd C:\DynamicBusinessLandingPage
python scripts/verify-imports.py
```

Expected output:

```
✅ PASS: agents_app
✅ PASS: landing_api
✅ PASS: No generic 'app' package found
```

## Best Practices Going Forward

1. **Use unique package names** - Avoid generic names like `app`, `core`, `utils`
2. **Use src layout** for complex projects (prevents accidental imports from repo root)
3. **Clear **pycache**** when refactoring package structures
4. **Verify imports** after major refactoring
5. **Be explicit with module paths** in uvicorn commands

## References

This fix follows the guidance from:

- Python packaging best practices
- Avoiding import shadowing anti-patterns
- Common causes of import collisions in multi-service Python projects
