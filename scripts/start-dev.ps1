# Dynamic Business Landing Page - Development Startup Script
# Starts both backend and frontend with auto-reload

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Starting Development Servers" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Get the project root directory
$projectRoot = Split-Path -Parent $PSScriptRoot
$backendPath = Join-Path $projectRoot "backend"
$clientPath = Join-Path $projectRoot "client"
$agentsPath = Join-Path $projectRoot "agents"
$logsPath = Join-Path $projectRoot "logs"

# Ensure logs directory exists and initialize per-run logs (overwrite each run)
if (-not (Test-Path $logsPath)) {
    New-Item -ItemType Directory -Path $logsPath | Out-Null
}
$backendLog = Join-Path $logsPath "backend.log"
$agentsLog = Join-Path $logsPath "agents.log"
$frontendLog = Join-Path $logsPath "frontend.log"
@($backendLog, $agentsLog, $frontendLog) | ForEach-Object { Set-Content -Path $_ -Value "" -Encoding UTF8 }

# PID file to track processes for cleanup
$pidFile = Join-Path $projectRoot ".server_pids.txt"

# Cleanup function to kill all tracked processes
function Cleanup-Servers {
    Write-Host "`nCleaning up servers..." -ForegroundColor Yellow
    
    # Stop jobs if they exist
    if ($agentsJob) { Stop-Job $agentsJob -ErrorAction SilentlyContinue; Remove-Job $agentsJob -ErrorAction SilentlyContinue }
    if ($backendJob) { Stop-Job $backendJob -ErrorAction SilentlyContinue; Remove-Job $backendJob -ErrorAction SilentlyContinue }
    if ($frontendJob) { Stop-Job $frontendJob -ErrorAction SilentlyContinue; Remove-Job $frontendJob -ErrorAction SilentlyContinue }
    
    # Kill processes by port (most reliable)
    try {
        Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue | 
            ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }
        Get-NetTCPConnection -LocalPort 8002 -ErrorAction SilentlyContinue | 
            ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }
        Get-NetTCPConnection -LocalPort 5173 -ErrorAction SilentlyContinue | 
            ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }
    } catch {
        # Ignore errors
    }
    
    # Remove PID file
    if (Test-Path $pidFile) {
        Remove-Item $pidFile -Force -ErrorAction SilentlyContinue
    }
    
    Write-Host "Servers stopped" -ForegroundColor Green
}

# Register cleanup on script exit
Register-EngineEvent PowerShell.Exiting -Action { Cleanup-Servers } | Out-Null

# Check if .env file exists
$envFile = Join-Path $backendPath ".env"
if (-not (Test-Path $envFile)) {
    Write-Host "WARNING: .env file not found in backend folder!" -ForegroundColor Yellow
    Write-Host "   Please create backend/.env with your API keys" -ForegroundColor Yellow
    Write-Host "   See backend/README_SETUP.md for details" -ForegroundColor Yellow
    Write-Host ""
}

# Check if backend virtual environment exists
$venvPath = Join-Path $backendPath ".venv"
if (-not (Test-Path $venvPath)) {
    Write-Host "Creating backend virtual environment..." -ForegroundColor Yellow
    python -m venv $venvPath
    Write-Host "Backend virtual environment created" -ForegroundColor Green
}

# Install backend dependencies from requirements.txt
$backendRequirements = Join-Path $backendPath "requirements.txt"
if (Test-Path $backendRequirements) {
    Write-Host "Installing backend dependencies from requirements.txt..." -ForegroundColor Yellow
    $backendPythonExe = Join-Path $venvPath "Scripts\python.exe"
    & $backendPythonExe -m pip install --upgrade pip 2>&1 | Out-Null
    & $backendPythonExe -m pip install -r $backendRequirements
    Write-Host "Backend dependencies installed" -ForegroundColor Green
} else {
    Write-Host "WARNING: backend/requirements.txt not found!" -ForegroundColor Yellow
}

# Check if frontend dependencies are installed
$clientDeps = Join-Path $clientPath "node_modules"
if (-not (Test-Path $clientDeps)) {
    Write-Host "Installing frontend dependencies..." -ForegroundColor Yellow
    Set-Location $clientPath
    npm install
    Set-Location $projectRoot
    Write-Host "Frontend dependencies installed" -ForegroundColor Green
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Starting Servers..." -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Agents:   http://localhost:8002" -ForegroundColor Green
Write-Host "Backend:  http://localhost:8000" -ForegroundColor Green
Write-Host "Frontend: http://localhost:5173" -ForegroundColor Green
Write-Host ""
Write-Host "Press Ctrl+C to stop all servers" -ForegroundColor Yellow
Write-Host ""

# Stop any existing servers on ports 8000 and 8002
Write-Host "Checking for existing servers..." -ForegroundColor Yellow
try {
    # Kill processes on port 8000 (backend)
    Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue | 
        ForEach-Object { 
            Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue
        }
    # Kill processes on port 8002 (AI server)
    Get-NetTCPConnection -LocalPort 8002 -ErrorAction SilentlyContinue | 
        ForEach-Object { 
            Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue
        }
    Write-Host "Cleaned up existing server processes" -ForegroundColor Green
} catch {
    Write-Host "Warning: Could not clean up all processes (may require admin rights)" -ForegroundColor Yellow
}
Start-Sleep -Seconds 2

# Check if agents virtual environment exists
$agentsVenvPath = Join-Path $agentsPath ".venv"
if (-not (Test-Path $agentsVenvPath)) {
    Write-Host "Creating agents virtual environment..." -ForegroundColor Yellow
    python -m venv $agentsVenvPath
    Write-Host "Agents virtual environment created" -ForegroundColor Green
}

# Install agents dependencies from requirements.txt
$agentsRequirements = Join-Path $agentsPath "requirements.txt"
if (Test-Path $agentsRequirements) {
    Write-Host "Installing agents dependencies from requirements.txt..." -ForegroundColor Yellow
    $pythonExe = Join-Path $agentsVenvPath "Scripts\python.exe"
    & $pythonExe -m pip install --upgrade pip 2>&1 | Out-Null
    & $pythonExe -m pip install -r $agentsRequirements
    Write-Host "Agents dependencies installed" -ForegroundColor Green
} else {
    Write-Host "WARNING: agents/requirements.txt not found!" -ForegroundColor Yellow
}

# Start agents service in background
Write-Host "Starting Agents Service..." -ForegroundColor Cyan
$agentsJob = Start-Job -ScriptBlock {
    param($agentsVenvPath, $agentsPath)
    Set-Location "$agentsPath\app"
    $env:PYTHONPATH = "$agentsPath"
    $env:PYTHONDONTWRITEBYTECODE=1
    $env:PYTHONUNBUFFERED='1'
    $env:PYTHONIOENCODING='utf-8'
    [Console]::OutputEncoding = New-Object System.Text.UTF8Encoding $false
    [Console]::InputEncoding = New-Object System.Text.UTF8Encoding $false
    # Service logs to C:\DynamicBusinessLandingPage\logs\agents.log automatically
    & "$agentsVenvPath\Scripts\python.exe" -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8002 2>&1
} -ArgumentList $agentsVenvPath, $agentsPath

Start-Sleep -Seconds 3

# Start backend in background
Write-Host "Starting Backend Server..." -ForegroundColor Cyan
$backendJob = Start-Job -ScriptBlock {
    param($venvPath, $backendPath)
    Set-Location $backendPath
    $env:PYTHONDONTWRITEBYTECODE=1
    $env:PYTHONUNBUFFERED='1'
    $env:PYTHONIOENCODING='utf-8'
    [Console]::OutputEncoding = New-Object System.Text.UTF8Encoding $false
    [Console]::InputEncoding = New-Object System.Text.UTF8Encoding $false
    # Service logs automatically via Python logging
    & "$venvPath\Scripts\python.exe" -m uvicorn landing_api.main:app --reload --host 127.0.0.1 --port 8000 2>&1
} -ArgumentList $venvPath, $backendPath

Start-Sleep -Seconds 3

# Start frontend in background
Write-Host "Starting Frontend Server..." -ForegroundColor Cyan
$frontendJob = Start-Job -ScriptBlock {
    param($clientPath)
    Set-Location $clientPath
    [Console]::OutputEncoding = New-Object System.Text.UTF8Encoding $false
    [Console]::InputEncoding = New-Object System.Text.UTF8Encoding $false
    & npm run dev 2>&1
} -ArgumentList $clientPath

Start-Sleep -Seconds 3

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "All servers are running!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Open your browser to: http://localhost:5173" -ForegroundColor Cyan
Write-Host ""
Write-Host "Monitoring for changes..." -ForegroundColor Yellow
Write-Host ""

# Show jobs status
Write-Host ""
Write-Host "Monitoring jobs..." -ForegroundColor Yellow
Write-Host ""

# Wait for Ctrl+C
try {
    # Keep the script running and monitor jobs
    while ($true) {
        Start-Sleep -Seconds 5
        
        # Check if jobs are still running
        $agentsRunning = Get-Job -Id $agentsJob.Id -ErrorAction SilentlyContinue | Where-Object { $_.State -eq "Running" }
        $backendRunning = Get-Job -Id $backendJob.Id -ErrorAction SilentlyContinue | Where-Object { $_.State -eq "Running" }
        $frontendRunning = Get-Job -Id $frontendJob.Id -ErrorAction SilentlyContinue | Where-Object { $_.State -eq "Running" }
        
        if (-not $agentsRunning) {
            Write-Host "Agents job stopped!" -ForegroundColor Yellow
            Receive-Job -Id $agentsJob.Id -ErrorAction SilentlyContinue
        }
        if (-not $backendRunning) {
            Write-Host "Backend job stopped!" -ForegroundColor Yellow
            Receive-Job -Id $backendJob.Id -ErrorAction SilentlyContinue
        }
        if (-not $frontendRunning) {
            Write-Host "Frontend job stopped!" -ForegroundColor Yellow
            Receive-Job -Id $frontendJob.Id -ErrorAction SilentlyContinue
        }
    }
}
catch {
    Write-Host ""
    Write-Host "Shutting down servers..." -ForegroundColor Yellow
}
finally {
    Cleanup-Servers
}
