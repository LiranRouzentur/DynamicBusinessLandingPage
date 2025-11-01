Param(
    [Parameter(Mandatory=$true, Position=0)] [string]$Query,
    [int]$MaxRetries = 3,
    [int]$HealthTimeoutSec = 120,
    [int]$PollIntervalSec = 20,
    [switch]$Headless
)

# Guard: prevent recursion if this script is run inside a server window
if ($env:IS_SERVER_WINDOW -eq '1') { 
    Write-Host "[INFO] Early exit: IS_SERVER_WINDOW=1 (Not running E2E test)" -ForegroundColor Gray
    exit 
}

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Dynamic Business Landing Page - E2E Test Runner" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Query: '$Query'" -ForegroundColor Gray
Write-Host ""

$projectRoot = Split-Path -Parent $PSScriptRoot
$backendPath = Join-Path $projectRoot "backend"
$clientPath = Join-Path $projectRoot "client"
$agentsPath = Join-Path $projectRoot "agents"
$mcpPath = Join-Path $projectRoot "mcp"
$logsPath = Join-Path $projectRoot "logs"
$pidFile = Join-Path $projectRoot ".server_pids.txt"

if (-not (Test-Path $logsPath)) { New-Item -ItemType Directory -Path $logsPath | Out-Null }
$backendLog = Join-Path $logsPath "backend.log"
$agentsLog = Join-Path $logsPath "agents.log"
$mcpLog = Join-Path $logsPath "mcp.log"
$frontendLog = Join-Path $logsPath "frontend.log"
@($backendLog, $agentsLog, $mcpLog, $frontendLog) | ForEach-Object { 
    if (Test-Path $_) { Remove-Item $_ -Force -ErrorAction SilentlyContinue }
    Set-Content -Path $_ -Value "" -Encoding UTF8 
}
${e2eOut} = Join-Path $logsPath "e2e.out.log"
${e2eErr} = Join-Path $logsPath "e2e.err.log"
if (Test-Path ${e2eOut}) { Remove-Item ${e2eOut} -Force -ErrorAction SilentlyContinue }
if (Test-Path ${e2eErr}) { Remove-Item ${e2eErr} -Force -ErrorAction SilentlyContinue }
Set-Content -Path ${e2eOut} -Value "" -Encoding UTF8
Set-Content -Path ${e2eErr} -Value "" -Encoding UTF8

$venvPath = Join-Path $backendPath ".venv"
$agentsVenvPath = Join-Path $agentsPath ".venv"
$mcpVenvPath = Join-Path $mcpPath ".venv"

# ========================================
# Clean Python cache to avoid stale bytecode issues
# ========================================
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

# ========================================
# Check for .env file
# ========================================
$envFile = Join-Path $backendPath ".env"
if (-not (Test-Path $envFile)) {
    Write-Host "WARNING: .env file not found!" -ForegroundColor Yellow
    Write-Host "   Create backend/.env with API keys" -ForegroundColor Yellow
    Write-Host ""
}

# ========================================
# Stop any existing servers on ports
# ========================================
Write-Host "Checking for existing servers..." -ForegroundColor Yellow
try {
    Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue | 
        ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }
    Get-NetTCPConnection -LocalPort 8002 -ErrorAction SilentlyContinue | 
        ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }
    Get-NetTCPConnection -LocalPort 8003 -ErrorAction SilentlyContinue | 
        ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }
    Get-NetTCPConnection -LocalPort 5173 -ErrorAction SilentlyContinue | 
        ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }
    Write-Host "Cleaned up existing server processes" -ForegroundColor Green
} catch {
    Write-Host "Warning: Could not clean up all processes (may require admin rights)" -ForegroundColor Yellow
}
Start-Sleep -Seconds 2

function Kill-Port {
    param([int]$Port)
    Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }
}

function Cleanup-Servers {
    Write-Host "`nCleaning up servers..." -ForegroundColor Yellow
    Kill-Port -Port 8000
    Kill-Port -Port 8002
    Kill-Port -Port 8003
    Kill-Port -Port 5173
    if (Test-Path $pidFile) { Remove-Item $pidFile -Force -ErrorAction SilentlyContinue }
}

Register-EngineEvent PowerShell.Exiting -Action { Cleanup-Servers } | Out-Null

function Ensure-Env {
    Write-Host "Installing dependencies..." -ForegroundColor Cyan
    Write-Host ""
    
    if (-not (Test-Path $venvPath)) { 
        Write-Host "Creating backend virtual environment..." -ForegroundColor Yellow
        python -m venv $venvPath 
        Write-Host "Backend virtual environment created" -ForegroundColor Green
    }
    if (-not (Test-Path $agentsVenvPath)) { 
        Write-Host "Creating agents virtual environment..." -ForegroundColor Yellow
        python -m venv $agentsVenvPath 
        Write-Host "Agents virtual environment created" -ForegroundColor Green
    }
    if (-not (Test-Path $mcpVenvPath)) { 
        Write-Host "Creating MCP virtual environment..." -ForegroundColor Yellow
        python -m venv $mcpVenvPath 
        Write-Host "MCP virtual environment created" -ForegroundColor Green
    }

    $backendReq = Join-Path $backendPath "requirements.txt"
    if (Test-Path $backendReq) {
        Write-Host "Installing backend dependencies from requirements.txt..." -ForegroundColor Yellow
        & (Join-Path $venvPath "Scripts\python.exe") -m pip install --upgrade pip 2>&1 | Out-Null
        & (Join-Path $venvPath "Scripts\python.exe") -m pip install -r $backendReq
        Write-Host "Backend dependencies installed" -ForegroundColor Green
    } else { Write-Host "WARNING: backend/requirements.txt not found!" -ForegroundColor Yellow }
    
    $agentsReq = Join-Path $agentsPath "requirements.txt"
    if (Test-Path $agentsReq) {
        Write-Host "Installing agents dependencies from requirements.txt..." -ForegroundColor Yellow
        & (Join-Path $agentsVenvPath "Scripts\python.exe") -m pip install --upgrade pip 2>&1 | Out-Null
        & (Join-Path $agentsVenvPath "Scripts\python.exe") -m pip install -r $agentsReq
        Write-Host "Agents dependencies installed" -ForegroundColor Green
    } else { Write-Host "WARNING: agents/requirements.txt not found!" -ForegroundColor Yellow }
    
    $mcpReq = Join-Path $mcpPath "requirements.txt"
    if (Test-Path $mcpReq) {
        Write-Host "Installing MCP dependencies from requirements.txt..." -ForegroundColor Yellow
        & (Join-Path $mcpVenvPath "Scripts\python.exe") -m pip install --upgrade pip 2>&1 | Out-Null
        & (Join-Path $mcpVenvPath "Scripts\python.exe") -m pip install -r $mcpReq
        Write-Host "MCP dependencies installed" -ForegroundColor Green
    } else { Write-Host "WARNING: mcp/requirements.txt not found!" -ForegroundColor Yellow }

    if (-not (Test-Path (Join-Path $clientPath "node_modules"))) {
        Write-Host "Installing frontend dependencies..." -ForegroundColor Yellow
        Push-Location $clientPath; npm install; Pop-Location
        Write-Host "Frontend dependencies installed" -ForegroundColor Green
    }

    Ensure-Playwright
    
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Green
    Write-Host "Dependencies ready" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Green
    Write-Host ""
}

function Ensure-Playwright {
    # Ensure Playwright browsers are installed so Chromium launches properly
    try {
        Push-Location $projectRoot
        npx --yes playwright install chromium | Out-Null
    } catch {
        Write-Host "Warning: Playwright install failed: $_" -ForegroundColor Yellow
    } finally {
        Pop-Location
    }
}

function Start-Servers {
    Write-Host "Starting servers in separate windows..." -ForegroundColor Cyan
    Write-Host ""
    Write-Host "MCP:      tcp://localhost:8003" -ForegroundColor Green
    Write-Host "Agents:   http://localhost:8002" -ForegroundColor Green
    Write-Host "Backend:  http://localhost:8000" -ForegroundColor Green
    Write-Host "Frontend: http://localhost:5173" -ForegroundColor Green
    Write-Host ""

    # MCP first:
    $mcpWindowTitle = "MCP Server - Port 8003"
    $mcpArgs = "-NoExit -Command `$env:IS_SERVER_WINDOW='1'; `$host.UI.RawUI.WindowTitle = '$mcpWindowTitle'; cd '$mcpPath'; [Console]::OutputEncoding = New-Object System.Text.UTF8Encoding `$false; [Console]::InputEncoding = New-Object System.Text.UTF8Encoding `$false; `$env:PYTHONUNBUFFERED='1'; `$env:PYTHONIOENCODING='utf-8'; `$env:PYTHONDONTWRITEBYTECODE=1; `$env:WORKSPACE_ROOT='$projectRoot\mcp\storage\workspace'; `& '$mcpVenvPath\Scripts\Activate.ps1'; python server_socket.py --profile all --host 127.0.0.1 --port 8003 2>&1 | ForEach-Object { `"`$_`"; `"`$_`" | Out-File -FilePath '$mcpLog' -Append -Encoding utf8 }"
    $mcpProcess = Start-Process powershell -ArgumentList $mcpArgs -PassThru
    Start-Sleep -Seconds 3

    # Agents
    $agentsWindowTitle = "Agents Service - Port 8002"
    $agentsArgs = "-NoExit -Command `$env:IS_SERVER_WINDOW='1'; `$host.UI.RawUI.WindowTitle = '$agentsWindowTitle'; cd '$agentsPath\app'; [Console]::OutputEncoding = New-Object System.Text.UTF8Encoding `$false; [Console]::InputEncoding = New-Object System.Text.UTF8Encoding `$false; `$env:VIRTUAL_ENV_DISABLE_PROMPT=1; `$env:PYTHONUNBUFFERED='1'; `$env:PYTHONIOENCODING='utf-8'; `$env:PYTHONPATH='$agentsPath'; `$env:PYTHONDONTWRITEBYTECODE=1; `& '$agentsVenvPath\Scripts\Activate.ps1'; python -m uvicorn app.main:app --reload --log-level debug --host 127.0.0.1 --port 8002 2>&1 | ForEach-Object { `"`$_`"; `"`$_`" | Out-File -FilePath '$agentsLog' -Append -Encoding utf8 }"
    $agentsProcess = Start-Process powershell -ArgumentList $agentsArgs -PassThru
    Start-Sleep -Seconds 2

    # Backend
    $backendWindowTitle = "Backend Server - Port 8000"
    $backendArgs = "-NoExit -Command `$env:IS_SERVER_WINDOW='1'; `$host.UI.RawUI.WindowTitle = '$backendWindowTitle'; cd '$backendPath'; [Console]::OutputEncoding = New-Object System.Text.UTF8Encoding `$false; [Console]::InputEncoding = New-Object System.Text.UTF8Encoding `$false; `$env:VIRTUAL_ENV_DISABLE_PROMPT=1; `$env:PYTHONUNBUFFERED='1'; `$env:PYTHONIOENCODING='utf-8'; `$env:PYTHONDONTWRITEBYTECODE=1; `& '$venvPath\Scripts\Activate.ps1'; uvicorn landing_api.main:app --reload --log-level debug --host 127.0.0.1 --port 8000 2>&1 | ForEach-Object { `"`$_`"; `"`$_`" | Out-File -FilePath '$backendLog' -Append -Encoding utf8 }"
    $backendProcess = Start-Process powershell -ArgumentList $backendArgs -PassThru
    Start-Sleep -Seconds 2

    # Frontend
    $frontendWindowTitle = "Frontend Server - Port 5173"
    $frontendArgs = "-NoExit -Command `$env:IS_SERVER_WINDOW='1'; `$host.UI.RawUI.WindowTitle = '$frontendWindowTitle'; cd '$clientPath'; [Console]::OutputEncoding = New-Object System.Text.UTF8Encoding `$false; [Console]::InputEncoding = New-Object System.Text.UTF8Encoding `$false; npm run dev 2>&1 | ForEach-Object { `"`$_`"; `"`$_`" | Out-File -FilePath '$frontendLog' -Append -Encoding utf8 }"
    $frontendProcess = Start-Process powershell -ArgumentList $frontendArgs -PassThru

    $pids = @()
    if ($mcpProcess) { $pids += $mcpProcess.Id }
    if ($agentsProcess) { $pids += $agentsProcess.Id }
    if ($backendProcess) { $pids += $backendProcess.Id }
    if ($frontendProcess) { $pids += $frontendProcess.Id }
    if ($pids.Count -gt 0) { $pids | Out-File -FilePath $pidFile -Encoding ASCII }
    
    Start-Sleep -Seconds 3
    Write-Host "[OK] Servers started in separate windows" -ForegroundColor Green
    Write-Host ""
}

function Test-HttpReady {
    param([string]$Url)
    try {
        $resp = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 3 -ErrorAction Stop
        return ($resp.StatusCode -ge 200 -and $resp.StatusCode -lt 500)
    } catch { 
        # Check if it's an HTTP error response (like 404) vs connection refused
        if ($_.Exception.Response) {
            $statusCode = [int]$_.Exception.Response.StatusCode.value__
            return ($statusCode -ge 200 -and $statusCode -lt 500)
        }
        # Connection refused or other network error - server not ready
        return $false 
    }
}

function Wait-Health {
    Write-Host "[Health Check] Starting health checks for all servers..." -ForegroundColor Cyan
    $deadline = (Get-Date).AddSeconds($HealthTimeoutSec)
    $checkCount = 0
    while ((Get-Date) -lt $deadline) {
        $checkCount++
        Write-Host "[Health Check #$checkCount] Checking server ports..." -ForegroundColor Gray
        
        $fe = Test-HttpReady -Url "http://localhost:5173"
        Write-Host "  Frontend (5173): $(if ($fe) { 'OK' } else { 'NOT READY' })" -ForegroundColor $(if ($fe) { 'Green' } else { 'Yellow' })
        
        $be = Test-HttpReady -Url "http://localhost:8000"
        Write-Host "  Backend (8000):  $(if ($be) { 'OK' } else { 'NOT READY' })" -ForegroundColor $(if ($be) { 'Green' } else { 'Yellow' })
        
        $ag = Test-HttpReady -Url "http://localhost:8002"
        Write-Host "  Agents (8002):   $(if ($ag) { 'OK' } else { 'NOT READY' })" -ForegroundColor $(if ($ag) { 'Green' } else { 'Yellow' })
        
        $mc = (Get-NetTCPConnection -LocalPort 8003 -ErrorAction SilentlyContinue) -ne $null
        Write-Host "  MCP (8003):      $(if ($mc) { 'OK' } else { 'NOT READY' })" -ForegroundColor $(if ($mc) { 'Green' } else { 'Yellow' })
        
        if ($fe -and $be -and $ag -and $mc) {
            Write-Host "[Health Check] All ports responding. Validating log patterns..." -ForegroundColor Cyan
            
            # Extra validation: look for startup lines in logs
            $okBack = (Select-String -Path $backendLog -Pattern "Uvicorn running on http://127.0.0.1:8000" -SimpleMatch -ErrorAction SilentlyContinue)
            Write-Host "  Backend log pattern:  $(if ($okBack) { 'FOUND' } else { 'NOT FOUND' })" -ForegroundColor $(if ($okBack) { 'Green' } else { 'Yellow' })
            
            $okAg = (Select-String -Path $agentsLog -Pattern "Uvicorn running on http://127.0.0.1:8002" -SimpleMatch -ErrorAction SilentlyContinue)
            Write-Host "  Agents log pattern:   $(if ($okAg) { 'FOUND' } else { 'NOT FOUND' })" -ForegroundColor $(if ($okAg) { 'Green' } else { 'Yellow' })
            
            $okFe = (Select-String -Path $frontendLog -Pattern "Local:   http://localhost:5173/" -SimpleMatch -ErrorAction SilentlyContinue)
            Write-Host "  Frontend log pattern: $(if ($okFe) { 'FOUND' } else { 'NOT FOUND' })" -ForegroundColor $(if ($okFe) { 'Green' } else { 'Yellow' })
            
            $okMcp = (Select-String -Path $mcpLog -Pattern "Listening on 127.0.0.1:8003" -SimpleMatch -ErrorAction SilentlyContinue)
            Write-Host "  MCP log pattern:      $(if ($okMcp) { 'FOUND' } else { 'NOT FOUND' })" -ForegroundColor $(if ($okMcp) { 'Green' } else { 'Yellow' })
            
            if ($okBack -and $okAg -and $okFe -and $okMcp) { 
                Write-Host "[Health Check] All servers HEALTHY!" -ForegroundColor Green
                return $true 
            }
        }
        Write-Host "[Health Check] Waiting 2s before next check..." -ForegroundColor Gray
        Write-Host ""
        Start-Sleep -Seconds 2
    }
    Write-Host "[Health Check] TIMEOUT: Servers did not become healthy within $HealthTimeoutSec seconds" -ForegroundColor Red
    return $false
}

function Tail-Errors {
    param([string[]]$Files)
    $patterns = @('ERROR', 'Error:', 'Traceback', 'Unhandled', 'ECONN', 'EADDRINUSE', 'Exception')
    foreach ($f in $Files) {
        if (-not (Test-Path $f)) { continue }
        $content = Get-Content -Path $f -Raw -ErrorAction SilentlyContinue
        foreach ($p in $patterns) { if ($content -match $p) { return @{ file = $f; pattern = $p } } }
    }
    return $null
}

function Start-LogMonitor {
    param([string]$LogFile, [string]$JobName)
    
    $monitorJob = Start-Job -Name $JobName -ScriptBlock {
        param($logPath)
        $lastPosition = 0
        $errorPatterns = @(
            'ERROR',
            'Build failed',
            'generation failed',
            'schema error',
            'validation error',
            'Exception:',
            'Traceback',
            '500 Internal Server Error',
            'phase.*ERROR',
            'Agent call failed',
            'timeout',
            'Failed to'
        )
        
        while ($true) {
            if (Test-Path $logPath) {
                $content = Get-Content $logPath -Raw -ErrorAction SilentlyContinue
                if ($content -and $content.Length -gt $lastPosition) {
                    $newContent = $content.Substring($lastPosition)
                    $lastPosition = $content.Length
                    
                    $lines = $newContent -split "`n"
                    foreach ($line in $lines) {
                        $trimmedLine = $line.Trim()
                        if ($trimmedLine) {
                            foreach ($pattern in $errorPatterns) {
                                if ($trimmedLine -match $pattern) {
                                    Write-Output "[MONITOR] $trimmedLine"
                                    break
                                }
                            }
                        }
                    }
                }
            }
            Start-Sleep -Milliseconds 500
        }
    } -ArgumentList $LogFile
    
    return $monitorJob
}

function Stop-LogMonitor {
    param($Job)
    if ($Job) {
        Stop-Job $Job -ErrorAction SilentlyContinue
        Remove-Job $Job -Force -ErrorAction SilentlyContinue
    }
}

function Get-MonitorErrors {
    param($Job)
    if ($Job) {
        return Receive-Job $Job -ErrorAction SilentlyContinue
    }
    return @()
}

function Run-Flow {
    # Resolve Node binary explicitly (compatible with older PowerShell)
    $nodeCmd = Get-Command node -ErrorAction SilentlyContinue
    if ($nodeCmd) { $node = $nodeCmd.Source } else { $node = "node" }
    
    # Build arguments array - Query needs to be quoted if it contains spaces
    # Always use debugger mode (non-headless) for UI testing
    $args = @("debuger/test-flow.js", "--query", "dominos pizza", "--url", "http://localhost:5173", "--debug")
    
    Push-Location $projectRoot
    try {
        Write-Host "[TEST] Starting Playwright with Chrome debugger mode..." -ForegroundColor Cyan
        $proc = Start-Process -FilePath $node -ArgumentList $args -PassThru -NoNewWindow -RedirectStandardOutput ${e2eOut} -RedirectStandardError ${e2eErr}
        $proc.WaitForExit()
        return $proc.ExitCode
    } finally {
        Pop-Location
    }
}

# ========================================
# SETUP PHASE (like start-dev-simple.ps1)
# ========================================

Ensure-Env
Start-Servers

# ========================================
# TRANSITION TO TEST MODE
# ========================================
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "TRANSITIONING TO TEST MODE" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Waiting for health checks..." -ForegroundColor Gray
if (-not (Wait-Health)) {
    Write-Host "Servers failed health check within timeout" -ForegroundColor Red
    Cleanup-Servers
    exit 1
}
Write-Host "All servers healthy!" -ForegroundColor Green
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "STARTING E2E TEST RUNS" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# ========================================
# MAIN TEST LOOP - Single Run with Manual Retry
# ========================================
$attempt = 1
$shouldRetry = $true

while ($shouldRetry -and $attempt -le $MaxRetries) {
    Write-Host "Attempt $attempt of $MaxRetries" -ForegroundColor Yellow
    Write-Host "[TEST] Starting Playwright E2E flow..." -ForegroundColor Magenta
    Write-Host "[TEST] Query: '$Query'" -ForegroundColor Cyan
    Write-Host "[TEST] Expected flow:" -ForegroundColor Cyan
    Write-Host "  1. Open Chrome in debugger mode (DevTools visible)" -ForegroundColor Gray
    Write-Host "  2. Navigate to frontend (http://localhost:5173)" -ForegroundColor Gray
    Write-Host "  3. Find search input field" -ForegroundColor Gray
    Write-Host "  4. Type 'dominos pizza' character by character" -ForegroundColor Gray
    Write-Host "  5. Wait for Google Places autocomplete dropdown" -ForegroundColor Gray
    Write-Host "  6. Select a random autocomplete result" -ForegroundColor Gray
    Write-Host "  7. Monitor build progress through progress log" -ForegroundColor Gray
    Write-Host "  8. Wait for build completion (READY phase or iframe content)" -ForegroundColor Gray
    Write-Host "  9. Verify landing page is displayed in iframe" -ForegroundColor Gray
    Write-Host ""
    
    # Start log monitors for backend and agents
    Write-Host "[MONITOR] Starting log monitors for backend and agents..." -ForegroundColor Cyan
    $backendMonitor = Start-LogMonitor -LogFile $backendLog -JobName "BackendMonitor"
    $agentsMonitor = Start-LogMonitor -LogFile $agentsLog -JobName "AgentsMonitor"
    
    try {
        $code = Run-Flow
        
        # Check for errors captured by monitors
        Write-Host "[MONITOR] Checking for errors in logs..." -ForegroundColor Cyan
        $backendErrors = Get-MonitorErrors -Job $backendMonitor
        $agentsErrors = Get-MonitorErrors -Job $agentsMonitor
        
        if ($backendErrors -or $agentsErrors) {
            Write-Host "[MONITOR] ERRORS DETECTED IN LOGS:" -ForegroundColor Red
            if ($backendErrors) {
                Write-Host "  Backend Errors:" -ForegroundColor Red
                $backendErrors | ForEach-Object { Write-Host "    $_" -ForegroundColor Red }
            }
            if ($agentsErrors) {
                Write-Host "  Agents Errors:" -ForegroundColor Red
                $agentsErrors | ForEach-Object { Write-Host "    $_" -ForegroundColor Red }
            }
            
            # If test passed but logs show errors, mark as failed
            if ($code -eq 0 -and ($backendErrors.Count -gt 0 -or $agentsErrors.Count -gt 0)) {
                Write-Host "[MONITOR] Test appeared to pass, but errors were detected in logs. Marking as FAILED." -ForegroundColor Red
                $code = 1
            }
        } else {
            Write-Host "[MONITOR] No errors detected in logs" -ForegroundColor Green
        }
    } finally {
        # Always stop monitors
        Stop-LogMonitor -Job $backendMonitor
        Stop-LogMonitor -Job $agentsMonitor
    }
    
    Write-Host ""
    Write-Host ("Playwright logs: {0} | {1}" -f ${e2eOut}, ${e2eErr}) -ForegroundColor Gray
    Write-Host "[TEST] Playwright flow complete with exit code: $code" -ForegroundColor Magenta
    Write-Host ""
    
    # Show last few lines of e2e logs for context
    if (Test-Path ${e2eOut}) {
        Write-Host "[TEST] Last output lines:" -ForegroundColor Cyan
        Get-Content ${e2eOut} -Tail 10 | ForEach-Object { Write-Host "  $_" -ForegroundColor Gray }
    }
    if (Test-Path ${e2eErr}) {
        $errLines = Get-Content ${e2eErr}
        if ($errLines) {
            Write-Host "[TEST] Error output:" -ForegroundColor Red
            $errLines | ForEach-Object { Write-Host "  $_" -ForegroundColor Red }
        }
    }
    Write-Host ""
    # Show captured screenshots
    Write-Host "[SNAPSHOTS] Checking for captured screenshots..." -ForegroundColor Cyan
    $screenshots = Get-ChildItem "$logsPath\*.png" -ErrorAction SilentlyContinue | Sort-Object Name
    if ($screenshots) {
        Write-Host "[SNAPSHOTS] Found $($screenshots.Count) screenshot(s):" -ForegroundColor Cyan
        $screenshots | ForEach-Object {
            $sizeKB = [math]::Round($_.Length/1KB, 2)
            Write-Host "  [SCREENSHOT] $($_.Name) - $sizeKB KB" -ForegroundColor Gray
        }
    } else {
        Write-Host "[SNAPSHOTS] No screenshots captured" -ForegroundColor Yellow
    }
    Write-Host ""
    
    # ========================================
    # DEEP ANALYSIS OF BUILD RESULTS
    # ========================================
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "BUILD ANALYSIS" -ForegroundColor Cyan
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host ""
    
    # 1. Build Status
    Write-Host "[1] BUILD STATUS:" -ForegroundColor Yellow
    if ($code -eq 0) {
        Write-Host "  ✅ E2E flow completed successfully" -ForegroundColor Green
    } else {
        Write-Host "  ❌ E2E flow failed with exit code $code" -ForegroundColor Red
    }
    Write-Host ""
    
    # 2. Final Build Phase
    Write-Host "[2] FINAL BUILD PHASE:" -ForegroundColor Yellow
    $finalPhase = Get-Content $backendLog -Tail 50 | Select-String -Pattern "phase=(\w+)" | Select-Object -Last 1
    if ($finalPhase) {
        Write-Host "  $finalPhase" -ForegroundColor Gray
    } else {
        Write-Host "  (No phase detected)" -ForegroundColor Gray
    }
    Write-Host ""
    
    # 3. Generator Attempts
    Write-Host "[3] GENERATOR ATTEMPTS:" -ForegroundColor Yellow
    $genAttempts = Get-Content $agentsLog | Select-String -Pattern "Generator attempt|Creative sampling" | ForEach-Object { "  $_" }
    if ($genAttempts) {
        $genAttempts | ForEach-Object { Write-Host $_ -ForegroundColor Gray }
    } else {
        Write-Host "  (No generator attempts logged)" -ForegroundColor Gray
    }
    Write-Host ""
    
    # 4. Validation Results
    Write-Host "[4] VALIDATION RESULTS:" -ForegroundColor Yellow
    $validationPassed = Get-Content $agentsLog | Select-String -Pattern "Validation passed|All validators passed" | Select-Object -Last 1
    $validationErrors = Get-Content $agentsLog | Select-String -Pattern "validation error|iframe.*failed|mcp.*failed" -CaseSensitive:$false
    if ($validationPassed) {
        Write-Host "  ✅ All validators passed" -ForegroundColor Green
    } elseif ($validationErrors) {
        Write-Host "  ❌ Validation errors detected:" -ForegroundColor Red
        $validationErrors | Select-Object -First 5 | ForEach-Object { Write-Host "    $_" -ForegroundColor Red }
    } else {
        Write-Host "  (No validation results)" -ForegroundColor Gray
    }
    Write-Host ""
    
    # 5. Token Usage (if available)
    Write-Host "[5] TOKEN USAGE:" -ForegroundColor Yellow
    $tokenLogs = Get-Content $agentsLog | Select-String -Pattern "TOKEN_SAVINGS|input_tokens|output_tokens" | Select-Object -Last 3
    if ($tokenLogs) {
        $tokenLogs | ForEach-Object { Write-Host "  $_" -ForegroundColor Gray }
    } else {
        Write-Host "  (No token usage logged)" -ForegroundColor Gray
    }
    Write-Host ""
    
    # 6. Creative Parameters
    Write-Host "[6] CREATIVE PARAMETERS USED:" -ForegroundColor Yellow
    $creativeParams = Get-Content $agentsLog | Select-String -Pattern "Creative sampling.*temp.*top_p" | Select-Object -Last 1
    if ($creativeParams) {
        Write-Host "  $creativeParams" -ForegroundColor Gray
    } else {
        Write-Host "  (No creative parameters logged)" -ForegroundColor Gray
    }
    Write-Host ""
    
    # 7. Errors Summary
    Write-Host "[7] ERRORS SUMMARY:" -ForegroundColor Yellow
    $recentErrors = Get-Content $backendLog,$agentsLog,$mcpLog | Select-String -Pattern "ERROR|Exception|failed" -CaseSensitive:$false | Select-Object -Last 10
    if ($recentErrors) {
        Write-Host "  Found errors in logs:" -ForegroundColor Red
        $recentErrors | ForEach-Object { Write-Host "    $_" -ForegroundColor Red }
    } else {
        Write-Host "  ✅ No errors detected in logs" -ForegroundColor Green
    }
    Write-Host ""
    
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host ""
    
    # Decision point: stop or retry?
    if ($code -eq 0) {
        Write-Host "✅ TEST PASSED - Analysis complete" -ForegroundColor Green
        Write-Host "Review screenshots in: $logsPath" -ForegroundColor Cyan
        $shouldRetry = $false
    } else {
        Write-Host "❌ TEST FAILED - Analysis complete" -ForegroundColor Red
        Write-Host "Check screenshots in: $logsPath for debugging" -ForegroundColor Yellow
        
        # Prompt for manual retry decision
        if ($attempt -lt $MaxRetries) {
            Write-Host ""
            Write-Host "═══════════════════════════════════════" -ForegroundColor Yellow
            Write-Host "MANUAL RETRY DECISION REQUIRED" -ForegroundColor Yellow
            Write-Host "═══════════════════════════════════════" -ForegroundColor Yellow
            Write-Host ""
            Write-Host "Do you want to retry this test? (Y/N)" -ForegroundColor Cyan
            Write-Host "  [Y] = Retry with same query" -ForegroundColor Gray
            Write-Host "  [N] = Stop and keep Chrome window open for inspection" -ForegroundColor Gray
            Write-Host ""
            
            $response = Read-Host "Enter your choice"
            
            if ($response -match '^[Yy]') {
                Write-Host ""
                Write-Host "[RETRY] User approved retry $($attempt + 1)..." -ForegroundColor Yellow
                Write-Host "[RETRY] Waiting for Playwright cleanup..." -ForegroundColor Gray
                Start-Sleep -Seconds 3
                $attempt++
            } else {
                Write-Host ""
                Write-Host "[STOP] User declined retry. Keeping Chrome open for manual inspection..." -ForegroundColor Yellow
                $shouldRetry = $false
            }
        } else {
            Write-Host ""
            Write-Host "[MAX RETRIES] Reached maximum retry limit ($MaxRetries)" -ForegroundColor Red
            $shouldRetry = $false
        }
    }
}

# ========================================
# CLEANUP
# ========================================
Write-Host ""
Write-Host "Cleaning up..." -ForegroundColor Yellow

# IMPORTANT: Do NOT auto-close Chrome to allow manual inspection
# Only close if test failed AND user declined retry
Write-Host ""
Write-Host "⚠️  Chrome debugger window is KEPT OPEN for manual inspection" -ForegroundColor Cyan
Write-Host "   You can manually close it when done analyzing the results." -ForegroundColor Gray
Write-Host ""

# Clean up servers
Cleanup-Servers
Write-Host ""
Write-Host "Done." -ForegroundColor Green
