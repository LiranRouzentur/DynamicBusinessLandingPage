#!/usr/bin/env pwsh
# Start all services via Docker Compose

Write-Host "🚀 Starting Landing Page Platform (Docker)" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# Check if .env file exists
if (!(Test-Path ".env")) {
    Write-Host "⚠️  Warning: .env file not found" -ForegroundColor Yellow
    Write-Host "Creating .env from .env.example..." -ForegroundColor Yellow
    
    if (Test-Path ".env.example") {
        Copy-Item ".env.example" ".env"
        Write-Host "✓ Created .env file" -ForegroundColor Green
        Write-Host "⚠️  Please edit .env and add your API keys" -ForegroundColor Yellow
        exit 1
    } else {
        Write-Host "❌ .env.example not found. Please create .env manually" -ForegroundColor Red
        exit 1
    }
}

# Check Docker is running
try {
    docker info | Out-Null
} catch {
    Write-Host "❌ Docker is not running. Please start Docker Desktop." -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "Building and starting services..." -ForegroundColor Cyan

# Build and start all services
docker-compose up --build -d

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "✅ All services started successfully!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Services:" -ForegroundColor Cyan
    Write-Host "  🔧 MCP Server:    http://localhost:8003/health" -ForegroundColor White
    Write-Host "  🤖 Agents:        http://localhost:8001/health" -ForegroundColor White
    Write-Host "  🌐 Backend API:   http://localhost:8000/health" -ForegroundColor White
    Write-Host "  💻 Frontend:      http://localhost:5173" -ForegroundColor White
    Write-Host ""
    Write-Host "View logs:" -ForegroundColor Cyan
    Write-Host "  docker-compose logs -f [service]" -ForegroundColor Gray
    Write-Host ""
    Write-Host "Stop services:" -ForegroundColor Cyan
    Write-Host "  docker-compose down" -ForegroundColor Gray
    Write-Host ""
} else {
    Write-Host ""
    Write-Host "❌ Failed to start services" -ForegroundColor Red
    Write-Host "Check logs with: docker-compose logs" -ForegroundColor Yellow
    exit 1
}

