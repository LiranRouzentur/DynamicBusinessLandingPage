# Development Scripts

## Quick Start

### **Option 1: Simple (Recommended)**

Opens servers in separate windows so you can see their output:

```powershell
.\scripts\start-dev-simple.ps1
```

### **Option 2: Background Jobs**

Keeps everything in one window with background jobs:

```powershell
.\scripts\start-dev.ps1
```

---

## What These Scripts Do

Both scripts:

1. ✅ **Check for .env file** with API keys
2. ✅ **Create virtual environment** if needed
3. ✅ **Install dependencies** if missing
4. ✅ **Start backend** on http://localhost:8000 (auto-reload enabled)
5. ✅ **Start frontend** on http://localhost:5173 (hot reload enabled)
6. ✅ **Monitor for file changes** (both servers)
7. ✅ **Clean shutdown** on Ctrl+C

---

## Differences

### `start-dev-simple.ps1`

- Opens servers in **separate PowerShell windows**
- See real-time output from both servers
- Easy to debug
- Press any key in the main window to stop

### `start-dev.ps1`

- Runs everything in background jobs
- Single unified output
- Monitors job status automatically
- Ctrl+C to stop

---

## Usage

```powershell
# Simple version (recommended)
cd C:\DynamicBusinessLandingPage
.\scripts\start-dev-simple.ps1

# Background jobs version
.\scripts\start-dev.ps1
```

---

## What to Expect

You'll see:

```
========================================
Starting Development Servers
========================================

✅ Dependencies ready

🚀 Starting Backend Server...
🚀 Starting Frontend Server...

✅ Both servers are running!

📡 Backend:  http://localhost:8000
🎨 Frontend: http://localhost:5173

Open your browser to: http://localhost:5173
```

---

## Troubleshooting

### "Cannot run script because execution policy..."

Run:

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### Port already in use

The script will try to kill existing servers, but if that fails:

```powershell
# Kill manually
Get-Process | Where-Object {$_.Name -eq "python" -or $_.Name -eq "node"} | Stop-Process -Force
```

### Missing API keys

Create `backend/.env`:

```env
GOOGLE_MAPS_API_KEY=your_key
OPENAI_API_KEY=your_key
```

---

## Features

✅ Auto-reload on code changes  
✅ Hot module replacement (HMR) in frontend  
✅ Background job monitoring  
✅ Clean shutdown  
✅ Error handling  
✅ Dependency checking

Enjoy development! 🚀

