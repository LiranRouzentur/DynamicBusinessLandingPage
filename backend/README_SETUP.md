# Backend Setup Instructions

## Step 1: Create Virtual Environment

```powershell
cd backend
python -m venv .venv
.venv\Scripts\activate
```

## Step 2: Install Dependencies

```powershell
pip install -r requirements.txt
```

## Step 3: Create .env File

Create a file named `.env` in the `backend/` directory with your API keys:

```env
# Google Maps API Key
# Get from: https://console.cloud.google.com/apis/credentials
GOOGLE_MAPS_API_KEY=your_actual_key_here

# OpenAI API Key
# Get from: https://platform.openai.com/api-keys
OPENAI_API_KEY=your_actual_key_here

# Asset Storage
ASSET_STORE=./artifacts
INLINE_THRESHOLD_KB=60

# Cache Settings
CACHE_TTL_DAYS=14

# Server Configuration
BACKEND_HOST=localhost
BACKEND_PORT=8000

# Frontend Configuration
FRONTEND_URL=http://localhost:5173

# Environment
ENVIRONMENT=development
```

## Step 4: Start the Server

```powershell
uvicorn app.main:app --reload
```

Server will run on `http://localhost:8000`

## Step 5: Test the API

```powershell
# Test health endpoint
curl http://localhost:8000/health

# Test build endpoint (replace place_id with a real one)
curl -X POST http://localhost:8000/api/build `
  -H "Content-Type: application/json" `
  -d '{"place_id": "ChIJN1t_tDeuEmsRUsoyG83frY4"}'
```

## Getting API Keys

### Google Maps API Key

1. Go to https://console.cloud.google.com/
2. Create a new project (or use existing)
3. Enable "Places API"
4. Go to "Credentials" → "Create Credentials" → "API Key"
5. Copy the key

### OpenAI API Key

1. Go to https://platform.openai.com/
2. Sign up or log in
3. Go to API Keys section
4. Create a new API key
5. Copy the key (safeguard it!)

## Troubleshooting

**Module not found errors**: Make sure you activated the virtual environment

```powershell
.venv\Scripts\activate
```

**Import errors**: Make sure you're in the backend directory when running uvicorn

```powershell
cd backend
uvicorn app.main:app --reload
```

**API key errors**: Double-check your .env file has the correct variable names

