# How to View Server Logs

## Current Setup: Separate Windows

If you ran `start-dev-simple.ps1`, you have **3 separate PowerShell windows**:

1. **"Agents Service - Port 8001"** - Shows AI agents logs
2. **"Backend Server - Port 8000"** - Shows backend API logs
3. **"Frontend Server - Port 5173"** - Shows Vite frontend logs

### To see the logs:

- Look for these PowerShell windows on your taskbar
- Each window shows its respective server output
- The title bar shows which service it is

### If you can't find the windows:

1. Press `Alt+Tab` to cycle through open windows
2. Look for PowerShell windows with colored backgrounds
3. Check your taskbar for multiple PowerShell icons

## Alternative: Use This Command

Run this in your current terminal to see all logs in one place:

```powershell
.\start-dev-unified.ps1
```

This shows all three server logs in the same terminal window.

## Quick Check: Are Servers Running?

```powershell
# Check if ports are in use
netstat -ano | findstr "8000 8001 5173"
```

If you see those ports, your servers are running!

## View Backend/Agents Logs Right Now

If you want to see what's happening in the existing windows:

1. **Find the backend window** (port 8000) - look for "127.0.0.1:8000" in the output
2. **Find the agents window** (port 8001) - look for "127.0.0.1:8001" in the output
3. Check for any validation errors or build progress messages

## Need to Restart?

If you need to restart the servers to see logs from the beginning:

```powershell
# Kill all running servers
Get-Process python | Where-Object { $_.CommandLine -like "*uvicorn*" } | Stop-Process

# Then restart
.\scripts\start-dev-simple.ps1
```
