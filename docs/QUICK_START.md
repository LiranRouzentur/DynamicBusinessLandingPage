# Quick Start Guide

## ✅ What's Been Implemented

All Product.md specifications are now embedded directly in the code files - **no external references**.

### Backend (Fully Functional)

- ✅ 6 AI agents with complete prompts and schemas
- ✅ Google Maps API integration
- ✅ Cache layer with TTL
- ✅ Artifact storage system
- ✅ State machine for build tracking
- ✅ 3 API endpoints (build, result, progress)
- ✅ SSE streaming for real-time progress
- ✅ Error handling and fallbacks

### Frontend (Ready for Development)

- ✅ React + TypeScript + Tailwind setup
- ✅ Split layout (30/70)
- ✅ Google Maps Autocomplete UI
- ✅ SSE hook for progress tracking
- ✅ iframe display for generated pages

## 🚀 Getting Started

### 1. Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv .venv

# Activate (Windows)
.venv\Scripts\activate

# Activate (macOS/Linux)
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create .env file
echo GOOGLE_MAPS_API_KEY=your_google_key > .env
echo OPENAI_API_KEY=your_openai_key >> .env
echo ASSET_STORE=./artifacts >> .env
echo INLINE_THRESHOLD_KB=60 >> .env
echo CACHE_TTL_DAYS=14 >> .env

# Start server
uvicorn app.main:app --reload
```

Backend will run on `http://localhost:8000`

### 2. Frontend Setup

```bash
cd client

# Install dependencies
npm install

# Start development server
npm run dev
```

Frontend will run on `http://localhost:5173`

## 🧪 Testing

### Test Build Endpoint

```bash
# Start a build
curl -X POST http://localhost:8000/api/build \
  -H "Content-Type: application/json" \
  -d '{"place_id": "ChIJN1t_tDeuEmsRUsoyG83frY4"}'

# Response:
# {"session_id": "abc-123", "cached": false}
```

### Test SSE Progress

Open in browser or use curl:

```bash
curl http://localhost:8000/sse/progress/{session_id}
```

### Test Result

```bash
curl http://localhost:8000/api/result/{session_id}
```

## 📋 Implementation Details

### All Prompts Embedded

1. **Orchestrator** - 6-step workflow, validation, and audit trail
2. **Selector** - Design source selection with style keywords
3. **Architect** - Layout plan with all 6 sections (hero, gallery, about, reviews, credits, map)
4. **Mapper** - Content binding with sanitization
5. **Generator** - Bundle creation (HTML, CSS, JS)
6. **QA** - Validation for a11y, performance, and policy

### Key Features

- **Zero External Dependencies**: All prompts in code
- **Complete Schemas**: All JSON structures embedded
- **Error Handling**: Comprehensive fallbacks
- **Caching**: 14-day TTL with LRU eviction
- **Real-time Progress**: SSE streaming
- **State Management**: Full state machine

## 🔍 File Structure

```
backend/
├── app/
│   ├── agents/           # All 6 AI agents with prompts
│   ├── api/             # Build, Result, Progress endpoints
│   ├── core/           # Google Fetcher, Cache, State Machine
│   ├── models/         # Schemas, Data Models, Errors
│   └── utils/          # Sanitization
└── requirements.txt    # Dependencies

client/
├── src/
│   ├── components/     # LeftPanel, RightPanel
│   ├── hooks/         # useSSE
│   ├── services/      # API client, Google Maps
│   └── types/         # TypeScript types
└── package.json       # Dependencies
```

## 📝 Notes

- All Product.md content is embedded in files
- No "Ref: Product.md" comments - everything is self-contained
- Prompts, schemas, and logic are all in Python files
- Ready for production deployment after testing

## 🎯 Next Development Steps

1. Add more agent sub-steps for detailed progress
2. Implement photo caching and optimization
3. Add review language detection
4. Implement bundle compression
5. Add metrics and observability

