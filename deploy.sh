#!/bin/bash
# ============================================================================
# Production Deployment Script for AWS EC2
# ============================================================================

set -e  # Exit on error

echo "🚀 Starting production deployment..."

# Check if .env exists
if [ ! -f "/srv/app/.env" ]; then
    echo "❌ Error: /srv/app/.env not found!"
    echo "Please create /srv/app/.env with required environment variables."
    exit 1
fi

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Error: Docker is not installed!"
    echo "Please install Docker first: https://docs.docker.com/engine/install/ubuntu/"
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo "❌ Error: Docker Compose is not installed!"
    echo "Please install Docker Compose first."
    exit 1
fi

# Use 'docker compose' (v2) if available, otherwise 'docker-compose' (v1)
if docker compose version &> /dev/null; then
    DOCKER_COMPOSE="docker compose"
else
    DOCKER_COMPOSE="docker-compose"
fi

echo "📦 Building Docker images..."
$DOCKER_COMPOSE build --parallel

echo "🛑 Stopping existing containers..."
$DOCKER_COMPOSE down

echo "🧹 Cleaning up old images..."
docker image prune -f

echo "🚀 Starting services..."
$DOCKER_COMPOSE up -d

echo "⏳ Waiting for services to be healthy..."
sleep 10

echo "🔍 Checking service health..."
$DOCKER_COMPOSE ps

echo ""
echo "✅ Deployment complete!"
echo ""
echo "Services:"
echo "  Frontend:  http://localhost:3000"
echo "  Backend:   http://localhost:8000 (internal)"
echo "  Agents:    http://localhost:8002 (internal)"
echo "  MCP:       http://localhost:8003 (internal)"
echo ""
echo "To view logs:"
echo "  $DOCKER_COMPOSE logs -f [service_name]"
echo ""
echo "To stop services:"
echo "  $DOCKER_COMPOSE down"
echo ""

