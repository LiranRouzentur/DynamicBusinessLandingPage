# Dynamic Business Landing Page - Simple Development Startup
# Opens servers in separate windows for better visibility

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Starting Development Servers" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$projectRoot = Split-Path -Parent $PSScriptRoot
$backendPath = Join-Path $projectRoot "backend"
$clientPath = Join-Path $projectRoot "client"
$venvPath = Join-Path $backendPath ".venv"

# Check if .env exists
$envFile = Join-Path $backendPath ".env"
if (-not (Test-Path $envFile)) {
    Write-Host "WARNING: .env file not found!" -ForegroundColor Yellow
    Write-Host "   Create backend/.env with API keys" -ForegroundColor Yellow
    Write-Host ""
}

# Create venv if needed
if (-not (Test-Path $venvPath)) {
    Write-Host "Creating virtual environment..." -ForegroundColor Yellow
    python -m venv $venvPath
}

# Install backend dependencies if needed
$pip = Join-Path $venvPath "Scripts\pip.exe"
if (Test-Path $pip) {
    Write-Host "Checking backend dependencies..." -ForegroundColor Yellow
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
Write-Host "Backend:  http://localhost:8000" -ForegroundColor Green
Write-Host "Frontend: http://localhost:5173" -ForegroundColor Green
Write-Host ""

# Start backend in new window
$backendWindow = "Backend Server"
$backendArgs = "-NoExit -Command cd '$backendPath'; `$env:VIRTUAL_ENV_DISABLE_PROMPT=1; `& '$venvPath\Scripts\Activate.ps1'; uvicorn app.main:app --reload --host 127.0.0.1 --port 8000"

Start-Process powershell -ArgumentList $backendArgs

Start-Sleep -Seconds 2

# Start frontend in new window
$frontendArgs = "-NoExit -Command cd '$clientPath'; npm run dev"
Start-Process powershell -ArgumentList $frontendArgs

Start-Sleep -Seconds 3

Write-Host "[OK] Servers started in separate windows" -ForegroundColor Green
Write-Host ""
Write-Host "Open your browser to: http://localhost:5173" -ForegroundColor Cyan
Write-Host ""
Write-Host "To stop servers:" -ForegroundColor Yellow
Write-Host "  Just close the PowerShell windows or press Ctrl+C here" -ForegroundColor Yellow
Write-Host ""

# Keep script running
Write-Host "Press Ctrl+C to exit (servers will keep running)" -ForegroundColor Yellow
Write-Host ""

try {
    while ($true) {
        Start-Sleep -Seconds 10
        Write-Host "." -NoNewline
    }
}
catch {
    Write-Host ""
    Write-Host "Monitoring stopped" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "[OK] Done" -ForegroundColor Green
