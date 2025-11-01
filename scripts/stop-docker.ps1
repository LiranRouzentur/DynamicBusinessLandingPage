#!/usr/bin/env pwsh
# Stop all Docker Compose services

Write-Host "🛑 Stopping Landing Page Platform (Docker)" -ForegroundColor Cyan
Write-Host "===========================================" -ForegroundColor Cyan

docker-compose down

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "✅ All services stopped" -ForegroundColor Green
} else {
    Write-Host ""
    Write-Host "❌ Failed to stop services" -ForegroundColor Red
    exit 1
}

