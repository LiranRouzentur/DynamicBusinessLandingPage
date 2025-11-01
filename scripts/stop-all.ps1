# Stop all development servers

Write-Host "Stopping all services..." -ForegroundColor Yellow

try {
    # Kill processes by port
    $ports = @(8000, 8002, 8003, 5173)
    
    foreach ($port in $ports) {
        $connections = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue
        if ($connections) {
            foreach ($conn in $connections) {
                Stop-Process -Id $conn.OwningProcess -Force -ErrorAction SilentlyContinue
                Write-Host "✓ Stopped process on port $port" -ForegroundColor Green
            }
        }
    }
    
    Write-Host ""
    Write-Host "All services stopped" -ForegroundColor Green
} catch {
    Write-Host "Error stopping services: $_" -ForegroundColor Red
}

