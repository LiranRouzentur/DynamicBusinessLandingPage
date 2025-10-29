# Script to kill all running backend and AI server instances
# Run this to clean up leftover processes
# Note: If processes keep restarting, you may need to close terminal windows or run as administrator

Write-Host "Killing all backend and AI server processes..." -ForegroundColor Yellow
Write-Host ""

# Function to kill processes on a port (with retries)
function Kill-PortProcesses {
    param($Port, $ServiceName)
    
    $retries = 3
    $killed = @()
    
    for ($i = 1; $i -le $retries; $i++) {
        $connections = Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue
        if (-not $connections) {
            break
        }
        
        foreach ($conn in $connections) {
            $processId = $conn.OwningProcess
            if ($killed -notcontains $processId) {
                Write-Host "Killing $ServiceName process: PID $processId (attempt $i)" -ForegroundColor Yellow
                try {
                    Stop-Process -Id $processId -Force -ErrorAction Stop
                    $killed += $processId
                    Start-Sleep -Milliseconds 500
                } catch {
                    Write-Host "  Warning: Could not kill PID $processId - may need admin rights" -ForegroundColor Red
                }
            }
        }
        
        Start-Sleep -Seconds 1
    }
    
    return $killed.Count
}

# Kill backend processes
$backendCount = Kill-PortProcesses -Port 8000 -ServiceName "Backend"
Write-Host ""

# Kill AI agents server processes (port 8002)
$agentsCount = Kill-PortProcesses -Port 8002 -ServiceName "AI Agents Server"
Write-Host ""

Start-Sleep -Seconds 2

# Verify ports are free
$backendPorts = Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue
$agentsServerPorts = Get-NetTCPConnection -LocalPort 8002 -ErrorAction SilentlyContinue

if (-not $backendPorts -and -not $agentsServerPorts) {
    Write-Host "✅ SUCCESS: All servers killed! Ports 8000 and 8002 are now free." -ForegroundColor Green
} else {
    Write-Host ""
    Write-Host "⚠️  WARNING: Some processes may still be running:" -ForegroundColor Yellow
    if ($backendPorts) {
        $backendPids = $backendPorts | ForEach-Object { $_.OwningProcess } | Sort-Object -Unique
        Write-Host "  Port 8000 still in use by PIDs: $($backendPids -join ', ')" -ForegroundColor Yellow
    }
    if ($agentsServerPorts) {
        $agentsPids = $agentsServerPorts | ForEach-Object { $_.OwningProcess } | Sort-Object -Unique
        Write-Host "  Port 8002 still in use by PIDs: $($agentsPids -join ', ')" -ForegroundColor Yellow
    }
    Write-Host ""
    Write-Host "If processes keep restarting, try:" -ForegroundColor Cyan
    Write-Host "  1. Close all PowerShell/terminal windows running servers" -ForegroundColor Cyan
    Write-Host "  2. Run this script as Administrator" -ForegroundColor Cyan
    Write-Host "  3. Manually kill with: Stop-Process -Id <PID> -Force" -ForegroundColor Cyan
}

Write-Host ""
Write-Host "You can now start fresh servers using:" -ForegroundColor Cyan
Write-Host "  .\scripts\start-dev.ps1" -ForegroundColor Cyan
Write-Host "  or" -ForegroundColor Cyan
Write-Host "  .\scripts\start-dev-simple.ps1" -ForegroundColor Cyan
