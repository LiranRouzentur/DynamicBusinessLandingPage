# Restart only the agents service
Write-Host "Restarting Agents Service..." -ForegroundColor Cyan

$projectRoot = Split-Path -Parent $PSScriptRoot

# Kill agents service on port 8002
Write-Host "Stopping existing agents service..." -ForegroundColor Yellow
try {
    $connections = Get-NetTCPConnection -LocalPort 8002 -ErrorAction SilentlyContinue
    if ($connections) {
        $connections | ForEach-Object { 
            Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue
        }
        Write-Host "✓ Stopped agents service" -ForegroundColor Green
    } else {
        Write-Host "No existing agents service found" -ForegroundColor Gray
    }
} catch {
    Write-Host "Error stopping service: $_" -ForegroundColor Yellow
}

Start-Sleep -Seconds 2

# Start agents service
Write-Host "Starting Agents Service..." -ForegroundColor Cyan
$agentsPath = Join-Path $projectRoot "agents"
$agentsVenvPath = Join-Path $agentsPath ".venv"

Start-Process powershell -ArgumentList "-NoExit", "-Command", "`$host.UI.RawUI.WindowTitle = 'Agents Service - Port 8002'; cd '$agentsPath'; & '$agentsVenvPath\Scripts\Activate.ps1'; `$env:PYTHONPATH='$agentsPath'; `$env:LOG_TO_FILE='false'; uvicorn app.main:app --reload --host 127.0.0.1 --port 8002 --log-level debug"

Write-Host ""
Write-Host "✓ Agents service restarted on port 8002" -ForegroundColor Green
Write-Host "Check the agents console window for detailed logs" -ForegroundColor Yellow
Write-Host ""

