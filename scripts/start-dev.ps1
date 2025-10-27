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

# Check if .env file exists
$envFile = Join-Path $backendPath ".env"
if (-not (Test-Path $envFile)) {
    Write-Host "⚠️  WARNING: .env file not found in backend folder!" -ForegroundColor Yellow
    Write-Host "   Please create backend/.env with your API keys" -ForegroundColor Yellow
    Write-Host "   See backend/README_SETUP.md for details" -ForegroundColor Yellow
    Write-Host ""
}

# Check if virtual environment exists
$venvPath = Join-Path $backendPath ".venv"
if (-not (Test-Path $venvPath)) {
    Write-Host "Creating virtual environment..." -ForegroundColor Yellow
    python -m venv $venvPath
    Write-Host "✅ Virtual environment created" -ForegroundColor Green
}

# Check if dependencies are installed
$backendDeps = Join-Path $venvPath "Scripts\pip.exe"
$clientDeps = Join-Path $clientPath "node_modules"

if (-not (Test-Path $clientDeps)) {
    Write-Host "Installing frontend dependencies..." -ForegroundColor Yellow
    Set-Location $clientPath
    npm install
    Set-Location $projectRoot
    Write-Host "✅ Frontend dependencies installed" -ForegroundColor Green
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Starting Servers..." -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "📡 Backend:  http://localhost:8000" -ForegroundColor Green
Write-Host "🎨 Frontend: http://localhost:5173" -ForegroundColor Green
Write-Host ""
Write-Host "Press Ctrl+C to stop both servers" -ForegroundColor Yellow
Write-Host ""

# Stop any existing servers
Write-Host "Checking for existing servers..." -ForegroundColor Yellow
Get-Process python, node -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -like "*uvicorn*" -or $_.CommandLine -like "*vite*" } | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 1

# Start backend in background
Write-Host "🚀 Starting Backend Server..." -ForegroundColor Cyan
$backendJob = Start-Job -ScriptBlock {
    param($venvPath, $backendPath)
    Set-Location $backendPath
    & "$venvPath\Scripts\python.exe" -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
} -ArgumentList $venvPath, $backendPath

Start-Sleep -Seconds 3

# Start frontend in background
Write-Host "🚀 Starting Frontend Server..." -ForegroundColor Cyan
$frontendJob = Start-Job -ScriptBlock {
    param($clientPath)
    Set-Location $clientPath
    & npm run dev
} -ArgumentList $clientPath

Start-Sleep -Seconds 3

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "✅ Both servers are running!" -ForegroundColor Green
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
        $backendRunning = Get-Job -Id $backendJob.Id -ErrorAction SilentlyContinue | Where-Object { $_.State -eq "Running" }
        $frontendRunning = Get-Job -Id $frontendJob.Id -ErrorAction SilentlyContinue | Where-Object { $_.State -eq "Running" }
        
        if (-not $backendRunning) {
            Write-Host "⚠️  Backend job stopped!" -ForegroundColor Yellow
            Receive-Job -Id $backendJob.Id -ErrorAction SilentlyContinue
        }
        if (-not $frontendRunning) {
            Write-Host "⚠️  Frontend job stopped!" -ForegroundColor Yellow
            Receive-Job -Id $frontendJob.Id -ErrorAction SilentlyContinue
        }
    }
}
catch {
    Write-Host ""
    Write-Host "Shutting down servers..." -ForegroundColor Yellow
}
finally {
    # Cleanup jobs
    Stop-Job $backendJob -ErrorAction SilentlyContinue
    Stop-Job $frontendJob -ErrorAction SilentlyContinue
    Remove-Job $backendJob -ErrorAction SilentlyContinue
    Remove-Job $frontendJob -ErrorAction SilentlyContinue
    
    # Also kill any remaining processes
    Get-Process python, node -ErrorAction SilentlyContinue | Where-Object { 
        $_.CommandLine -like "*uvicorn*" -or $_.CommandLine -like "*vite*" 
    } | Stop-Process -Force -ErrorAction SilentlyContinue
    
    Write-Host ""
    Write-Host "✅ Servers stopped" -ForegroundColor Green
}

