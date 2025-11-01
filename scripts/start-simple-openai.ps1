# Simple OpenAI Server - Startup Script
# Installs dependencies, runs request from simple_request.json
# Generates single-file HTML with quality gates and iframe preview

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Simple OpenAI Server - Landing Page Generator" -ForegroundColor Cyan
Write-Host "Using Responses API with Quality Gates" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$projectRoot = Split-Path -Parent $PSScriptRoot
$simpleServerPath = Join-Path $projectRoot "simple_openai_server"
$venvPath = Join-Path $simpleServerPath ".venv"

# Kill any existing Python processes that might be using resources
Write-Host "Checking for existing Python processes..." -ForegroundColor Yellow
try {
    $pythonProcesses = Get-Process python* -ErrorAction SilentlyContinue
    if ($pythonProcesses) {
        $pythonProcesses | Where-Object { $_.Path -like "*simple_openai_server*" } | Stop-Process -Force -ErrorAction SilentlyContinue
        Write-Host "Cleaned up existing processes" -ForegroundColor Green
    } else {
        Write-Host "No processes to clean up" -ForegroundColor Gray
    }
} catch {
    Write-Host "Warning: Could not clean up all processes" -ForegroundColor Yellow
}

Start-Sleep -Seconds 1

# Clean Python cache to avoid stale bytecode issues
Write-Host "Cleaning Python cache..." -ForegroundColor Yellow
$cacheDirs = Get-ChildItem -Path $simpleServerPath -Recurse -Directory -Filter "__pycache__" -ErrorAction SilentlyContinue
$cacheFiles = Get-ChildItem -Path $simpleServerPath -Recurse -File -Filter "*.pyc" -ErrorAction SilentlyContinue

if ($cacheDirs -or $cacheFiles) {
    if ($cacheDirs) {
        $cacheDirs | ForEach-Object { Remove-Item -Path $_.FullName -Recurse -Force -ErrorAction SilentlyContinue }
    }
    if ($cacheFiles) {
        $cacheFiles | ForEach-Object { Remove-Item -Path $_.FullName -Force -ErrorAction SilentlyContinue }
    }
    $totalItems = ($cacheDirs.Count + $cacheFiles.Count)
    Write-Host "Cache cleaned: removed $totalItems items" -ForegroundColor Green
} else {
    Write-Host "No cache files found" -ForegroundColor Gray
}
Write-Host ""

# Check if .env exists
$envFile = Join-Path $simpleServerPath ".env"
if (-not (Test-Path $envFile)) {
    Write-Host "WARNING: .env file not found!" -ForegroundColor Red
    Write-Host "   Create simple_openai_server/.env with:" -ForegroundColor Yellow
    Write-Host "   OPENAI_API_KEY=your-api-key-here" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Cannot proceed without API key!" -ForegroundColor Red
    exit 1
}

# Create venv if needed
if (-not (Test-Path $venvPath)) {
    Write-Host "Creating virtual environment..." -ForegroundColor Yellow
    python -m venv $venvPath
    Write-Host "Virtual environment created" -ForegroundColor Green
} else {
    Write-Host "Virtual environment exists" -ForegroundColor Gray
}

# Install dependencies from requirements.txt
$requirementsFile = Join-Path $simpleServerPath "requirements.txt"
if (Test-Path $requirementsFile) {
    Write-Host "Installing dependencies from requirements.txt..." -ForegroundColor Yellow
    $pythonExe = Join-Path $venvPath "Scripts\python.exe"
    & $pythonExe -m pip install --upgrade pip 2>&1 | Out-Null
    & $pythonExe -m pip install -r $requirementsFile --quiet
    Write-Host "Dependencies installed" -ForegroundColor Green
} else {
    Write-Host "WARNING: requirements.txt not found!" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "Dependencies Ready" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""

# Run the example request
Write-Host "Running example request..." -ForegroundColor Cyan
Write-Host ""

$pythonExe = Join-Path $venvPath "Scripts\python.exe"
$runScript = Join-Path $simpleServerPath "run_example.py"

if (-not (Test-Path $runScript)) {
    Write-Host "ERROR: run_example.py not found!" -ForegroundColor Red
    exit 1
}

# Execute the Python script
Set-Location $simpleServerPath
& $pythonExe $runScript

# Display results
Write-Host ""
$htmlFile = Join-Path $simpleServerPath "index.html"
$previewFile = Join-Path $simpleServerPath "preview.html"

if ($LASTEXITCODE -eq 0)
{
    Write-Host "========================================" -ForegroundColor Green
    Write-Host "SUCCESS - Landing Page Generated!" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "Generated Files:" -ForegroundColor Cyan
    Write-Host "   - simple_request.json (request sent)" -ForegroundColor Gray
    Write-Host "   - simple_response.json (response received)" -ForegroundColor Gray
    
    if (Test-Path $htmlFile)
    {
        Write-Host "   - index.html (single-file landing page)" -ForegroundColor Green
    }
    
    if (Test-Path $previewFile)
    {
        Write-Host "   - preview.html (iframe preview)" -ForegroundColor Green
        Write-Host ""
        Write-Host "Open preview in browser:" -ForegroundColor Cyan
        Write-Host "   $previewFile" -ForegroundColor Yellow
        Write-Host ""
        Write-Host "Or view the landing page directly:" -ForegroundColor Cyan
        Write-Host "   $htmlFile" -ForegroundColor Yellow
    }
    elseif (Test-Path $htmlFile)
    {
        Write-Host ""
        Write-Host "Open landing page in browser:" -ForegroundColor Cyan
        Write-Host "   $htmlFile" -ForegroundColor Yellow
    }
    else
    {
        Write-Host ""
        Write-Host "Note: No HTML content generated" -ForegroundColor Gray
    }
}
else
{
    Write-Host "========================================" -ForegroundColor Red
    Write-Host "FAILED" -ForegroundColor Red
    Write-Host "========================================" -ForegroundColor Red
    Write-Host ""
    Write-Host "Check error messages above" -ForegroundColor Yellow
}

Set-Location $projectRoot
Write-Host ""
Write-Host "Press any key to exit..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")

