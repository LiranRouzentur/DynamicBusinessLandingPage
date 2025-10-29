# Setup Guide

## Prerequisites

- Python 3.11+
- Node.js 18+
- npm or yarn

## Initial Setup

### 1. Backend Setup

```bash
cd backend
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt
```

### 2. Frontend Setup

```bash
cd client
npm install
```

### 3. Environment Configuration

Create `.env` file in the backend directory:

```bash
cd backend
cp .env.example .env
# Edit .env with your API keys
```

Required environment variables:

- `GOOGLE_MAPS_API_KEY` - Get from [Google Cloud Console](https://console.cloud.google.com/)
- `OPENAI_API_KEY` - Get from [OpenAI Platform](https://platform.openai.com/)

## Running the Application

### Start Backend

```bash
cd backend
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
uvicorn app.main:app --reload
```

Backend will run on `http://localhost:8000`

### Start Frontend

```bash
cd client
npm run dev
```

Frontend will run on `http://localhost:5173`

## Development Workflow

1. Backend and frontend run on separate ports (8000 and 5173)
2. Frontend proxies API calls to backend
3. Make changes to either side and see live reload

## Project Structure

- `backend/app/` - Python FastAPI application
- `client/src/` - React TypeScript application
- `artifacts/` - Generated landing page bundles
- `docs/` - Additional documentation

## Key Files

- `Product.md` - Master PRD (source of truth)
- `PROJECT_STRUCTURE.md` - Detailed file layout
- `.env` - Environment configuration
- `backend/requirements.txt` - Python dependencies
- `client/package.json` - Node dependencies

## Next Steps

1. Configure API keys in `.env`
2. Implement Google Fetcher in `backend/app/core/google_fetcher.py`
3. Implement AI Agents in `backend/app/agents/`
4. Test end-to-end flow

