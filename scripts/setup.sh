#!/bin/bash

# Setup script for development environment

set -e

echo "Setting up Dynamic Business Landing Page..."

# Backend setup
echo "Setting up backend..."
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cd ..

# Frontend setup
echo "Setting up frontend..."
cd client
npm install
cd ..

# Create .env file
if [ ! -f .env ]; then
  echo "Creating .env file..."
  cat > .env << EOF
GOOGLE_MAPS_API_KEY=your_key_here
OPENAI_API_KEY=your_key_here
ASSET_STORE=./artifacts
INLINE_THRESHOLD_KB=60
CACHE_TTL_DAYS=14
EOF
  echo "Please update .env with your API keys"
fi

echo "Setup complete!"
echo "To start backend: cd backend && source .venv/bin/activate && uvicorn app.main:app --reload"
echo "To start frontend: cd client && npm run dev"


