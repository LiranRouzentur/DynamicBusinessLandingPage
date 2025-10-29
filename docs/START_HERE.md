# 🚀 Quick Start Guide

## ✅ Everything is Running!

### **Backend**

- **URL**: http://localhost:8000
- **Status**: ✅ Running with auto-reload
- **Logs**: Check the "Backend" PowerShell window

### **Frontend**

- **URL**: http://localhost:5173
- **Status**: ✅ Running with hot reload
- **Logs**: Check the "Frontend" PowerShell window

---

## 🎯 What to Do Now

### **1. Open the Application**

Go to: **http://localhost:5173**

### **2. Test the Build Process**

The frontend has:

- **Left Panel**: Google Maps search (needs your Google API key)
- **Right Panel**: Will display generated landing pages

---

## 📝 Important Note

### **API Keys Required**

To actually generate landing pages, add your API keys to:
**`backend/.env`**

```env
GOOGLE_MAPS_API_KEY=your_key_here
OPENAI_API_KEY=your_key_here
```

Get your keys:

- **Google Maps**: https://console.cloud.google.com/
- **OpenAI**: https://platform.openai.com/

---

## 🛠️ Development Workflow

### **Start Development**

```powershell
.\start-dev.ps1
```

This will:

1. Open Backend server in one window (auto-reload on code changes)
2. Open Frontend server in another window (hot reload on code changes)
3. Both servers watch for file changes!

### **Stop Servers**

Just close the PowerShell windows.

---

## 📂 Project Structure

```
DynamicBusinessLandingPage/
├── backend/          ← FastAPI server (Python)
│   ├── .venv/       ← Virtual environment
│   ├── app/         ← Application code
│   └── .env         ← API keys (create this!)
│
├── client/           ← React frontend
│   ├── src/         ← Source code
│   └── node_modules/ ← Dependencies
│
├── start-backend.ps1    ← Run backend only
├── start-frontend.ps1   ← Run frontend only
└── start-dev.ps1        ← Run both (USE THIS!)
```

---

## 🧪 Quick Test

```powershell
# Test backend
curl http://localhost:8000/

# Should return:
# {"name":"Dynamic Business Landing Page API","version":"1.0.0","status":"online"}
```

---

## 🎨 How It Works

1. User searches for a business in the frontend
2. Sends place_id to backend `/api/build`
3. Backend fetches data from Google Maps
4. 6 AI agents generate landing page:
   - Orchestrator (coordinates)
   - Selector (chooses design)
   - Architect (plans layout)
   - Mapper (binds content)
   - Generator (creates HTML/CSS/JS)
   - QA (validates output)
5. Generated page displayed in iframe
6. Real-time progress via SSE

---

## 📚 Next Steps

1. ✅ Open http://localhost:5173
2. ⏳ Add API keys to `backend/.env`
3. ⏳ Search for a business
4. ⏳ Watch it generate a landing page!

---

## 🆘 Troubleshooting

### Port already in use?

```powershell
# Kill existing servers
Get-Process python, node | Stop-Process -Force
```

### Servers won't start?

```powershell
# Install dependencies
cd backend
.\.venv\Scripts\activate
pip install -r requirements.txt

cd ..\client
npm install
```

### Need help?

- Check the logs in the PowerShell windows
- API docs: http://localhost:8000/docs
- Backend logs: PowerShell window titled "Backend"
- Frontend logs: PowerShell window titled "Frontend"

---

**🎉 You're all set! Start coding!**
