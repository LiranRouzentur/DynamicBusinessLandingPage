<!-- SPDX-License-Identifier: Proprietary -->
<!-- Copyright © 2025 Liran Rouzentur. All rights reserved. -->

# Dynamic Business Landing Page Generator

Full-stack AI-powered system that automatically generates responsive landing pages from Google Places data in under 60 seconds.

## Tech Stack

**Frontend**: React 18 + TypeScript + Vite + Tailwind CSS  
**Backend**: FastAPI + Python 3.10  
**Agents**: OpenAI GPT-4 (Responses API) + Multi-agent orchestration  
**Validation**: MCP (Model Context Protocol) + Playwright  
**APIs**: Google Places API v1, Unsplash (stock images)

## Quick Start

### Prerequisites

- Python 3.10+
- Node.js 18+
- OpenAI API Key (GPT-4 access)
- Google Maps API Key (Places API v1)
- Unsplash API Key (optional)

### Installation

```bash
# 1. Generate API key for authentication
python -c "import secrets; print(secrets.token_urlsafe(32))"
# Copy the generated key - you'll need it for both .env files

# 2. Configure backend environment
# Create backend/.env (or .env in root):
cat > .env << 'EOF'
API_KEY=your-generated-key-from-step-1
GOOGLE_MAPS_API_KEY=your-google-maps-api-key
OPENAI_API_KEY=your-openai-api-key
BACKEND_HOST=localhost
BACKEND_PORT=8000
FRONTEND_URL=http://localhost:5173
ENVIRONMENT=development
ASSET_STORE=./artifacts
INLINE_THRESHOLD_KB=60
EOF

# 3. Configure frontend environment
# Create client/.env:
cat > client/.env << 'EOF'
GOOGLE_MAPS_API_KEY=your-google-maps-api-key
API_KEY=same-key-from-step-1
EOF

# 4.  RECOMMENDED Start all services (Windows PowerShell) - Skip 4 and 5 if run.
.\scripts\start-dev-simple.ps1

# 5. Install Python dependencies
pip install -r agents/requirements.txt
pip install -r backend/requirements.txt
pip install -r mcp/requirements.txt
pip install playwright && playwright install chromium

# 6. Install client dependencies
cd client
npm install
cd ..


# Or manually:
# Terminal 1: cd mcp && uvicorn app.server:app --port 8003 --reload
# Terminal 2: cd agents && uvicorn app.main:app --port 8002 --reload
# Terminal 3: cd backend && uvicorn landing_api.main:app --port 8000 --reload
# Terminal 4: cd client && npm run dev
```

### Access

- **Frontend**: http://localhost:5173 (Vite dev server)
- **Backend API**: http://localhost:8000
- **Agents Service**: http://localhost:8002
- **MCP Server**: http://localhost:8003

## Security

### Implemented

**Authentication**

- API key authentication (`X-API-Key` header)
- Development mode: optional, Production: required

**Input Validation**

- `place_id` format validation (prevents XSS, SQLi, path traversal)
- Pydantic schema validation on all API requests

**CORS Protection**

- Backend: restricted to `FRONTEND_URL`
- MCP: restricted to localhost services only
- Production: configure via environment variables

**Content Security**

- Iframe sandboxing (`allow-scripts allow-forms allow-popups`)
- No `allow-same-origin` (prevents parent page access)
- Validation pipeline (MCP) before HTML display

**Session Management**

- Automatic cleanup (1 hour TTL)
- Background task removes stale sessions

### Recommended for Production

**Security Headers**

- X-Content-Type-Options, X-Frame-Options, X-XSS-Protection
- Strict-Transport-Security, Content-Security-Policy

**Session Storage**

- Redis for multi-instance deployments
- Session capacity limits (prevent memory exhaustion)

## Architecture

```
┌─────────────────────────────────────────┐
│  Client (React + Vite) - Port 5173     │
│  - Search interface                     │
│  - Real-time SSE progress               │
│  - Live preview iframe                  │
└────────────┬────────────────────────────┘
             │ HTTP/SSE
┌────────────▼────────────────────────────┐
│  Backend (FastAPI) - Port 8000         │
│  - REST API endpoints                   │
│  - Google Places integration            │
│  - State machine (build progress)       │
│  - Artifact storage                     │
└────────────┬────────────────────────────┘
             │ HTTP
┌────────────▼────────────────────────────┐
│  Agents Service - Port 8002             │
│  ┌───────────────────────────────────┐  │
│  │ Orchestrator                       │  │
│  │  ├─> Mapper (data enrichment)     │  │
│  │  └─> Generator (HTML creation)    │  │
│  └───────────────────────────────────┘  │
└───┬──────────────────────┬──────────────┘
    │                      │
┌───▼────────────┐   ┌────▼─────────────┐
│ OpenAI GPT-4   │   │ MCP - Port 8003  │
│ Responses API  │   │ - Validation     │
└────────────────┘   │ - Security       │
                     │ - QA checks      │
                     └──────────────────┘
```

## Client Features

### UI Components

**Left Panel**:

- Google Places autocomplete search
- Real-time build progress log (SSE)
- Phase indicators: FETCHING → ORCHESTRATING → GENERATING → QA → READY
- Error handling with retry option

**Right Panel**:

- Live preview iframe (displays generated HTML)
- Loading skeleton during generation
- Download button for final HTML
- Responsive layout (splits to stacked on mobile)

### Technologies

- **React 18**: Functional components with hooks
- **TypeScript**: Full type safety
- **Vite**: Fast HMR, optimized builds
- **Tailwind CSS**: Utility-first styling
- **SSE (Server-Sent Events)**: Real-time progress updates
- **Context API**: Global state management (BuildContext)

### Key Hooks

- `useBuildApi`: Manages build API calls (start, poll result)
- `useSSE`: Handles Server-Sent Events connection
- `useDebounce`: Debounces search input

## Agent Workflow

1. **Mapper Agent**: Enriches Google data → business summary, logo, images, colors
2. **Generator Agent**: Creates single-file HTML with Bootstrap 5, AOS, Font Awesome
3. **Orchestrator Agent**: Coordinates workflow, handles retries (max 3), parallel validation

### Validation Pipeline

- **Pre-write**: Security (no inline handlers), structure, CSP compliance
- **Iframe**: Playwright rendering, console errors, image validation
- **MCP**: HTML validity, accessibility, SEO, security

## Generated Output Features

- **Single HTML file**: Complete page with embedded CSS/JS (~50-150KB)
- **AI-generated design**: Unique visual style per business (deterministic seed)
- **Stock images**: Automatic fallback to Unsplash if business images insufficient
- **CSP-compliant**: No inline handlers, strict image source policy
- **CTA-free**: Informational only (no contact forms)
- **Responsive**: Mobile-first with Bootstrap 5 grid
- **Animated**: AOS scroll effects (fade, slide, zoom)

## API Endpoints

### Backend (Port 8000)

```
POST   /api/build              Start new build (returns session_id)
GET    /api/result/:session_id Get build result (HTML + meta)
GET    /sse/progress/:session_id Server-Sent Events (real-time updates)
POST   /api/events             Receive events from agents (internal)
GET    /health                 Health check
```

### Agents (Port 8002)

```
POST   /build                  Generate landing page
GET    /health                 Health check
```

### MCP (Port 8003)

```
POST   /mcp/tools/write_files            Write files to workspace
POST   /mcp/tools/validate_static_bundle Validate HTML bundle
POST   /mcp/tools/validator_errors       Fix validation errors
GET    /health                           Health check
```

## Design Decisions

### Why OpenAI Responses API?

- **Stateful context**: 80-90% token savings on retries via `previous_response_id`
- **Strict schemas**: Guaranteed valid JSON with `strict: True`
- **Multi-turn**: Designed for agent workflows

### Why MCP?

- **Separation of concerns**: Validation isolated from agents
- **Reusable tools**: HTTP-based, callable from any service
- **Policy-driven**: JSON configs for CSP, domains, limits

## Project Structure

```
client/                    # Frontend (React + Vite)
├── src/
│   ├── App.tsx                    # Main app component
│   ├── components/
│   │   ├── LeftPanel/             # Search + progress log
│   │   ├── RightPanel/            # Preview iframe
│   │   └── SearchCard.tsx         # Google Places search
│   ├── contexts/
│   │   └── BuildContext.tsx       # Global state
│   ├── hooks/
│   │   ├── useBuildApi.ts         # API calls
│   │   └── useSSE.ts              # Server-Sent Events
│   └── services/
│       └── google-maps.ts         # Places autocomplete
├── vite.config.ts
└── package.json

agents/                    # AI agents service
├── app/
│   ├── base_agent.py              # Responses API base class
│   ├── orchestrator/              # Workflow coordinator
│   ├── generator/                 # HTML generator
│   ├── mapper/                    # Data enricher
│   ├── core/                      # Validators
│   └── main.py                    # FastAPI entry
├── mcp_client.py
└── requirements.txt

backend/                   # Backend API
├── landing_api/
│   ├── api/                       # REST endpoints
│   │   ├── build.py               # Build workflow
│   │   ├── progress.py            # SSE endpoint
│   │   └── result.py              # Result retrieval
│   ├── core/
│   │   ├── agents_client.py       # Agents HTTP client
│   │   ├── google_fetcher.py      # Places API
│   │   └── state_machine.py       # Build state
│   └── main.py
├── artifacts/                     # Generated HTML files
└── requirements.txt

mcp/                       # Validation server
├── app/
│   └── server.py                  # FastMCP + Starlette
├── tools/                         # Validation tools
│   ├── bundle.py                  # File operations
│   ├── qa.py                      # Quality checks
│   └── fixer.py                   # Auto-fix errors
├── policies/                      # JSON configs
└── requirements.txt
```

## Environment Variables

```bash
# Required
OPENAI_API_KEY=sk-your-key-here
GOOGLE_MAPS_API_KEY=your-google-key-here

# Optional
UNSPLASH_ACCESS_KEY=your-unsplash-key-here
USE_RESPONSES_API=true              # Enable stateful context
AGENTS_DEBUG_FILES=false            # Save request/response JSON

# Service URLs (defaults)
BACKEND_URL=http://localhost:8000
AGENTS_URL=http://localhost:8002
MCP_BASE_URL=http://localhost:8003
VITE_API_BASE_URL=http://localhost:8000  # Client API endpoint
```

## AI Integration

### Responses API Stateful Context

```python
# First call: ~5000 tokens
result, response_id = await agent._call_responses_api(
    user_message=full_context,
    is_retry=False
)

# Retry: ~500 tokens (90% savings)
result, new_id = await agent._call_responses_api(
    user_message={"errors": errors},
    previous_response_id=response_id,  # Server caches context
    is_retry=True
)
```

### Visual Feedback Loop

On retry, system sends PNG screenshot to AI:

```python
result = await generator.run_with_visual_feedback(
    html=current_html,
    screenshot_base64=screenshot,  # Playwright capture
    validator_errors=errors
)
# AI analyzes rendered page → fixes spacing, contrast, alignment
```

### Design Uniqueness

```python
# Deterministic seed from place_id
seed = sha256(f"{place_id}|{primary_type}").hexdigest()[:8]

# Design knobs: grid, radius, shadows, palette, typography, animations
knobs = design_knobs(seed)
# Same business → same design, different businesses → different
```

## Development

### Client Development

```bash
cd client
npm run dev          # Start dev server (http://localhost:5173)
npm run build        # Production build
npm run preview      # Preview production build
npm run lint         # Run ESLint
npm run format       # Format with Prettier
```

### Backend Development

```bash
# Enable debug mode
export AGENTS_DEBUG_FILES=true

# Check logs
tail -f backend/logs/backend.log

# Inspect artifacts
ls backend/artifacts/{session_id}/
```

## Assumptions & Limitations

### Assumptions

- GPT-4 API access (not GPT-3.5)
- Modern browser (Chrome 90+, Firefox 88+, Safari 14+)

### Limitations

- **Single-page only**: No multi-page sites
- **English content**: No i18n support
- **Static output**: No real-time data updates
- **Cost**: ~$0.10-$0.50 per page (GPT-4)
- **Rate limits**: Google (1k/day), OpenAI (per-account)

## Troubleshooting

### Client won't start

```bash
cd client
rm -rf node_modules package-lock.json
npm install
npm run dev
```

### Backend connection refused

Check all services are running:

```bash
curl http://localhost:8000/health
curl http://localhost:8002/health
curl http://localhost:8003/health
```

### Build fails

Check logs in `backend/artifacts/{session_id}/` and enable debug:

```bash
export AGENTS_DEBUG_FILES=true
```

## Credits

- OpenAI (GPT-4), Google (Places API), Unsplash/Pexels (images)
- React, Vite, Tailwind CSS, FastAPI, Bootstrap, AOS, Font Awesome
