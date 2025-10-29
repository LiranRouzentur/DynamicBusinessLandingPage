# Server Status

## ✅ Both Servers Started

### **Backend (FastAPI)**

- **URL**: http://localhost:8000
- **Status**: Running
- **API Docs**: http://localhost:8000/docs
- **Test**: `curl http://localhost:8000/`

### **Frontend (React + Vite)**

- **URL**: http://localhost:5173
- **Status**: Starting
- **Wait**: May take 10-15 seconds to fully start

---

## 🎯 What You Can Do Now

### 1. **Open the Frontend**

Navigate to: **http://localhost:5173**

You should see:

- Left panel (30%): Search box for Google Maps places
- Right panel (70%): Will show generated landing pages

### 2. **Test the Backend API**

```powershell
# Test health endpoint
curl http://localhost:8000/

# Should return:
# {"name":"Dynamic Business Landing Page API","version":"1.0.0","status":"online"}
```

### 3. **Test Build Endpoint** (requires API keys in .env)

```powershell
curl -X POST http://localhost:8000/api/build `
  -H "Content-Type: application/json" `
  -d '{"place_id": "ChIJN1t_tDeuEmsRUsoyG83frY4"}'
```

---

## 🏗️ Application Architecture

### Backend → Frontend Flow

1. **User searches** for a business in the frontend
2. **Place ID** sent to `/api/build`
3. **Backend fetches** data from Google Maps
4. **Orchestrator** coordinates 6 AI agents
5. **Generates** HTML/CSS/JS bundle
6. **Returns** to frontend for display in iframe

### Real-Time Progress

- **SSE stream** shows build progress
- Phases: FETCHING → ORCHESTRATING → GENERATING → QA → READY
- Updates display in left panel

---

## ⚙️ Configuration

### Backend Settings

- **Port**: 8000
- **Environment**: Development
- **Auto-reload**: Enabled (--reload flag)

### Frontend Settings

- **Port**: 5173
- **Hot reload**: Enabled
- **Proxy**: Configured to forward `/api` and `/sse` to backend

---

## 🐛 Troubleshooting

### If frontend doesn't load:

```powershell
cd client
npm run dev
# Check the output for errors
```

### If backend doesn't respond:

```powershell
cd backend
.\.venv\Scripts\uvicorn.exe app.main:app --reload
# Check for import errors
```

### API key issues:

Make sure `backend/.env` has valid keys:

```env
GOOGLE_MAPS_API_KEY=your_key
OPENAI_API_KEY=your_key
```

---

## 📱 Open in Browser

- **Frontend**: http://localhost:5173
- **Backend**: http://localhost:8000
- **Backend API Docs**: http://localhost:8000/docs

