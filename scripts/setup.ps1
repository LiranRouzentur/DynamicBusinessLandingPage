# Setup script for development environment (Windows)
# Sets up isolated dependencies for all services

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Setting up Dynamic Business Landing Page" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot

# Backend setup with isolated dependencies
Write-Host "Setting up backend with isolated dependencies..." -ForegroundColor Cyan
Set-Location "$projectRoot\backend"
if (-not (Test-Path ".venv")) {
    Write-Host "Creating backend virtual environment..." -ForegroundColor Yellow
    python -m venv .venv
}
& ".\.venv\Scripts\Activate.ps1"
Write-Host "Upgrading pip..." -ForegroundColor Yellow
python -m pip install --upgrade pip
Write-Host "Installing backend dependencies (including OpenAI SDK 2.6.1)..." -ForegroundColor Yellow
pip install -r requirements.txt
deactivate
Set-Location $projectRoot
Write-Host "✅ Backend setup complete" -ForegroundColor Green
Write-Host ""

# Agents setup with isolated dependencies
Write-Host "Setting up Agents service with isolated dependencies..." -ForegroundColor Cyan
Set-Location "$projectRoot\agents"
if (-not (Test-Path ".venv")) {
    Write-Host "Creating agents virtual environment..." -ForegroundColor Yellow
    python -m venv .venv
}
& ".\.venv\Scripts\Activate.ps1"
Write-Host "Upgrading pip..." -ForegroundColor Yellow
python -m pip install --upgrade pip
Write-Host "Installing agents dependencies (including OpenAI SDK 2.6.1)..." -ForegroundColor Yellow
pip install -r requirements.txt
deactivate
Set-Location $projectRoot
Write-Host "✅ Agents setup complete" -ForegroundColor Green
Write-Host ""

# MCP setup with isolated dependencies
Write-Host "Setting up MCP server with isolated dependencies..." -ForegroundColor Cyan
Set-Location "$projectRoot\mcp"
if (-not (Test-Path ".venv")) {
    Write-Host "Creating MCP virtual environment..." -ForegroundColor Yellow
    python -m venv .venv
}
& ".\.venv\Scripts\Activate.ps1"
Write-Host "Upgrading pip..." -ForegroundColor Yellow
python -m pip install --upgrade pip
Write-Host "Installing MCP dependencies..." -ForegroundColor Yellow
pip install -r requirements.txt
deactivate
Set-Location $projectRoot
Write-Host "✅ MCP setup complete" -ForegroundColor Green
Write-Host ""

# Frontend setup
Write-Host "Setting up frontend..." -ForegroundColor Cyan
Set-Location "$projectRoot\client"
npm install
Set-Location $projectRoot
Write-Host "✅ Frontend setup complete" -ForegroundColor Green
Write-Host ""

# Create .env file for backend if it doesn't exist
$backendEnv = "$projectRoot\backend\.env"
if (-not (Test-Path $backendEnv)) {
    Write-Host "Creating backend\.env file..." -ForegroundColor Yellow
    @"
GOOGLE_MAPS_API_KEY=your_key_here
OPENAI_API_KEY=your_key_here
ASSET_STORE=./artifacts
INLINE_THRESHOLD_KB=60
CACHE_TTL_DAYS=14
"@ | Out-File -FilePath $backendEnv -Encoding utf8
    Write-Host "✅ Created backend\.env - Please update with your API keys" -ForegroundColor Green
}

# Create .env file for agents if it doesn't exist
$agentsEnv = "$projectRoot\agents\.env"
if (-not (Test-Path $agentsEnv)) {
    Write-Host "Creating agents\.env file..." -ForegroundColor Yellow
    @"
OPENAI_API_KEY=your_key_here
BACKEND_URL=http://localhost:8000
MCP_URL=http://localhost:8003
USE_RESPONSES_API=true
AGENTS_DEBUG_FILES=false
"@ | Out-File -FilePath $agentsEnv -Encoding utf8
    Write-Host "✅ Created agents\.env - Please update with your API keys" -ForegroundColor Green
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "Setup complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "✅ Backend virtual environment: backend\.venv" -ForegroundColor White
Write-Host "✅ Agents virtual environment: agents\.venv" -ForegroundColor White
Write-Host "✅ MCP virtual environment: mcp\.venv" -ForegroundColor White
Write-Host "✅ Frontend dependencies: client\node_modules" -ForegroundColor White
Write-Host ""
Write-Host "✅ OpenAI SDK 2.6.1 installed in all Python services" -ForegroundColor Cyan
Write-Host ""
Write-Host "To start all services:" -ForegroundColor Yellow
Write-Host "  scripts\start-clean.ps1" -ForegroundColor White
Write-Host ""
Write-Host "Or start individually:" -ForegroundColor Yellow
Write-Host "  Backend:  cd backend && .\.venv\Scripts\Activate.ps1 && uvicorn landing_api.main:app --reload" -ForegroundColor White
Write-Host "  Agents:   cd agents && .\.venv\Scripts\Activate.ps1 && uvicorn app.main:app --reload --port 8002" -ForegroundColor White
Write-Host "  MCP:      cd mcp && .\.venv\Scripts\Activate.ps1 && uvicorn app.server:app --port 8003" -ForegroundColor White
Write-Host "  Frontend: cd client && npm run dev" -ForegroundColor White
Write-Host ""

