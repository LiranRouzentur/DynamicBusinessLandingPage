# Dynamic Business Landing Page - Simple Development Startup
# Opens servers in separate windows for better visibility

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Starting Development Servers" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$projectRoot = Split-Path -Parent $PSScriptRoot
$backendPath = Join-Path $projectRoot "backend"
$clientPath = Join-Path $projectRoot "client"
$agentsPath = Join-Path $projectRoot "ai"
$venvPath = Join-Path $backendPath ".venv"
$agentsVenvPath = Join-Path $agentsPath ".venv"

# Stop any existing servers on ports 8000 and 8002
Write-Host "Checking for existing servers..." -ForegroundColor Yellow
try {
    # Kill processes on port 8000 (backend)
    Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue | 
        ForEach-Object { 
            Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue
        }
    # Kill processes on port 8002 (AI agents server)
    Get-NetTCPConnection -LocalPort 8002 -ErrorAction SilentlyContinue | 
        ForEach-Object { 
            Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue
        }
    Write-Host "Cleaned up existing server processes" -ForegroundColor Green
} catch {
    Write-Host "Warning: Could not clean up all processes (may require admin rights)" -ForegroundColor Yellow
}
Start-Sleep -Seconds 2

# Clean Python cache to avoid stale bytecode issues
Write-Host "Cleaning Python cache..." -ForegroundColor Yellow
$cacheDirs = Get-ChildItem -Path $projectRoot -Recurse -Directory -Filter "__pycache__" -ErrorAction SilentlyContinue
$cacheFiles = Get-ChildItem -Path $projectRoot -Recurse -File -Filter "*.pyc" -ErrorAction SilentlyContinue

if ($cacheDirs -or $cacheFiles) {
    if ($cacheDirs) {
        $cacheDirs | ForEach-Object { Remove-Item -Path $_.FullName -Recurse -Force -ErrorAction SilentlyContinue }
    }
    if ($cacheFiles) {
        $cacheFiles | ForEach-Object { Remove-Item -Path $_.FullName -Force -ErrorAction SilentlyContinue }
    }
    $totalItems = $cacheDirs.Count + $cacheFiles.Count
    Write-Host "Cache cleaned: removed $totalItems items" -ForegroundColor Green
} else {
    Write-Host "No cache files found" -ForegroundColor Gray
}
Write-Host ""

# Check if .env exists
$envFile = Join-Path $backendPath ".env"
if (-not (Test-Path $envFile)) {
    Write-Host "WARNING: .env file not found!" -ForegroundColor Yellow
    Write-Host "   Create backend/.env with API keys" -ForegroundColor Yellow
    Write-Host ""
}

# Create backend venv if needed
if (-not (Test-Path $venvPath)) {
    Write-Host "Creating backend virtual environment..." -ForegroundColor Yellow
    python -m venv $venvPath
    Write-Host "Backend virtual environment created" -ForegroundColor Green
}

# Install backend dependencies from requirements.txt
$backendRequirements = Join-Path $backendPath "requirements.txt"
if (Test-Path $backendRequirements) {
    Write-Host "Installing backend dependencies from requirements.txt..." -ForegroundColor Yellow
    & "$venvPath\Scripts\pip.exe" install --upgrade pip
    & "$venvPath\Scripts\pip.exe" install -r $backendRequirements
    Write-Host "Backend dependencies installed" -ForegroundColor Green
} else {
    Write-Host "WARNING: backend/requirements.txt not found!" -ForegroundColor Yellow
}

# Create agents venv if needed
if (-not (Test-Path $agentsVenvPath)) {
    Write-Host "Creating agents virtual environment..." -ForegroundColor Yellow
    python -m venv $agentsVenvPath
    Write-Host "Agents virtual environment created" -ForegroundColor Green
}

# Install agents dependencies from requirements.txt
$agentsRequirements = Join-Path $agentsPath "requirements.txt"
if (Test-Path $agentsRequirements) {
    Write-Host "Installing agents dependencies from requirements.txt..." -ForegroundColor Yellow
    & "$agentsVenvPath\Scripts\pip.exe" install --upgrade pip
    & "$agentsVenvPath\Scripts\pip.exe" install -r $agentsRequirements
    Write-Host "Agents dependencies installed" -ForegroundColor Green
} else {
    Write-Host "WARNING: ai/requirements.txt not found!" -ForegroundColor Yellow
}

# Install frontend dependencies if needed
if (-not (Test-Path (Join-Path $clientPath "node_modules"))) {
    Write-Host "Installing frontend dependencies..." -ForegroundColor Yellow
    Set-Location $clientPath
    npm install
    Set-Location $projectRoot
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "Dependencies ready" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Starting servers in separate windows..." -ForegroundColor Cyan
Write-Host ""
Write-Host "Agents:   http://localhost:8002" -ForegroundColor Green
Write-Host "Backend:  http://localhost:8000" -ForegroundColor Green
Write-Host "Frontend: http://localhost:5173" -ForegroundColor Green
Write-Host ""

# PID file to track processes for cleanup
$pidFile = Join-Path $projectRoot ".server_pids.txt"

# Cleanup function to kill all tracked processes
function Cleanup-Servers {
    Write-Host "`nCleaning up servers..." -ForegroundColor Yellow
    
    # Kill processes by port (most reliable method)
    try {
        $pidsKilled = @()
        
        # Kill backend (port 8000)
        Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue | 
            ForEach-Object { 
                $processId = $_.OwningProcess
                Stop-Process -Id $processId -Force -ErrorAction SilentlyContinue
                $pidsKilled += $processId
            }
        
        # Kill AI agents server (port 8002)
        Get-NetTCPConnection -LocalPort 8002 -ErrorAction SilentlyContinue | 
            ForEach-Object { 
                $processId = $_.OwningProcess
                Stop-Process -Id $processId -Force -ErrorAction SilentlyContinue
                $pidsKilled += $processId
            }
        
        # Kill frontend (port 5173)
        Get-NetTCPConnection -LocalPort 5173 -ErrorAction SilentlyContinue | 
            ForEach-Object { 
                $processId = $_.OwningProcess
                Stop-Process -Id $processId -Force -ErrorAction SilentlyContinue
                $pidsKilled += $processId
            }
        
        if ($pidsKilled.Count -gt 0) {
            Write-Host "Killed $($pidsKilled.Count) server process(es)" -ForegroundColor Green
        }
    } catch {
        Write-Host "Error during cleanup: $_" -ForegroundColor Red
    }
    
    # Remove PID file
    if (Test-Path $pidFile) {
        Remove-Item $pidFile -Force -ErrorAction SilentlyContinue
    }
}

# Register cleanup on script exit
Register-EngineEvent PowerShell.Exiting -Action { Cleanup-Servers } | Out-Null

# Start agents service in new window with -PassThru to get process object
Write-Host "Starting Agents Service..." -ForegroundColor Cyan
$agentsWindowTitle = "Agents Service - Port 8002"
$agentsArgs = "-NoExit -Command `$host.UI.RawUI.WindowTitle = '$agentsWindowTitle'; cd '$agentsPath'; `$env:VIRTUAL_ENV_DISABLE_PROMPT=1; `$env:PYTHONPATH='$agentsPath'; `$env:PYTHONDONTWRITEBYTECODE=1; `& '$agentsVenvPath\Scripts\Activate.ps1'; python -m uvicorn agents.main:app --reload --log-level debug --host 127.0.0.1 --port 8002"

$agentsProcess = Start-Process powershell -ArgumentList $agentsArgs -PassThru

Start-Sleep -Seconds 2

# Start backend in new window with -PassThru
Write-Host "Starting Backend Server..." -ForegroundColor Cyan
$backendWindowTitle = "Backend Server - Port 8000"
$backendArgs = "-NoExit -Command `$host.UI.RawUI.WindowTitle = '$backendWindowTitle'; cd '$backendPath'; `$env:VIRTUAL_ENV_DISABLE_PROMPT=1; `$env:PYTHONDONTWRITEBYTECODE=1; `& '$venvPath\Scripts\Activate.ps1'; uvicorn landing_api.main:app --reload --log-level debug --host 127.0.0.1 --port 8000"

$backendProcess = Start-Process powershell -ArgumentList $backendArgs -PassThru

Start-Sleep -Seconds 2

# Start frontend in new window with -PassThru
Write-Host "Starting Frontend Server..." -ForegroundColor Cyan
$frontendWindowTitle = "Frontend Server - Port 5173"
$frontendArgs = "-NoExit -Command `$host.UI.RawUI.WindowTitle = '$frontendWindowTitle'; cd '$clientPath'; npm run dev"

$frontendProcess = Start-Process powershell -ArgumentList $frontendArgs -PassThru

# Save PIDs to file for cleanup
$pids = @()
if ($agentsProcess) { $pids += $agentsProcess.Id }
if ($backendProcess) { $pids += $backendProcess.Id }
if ($frontendProcess) { $pids += $frontendProcess.Id }
if ($pids.Count -gt 0) {
    $pids | Out-File -FilePath $pidFile -Encoding ASCII
}

Start-Sleep -Seconds 3

Write-Host "[OK] Servers started in separate windows" -ForegroundColor Green
Write-Host ""
Write-Host "Open your browser to: http://localhost:5173" -ForegroundColor Cyan
Write-Host ""
Write-Host "To stop servers:" -ForegroundColor Yellow
Write-Host "  Press Ctrl+C here - servers will be automatically stopped" -ForegroundColor Yellow
Write-Host ""

# Keep script running and handle cleanup
Write-Host "Press Ctrl+C to stop all servers and exit" -ForegroundColor Yellow
Write-Host ""

try {
    while ($true) {
        Start-Sleep -Seconds 10
        Write-Host "." -NoNewline
    }
}
catch {
    Write-Host ""
    Write-Host "Stopping all servers..." -ForegroundColor Yellow
}
finally {
    Cleanup-Servers
    Write-Host ""
    Write-Host "[OK] Done" -ForegroundColor Green
}
