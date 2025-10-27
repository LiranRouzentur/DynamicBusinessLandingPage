# Next Steps - Implementation Roadmap

## ✅ What's Complete

- ✅ Backend architecture fully scaffolded
- ✅ All 6 AI agents with OpenAI integration
- ✅ Google Fetcher implemented
- ✅ Cache, artifact store, state machine
- ✅ All API endpoints (build, result, progress)
- ✅ Frontend structure with React + Tailwind

## 🎯 Immediate Next Steps

### 1. **Test Backend Setup**

```bash
cd backend

# Create .env file with API keys
cat > .env << EOF
GOOGLE_MAPS_API_KEY=your_key_here
OPENAI_API_KEY=your_key_here
ASSET_STORE=./artifacts
INLINE_THRESHOLD_KB=60
CACHE_TTL_DAYS=14
EOF

# Install dependencies
python -m venv .venv
.venv\Scripts\activate  # Windows
pip install -r requirements.txt

# Test that it starts
uvicorn app.main:app --reload
```

### 2. **Test Basic Flow**

Test the build endpoint with a real place_id:

```bash
# Start backend
uvicorn app.main:app --reload

# In another terminal, test the API
curl -X POST http://localhost:8000/api/build \
  -H "Content-Type: application/json" \
  -d '{"place_id": "ChIJN1t_tDeuEmsRUsoyG83frY4"}'

# Should return: {"session_id": "...", "cached": false}
```

### 3. **Frontend Implementation Priority**

The frontend needs these components:

#### **A. Google Maps Autocomplete Integration**

- **File**: `client/src/components/LeftPanel/SearchBox.tsx`
- **Needs**: Proper Google Maps Places API integration
- **Current**: Has structure but needs actual implementation

#### **B. SSE Progress Display**

- **File**: `client/src/hooks/useSSE.ts`
- **Needs**: Better error handling and reconnection logic
- **Current**: Basic implementation

#### **C. Theme Toggle**

- **Files**: `client/src/App.tsx`, `client/src/theme/theme-provider.tsx`
- **Needs**: light mode toggle UI
- **Current**: Structure exists

### 4. **Priority Tasks**

#### **Phase 1: Get Backend Working** (Estimated: 1 hour)

1. ✅ Setup environment variables
2. ✅ Install Python dependencies
3. ⏳ Test Google Fetcher with real API key
4. ⏳ Test orchestrator with mock data
5. ⏳ Fix any runtime errors

#### **Phase 2: Frontend Integration** (Estimated: 2 hours)

1. ⏳ Implement Google Maps Autocomplete in SearchBox
2. ⏳ Wire up SSE progress display
3. ⏳ Test end-to-end flow
4. ⏳ Add error handling UI

#### **Phase 3: Polish & Testing** (Estimated: 1 hour)

1. ⏳ Add loading states
2. ⏳ Improve error messages
3. ⏳ Test with multiple place_ids
4. ⏳ Verify cache behavior

---

## 🛠️ Implementation Details

### **Frontend: Google Maps Integration**

The frontend needs to:

1. Load Google Maps JS API
2. Initialize Places Autocomplete
3. Handle place selection
4. Send place_id to backend

**Current Status**: `SearchBox.tsx` has the structure but needs the actual Google Maps SDK integration.

### **Testing Strategy**

1. **Unit Tests**: Test each agent individually with mock data
2. **Integration Tests**: Test full flow with real OpenAI (use small test budget)
3. **E2E Tests**: Test with real place_id from Google Maps
4. **Cache Tests**: Verify caching works correctly

---

## 🐛 Known Issues to Fix

1. **Google Fetcher**: Currently uses `client.place()` which may need adjustment for actual API
2. **State Management**: Session store is in-memory (needs Redis for production)
3. **Error Handling**: Some agents have basic error handling, needs to be more robust
4. **Frontend**: Google Maps integration is placeholder
5. **Dependencies**: May need to add googlemaps package to requirements.txt

---

## 📊 Progress Tracker

- [x] Project structure
- [x] Backend agents with OpenAI
- [x] Core modules (cache, fetcher, store)
- [x] API endpoints
- [x] State machine
- [ ] Google Maps SDK integration (frontend)
- [ ] End-to-end testing
- [ ] Error handling polish
- [ ] Production readiness

---

## 🚀 Quick Start Commands

```bash
# 1. Setup backend
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
# Add .env file with keys
uvicorn app.main:app --reload

# 2. Setup frontend
cd client
npm install
npm run dev

# 3. Test build
curl -X POST http://localhost:8000/api/build \
  -H "Content-Type: application/json" \
  -d '{"place_id": "ChIJN1t_tDeuEmsRUsoyG83frY4"}'
```

---

## 💡 Recommendations

**Start with:**

1. Get backend running with real API keys
2. Test with mock/sample data first
3. Then implement frontend Google Maps
4. Finally connect everything end-to-end

**Next file to work on:**

- `client/src/components/LeftPanel/SearchBox.tsx` - Google Maps Autocomplete integration
- Or add unit tests for backend agents first

Which would you like to tackle next?

1. Test the backend with real API keys
2. Implement Google Maps in the frontend
3. Add tests
4. Something else?

