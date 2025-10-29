# Complete Setup Guide

## Current Status

✅ **Project structure**: Complete  
✅ **All code files**: Created  
⏳ **Virtual environment**: Not created yet  
⏳ **Dependencies**: Not installed yet  
⏳ **.env file**: Not created yet  
⏳ **API keys**: Need to be obtained

---

## Step-by-Step Setup

### Step 1: Create Virtual Environment

Open PowerShell in the project root and run:

```powershell
cd backend
python -m venv .venv
```

### Step 2: Activate Virtual Environment

```powershell
.venv\Scripts\activate
```

You should see `(.venv)` at the beginning of your prompt.

### Step 3: Install Dependencies

```powershell
pip install -r requirements.txt
```

This will install all required packages (FastAPI, OpenAI, Google Maps, etc.)

### Step 4: Create .env File

Create a file named `.env` in the `backend/` folder with this content:

```env
GOOGLE_MAPS_API_KEY=PASTE_YOUR_KEY_HERE
OPENAI_API_KEY=PASTE_YOUR_KEY_HERE
ASSET_STORE=./artifacts
INLINE_THRESHOLD_KB=60
CACHE_TTL_DAYS=14
BACKEND_HOST=localhost
BACKEND_PORT=8000
FRONTEND_URL=http://localhost:5173
ENVIRONMENT=development
```

### Step 5: Get Your API Keys

#### Google Maps API Key

1. Go to https://console.cloud.google.com/
2. Create project or select existing
3. Enable **Places API**
4. Go to **Credentials** → **Create Credentials** → **API Key**
5. Copy and paste into `.env` file

#### OpenAI API Key

1. Go to https://platform.openai.com/
2. Sign up/login
3. Go to **API Keys** section
4. Create new key
5. Copy and paste into `.env` file

### Step 6: Start the Backend

```powershell
# Make sure you're in backend/ directory and venv is activated
uvicorn app.main:app --reload
```

Backend will run on `http://localhost:8000`

### Step 7: Test the Backend

Open another terminal and test:

```powershell
# Test health check
curl http://localhost:8000/health

# Should return: {"status":"healthy"}
```

---

## Frontend Setup (Optional - for later)

```powershell
cd client
npm install
npm run dev
```

Frontend will run on `http://localhost:5173`

---

## Quick Commands Cheat Sheet

```powershell
# Activate virtual environment
cd backend
.venv\Scripts\activate

# Start backend server
uvicorn app.main:app --reload

# Install new package
pip install package-name

# Update requirements.txt (after installing packages)
pip freeze > requirements.txt

# Run tests (when ready)
pytest
```

---

## Troubleshooting

**Problem**: `python: command not found`  
**Solution**: Install Python 3.11+ from python.org

**Problem**: `.venv\Scripts\activate` fails  
**Solution**: Make sure you're in the `backend/` directory

**Problem**: Module import errors  
**Solution**: Verify virtual environment is activated (you should see (.venv))

**Problem**: API key errors  
**Solution**: Double-check `.env` file is in `backend/` folder and keys are correct

---

## What We've Built

- ✅ Complete backend structure
- ✅ 6 AI agents with OpenAI integration
- ✅ Google Maps fetcher
- ✅ Cache system
- ✅ Artifact storage
- ✅ 3 API endpoints
- ✅ Real-time SSE progress
- ✅ Error handling

**Ready to test once dependencies are installed!**

