# Clean startup script - no file redirection conflicts
# Services handle their own logging to C:\DynamicBusinessLandingPage\logs\

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Starting Development Servers (Clean)" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$projectRoot = Split-Path -Parent $PSScriptRoot

# Kill any existing processes on our ports
Write-Host "Stopping any existing services..." -ForegroundColor Yellow
try {
    Get-NetTCPConnection -LocalPort 8000,8002,8003,5173 -ErrorAction SilentlyContinue | 
        ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }
    Write-Host "✓ Cleaned up existing processes" -ForegroundColor Green
} catch {
    Write-Host "No existing processes to clean up" -ForegroundColor Gray
}

Start-Sleep -Seconds 2

# Start MCP Server
Write-Host ""
Write-Host "Starting MCP Server (port 8003)..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList "-NoExit", "-Command", "`$host.UI.RawUI.WindowTitle = 'MCP Server - Port 8003'; cd '$projectRoot\mcp'; & '.\.venv\Scripts\Activate.ps1'; uvicorn app.server:app --host 127.0.0.1 --port 8003 --log-level info"

Start-Sleep -Seconds 3

# Start Agents Service  
Write-Host "Starting Agents Service (port 8002)..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList "-NoExit", "-Command", "`$host.UI.RawUI.WindowTitle = 'Agents Service - Port 8002'; cd '$projectRoot\agents'; & '.\.venv\Scripts\Activate.ps1'; `$env:PYTHONPATH='$projectRoot\agents'; uvicorn app.main:app --reload --host 127.0.0.1 --port 8002 --log-level debug"

Start-Sleep -Seconds 3

# Start Backend
Write-Host "Starting Backend (port 8000)..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$projectRoot\backend'; & '.\.venv\Scripts\Activate.ps1'; uvicorn landing_api.main:app --reload --host 127.0.0.1 --port 8000"

Start-Sleep -Seconds 3

# Start Frontend
Write-Host "Starting Frontend (port 5173)..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$projectRoot\client'; npm run dev"

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "All servers started in separate windows!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Services:" -ForegroundColor Cyan
Write-Host "  MCP:      http://localhost:8003" -ForegroundColor White
Write-Host "  Agents:   http://localhost:8002" -ForegroundColor White
Write-Host "  Backend:  http://localhost:8000" -ForegroundColor White
Write-Host "  Frontend: http://localhost:5173" -ForegroundColor White
Write-Host ""
Write-Host "All services log to their console windows" -ForegroundColor Yellow
Write-Host ""
Write-Host "Close the individual windows to stop services" -ForegroundColor Yellow
Write-Host "Or run: scripts/stop-all.ps1" -ForegroundColor Yellow
Write-Host ""

