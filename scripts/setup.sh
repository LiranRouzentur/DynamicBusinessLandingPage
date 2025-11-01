#!/bin/bash

# Setup script for development environment
# Sets up isolated dependencies for both backend and AI server

set -e

echo "========================================"
echo "Setting up Dynamic Business Landing Page"
echo "========================================"
echo ""

# Get project root
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

# Backend setup with isolated dependencies
echo "Setting up backend with isolated dependencies..."
cd backend
if [ ! -d ".venv" ]; then
    echo "Creating backend virtual environment..."
    python -m venv .venv
fi
source .venv/bin/activate
echo "Upgrading pip..."
pip install --upgrade pip
echo "Installing backend dependencies from requirements.txt..."
pip install -r requirements.txt
cd "$PROJECT_ROOT"
echo "✅ Backend setup complete"
echo ""

# AI server setup with isolated dependencies
echo "Setting up AI server with isolated dependencies..."
cd agents
if [ ! -d ".venv" ]; then
    echo "Creating AI server virtual environment..."
    python -m venv .venv
fi
source .venv/bin/activate
echo "Upgrading pip..."
pip install --upgrade pip
echo "Installing AI server dependencies from requirements.txt..."
pip install -r requirements.txt
cd "$PROJECT_ROOT"
echo "✅ AI server setup complete"
echo ""

# Frontend setup
echo "Setting up frontend..."
cd client
npm install
cd "$PROJECT_ROOT"
echo "✅ Frontend setup complete"
echo ""

# Create .env file for backend
BACKEND_ENV="$PROJECT_ROOT/backend/.env"
if [ ! -f "$BACKEND_ENV" ]; then
  echo "Creating backend/.env file..."
  cat > "$BACKEND_ENV" << EOF
GOOGLE_MAPS_API_KEY=your_key_here
OPENAI_API_KEY=your_key_here
ASSET_STORE=./artifacts
INLINE_THRESHOLD_KB=60
CACHE_TTL_DAYS=14
EOF
  echo "✅ Created backend/.env - Please update with your API keys"
fi

# Create .env file for AI server
AI_ENV="$PROJECT_ROOT/ai/.env"
if [ ! -f "$AI_ENV" ]; then
  echo "Creating ai/.env file..."
  cat > "$AI_ENV" << EOF
OPENAI_API_KEY=your_key_here
BACKEND_URL=http://localhost:8000
EOF
  echo "✅ Created ai/.env - Please update with your API keys"
fi

echo ""
echo "========================================"
echo "Setup complete!"
echo "========================================"
echo ""
echo "✅ Backend virtual environment: backend/.venv"
echo "✅ AI server virtual environment: ai/.venv"
echo "✅ Frontend dependencies: client/node_modules"
echo ""
echo "To start backend:"
echo "  cd backend && source .venv/bin/activate && uvicorn landing_api.main:app --reload"
echo ""
echo "To start AI server:"
echo "  cd agents && source .venv/bin/activate && uvicorn app.main:app --reload --port 8002"
echo ""
echo "To start frontend:"
echo "  cd client && npm run dev"
echo ""


