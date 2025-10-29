# Project Structure Draft

Based on Product.md specifications

```
DynamicBusinessLandingPage/
│
├── README.md                         # Project overview, quick start
├── Product.md                        # Master PRD (source of truth)
├── .env.example                     # Environment template
├── .gitignore
│
├── ai/                                # AI Agents Service (Ref: Product.md > Section 2)
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                  # Agents service entry point
│   │   ├── agent_core.py            # Core agent orchestration
│   │   ├── event_bridge.py          # Event communication bridge
│   │   ├── types.py                 # Type definitions
│   │   │
│   │   └── agents/                  # AI agent implementations
│   │       ├── __init__.py
│   │       ├── base.py              # Base agent class
│   │       ├── orchestrator.py      # Main orchestrator
│   │       ├── designer/            # Design agent
│   │       ├── mapper/              # Content mapper agent
│   │       ├── generator/           # Generator agent
│   │       └── qa/                  # QA agent
│   │
│   ├── requirements.txt             # Python dependencies
│   └── pyproject.toml
│
├── backend/                          # FastAPI server (Ref: Product.md > Section 9)
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                  # FastAPI app entry, routes
│   │   │
│   │   ├── api/                     # API endpoints
│   │   │   ├── __init__.py
│   │   │   ├── build.py            # POST /api/build
│   │   │   ├── result.py           # GET /api/result/{sessionId}
│   │   │   └── progress.py         # GET /sse/progress/{sessionId}
│   │   │
│   │   ├── core/                    # Core business logic
│   │   │   ├── __init__.py
│   │   │   ├── config.py           # Settings (env vars)
│   │   │   ├── cache.py            # Cache layer (Ref: Product.md > Section 2)
│   │   │   ├── google_fetcher.py   # Google Maps API client (Ref: Product.md > Section 2)
│   │   │   ├── artifact_store.py   # File storage (Ref: Product.md > Section 9)
│   │   │   ├── state_machine.py    # Build state transitions (Ref: Product.md > Section 3)
│   │   │   └── agents_client.py    # Client for agents service
│   │   │
│   │   ├── models/                  # Pydantic models
│   │   │   ├── __init__.py
│   │   │   ├── schemas.py          # Request/Response models (Ref: Product.md > Section 4)
│   │   │   ├── normalized_data.py    # Normalized place payload (Ref: Product.md > Section 5)
│   │   │   └── errors.py            # Error models (Ref: Product.md > Section 8)
│   │   │
│   │   ├── utils/                   # Utilities
│   │   │   ├── __init__.py
│   │   │   ├── sanitization.py     # HTML sanitization (Ref: Product.md > Section 6)
│   │   │   ├── logging.py          # Structured logging
│   │   │   └── validation.py       # Input validation
│   │   │
│   │   └── tests/                   # Tests
│   │       ├── __init__.py
│   │       ├── test_google_fetcher.py
│   │       ├── test_orchestrator.py
│   │       ├── test_sanitization.py
│   │       └── fixtures/
│   │           └── sample_place_data.json
│   │
│   ├── requirements.txt             # Python dependencies
│   ├── pyproject.toml
│   └── pytest.ini
│
├── client/                          # React frontend (Ref: Product.md > Section 9)
│   ├── package.json
│   ├── vite.config.ts
│   ├── tsconfig.json
│   ├── tailwind.config.js
│   ├── postcss.config.js
│   │
│   ├── public/
│   │   └── favicon.ico
│   │
│   ├── src/
│   │   ├── App.tsx                 # Main app component
│   │   ├── main.tsx
│   │   ├── index.css               # Base styles + Tailwind imports
│   │   │
│   │   ├── components/
│   │   │   ├── LeftPanel/          # Left panel (30%) (Ref: Product.md > Section 1)
│   │   │   │   ├── index.tsx
│   │   │   │   ├── SearchBox.tsx  # Google Maps Autocomplete
│   │   │   │   └── ProgressLog.tsx # SSE log display
│   │   │   │
│   │   │   └── RightPanel/         # Right panel (70%) (Ref: Product.md > Section 1)
│   │   │       ├── index.tsx
│   │   │       └── SiteFrame.tsx   # iframe container
│   │   │
│   │   ├── hooks/
│   │   │   ├── useSSE.ts          # SSE connection hook
│   │   │   └── useBuildStatus.ts
│   │   │
│   │   ├── services/
│   │   │   ├── api.ts             # API client (axios/fetch)
│   │   │   └── google-maps.ts     # Places Autocomplete wrapper
│   │   │
│   │   ├── types/
│   │   │   ├── api.ts             # TypeScript types
│   │   │   └── models.ts
│   │   │
│   │   ├── utils/
│   │   │   └── constants.ts
│   │   │
│   │   └── theme/
│   │       ├── theme.ts           # light theme config
│   │       └── theme-provider.tsx
│   │
│   └── tests/
│       ├── App.test.tsx
│       └── components/
│
├── artifacts/                       # Generated bundles (Ref: Product.md > Section 9)
│   └── {sessionId}/
│       ├── index.html
│       ├── styles.css
│       └── app.js
│
├── docs/                            # Additional documentation
│   ├── API.md                      # API documentation
│   ├── ARCHITECTURE.md             # Detailed architecture
│   └── DEPLOYMENT.md
│
├── scripts/                         # Utility scripts
│   ├── setup.sh                   # Initial setup
│   └── seed_test_data.py          # Test data seeding
│
└── .github/
    └── workflows/
        └── ci.yml                  # CI/CD pipeline (Ref: Product.md > Section 11)
```

## Key File Responsibilities

### Backend (`/backend/app/`)

**main.py** (Ref: Product.md > Section 9)

- FastAPI application setup
- Route registration
- CORS configuration
- Middleware setup

**api/build.py** (Ref: Product.md > Section 4, lines 663-697)

- Handles `POST /api/build`
- Cache lookup by place_id
- Initiates build process or returns cached session_id

**api/result.py** (Ref: Product.md > Section 4, lines 698-711)

- Handles `GET /api/result/{sessionId}`
- Returns index.html with inlined or linked CSS/JS

**api/progress.py** (Ref: Product.md > Section 4, lines 712-725)

- Handles `GET /sse/progress/{sessionId}`
- Streams build progress as SSE events (Ref: Product.md lines 728-739)

**core/google_fetcher.py** (Ref: Product.md > Section 2, lines 63-85)

- Fetches Place Details, Photos, Reviews from Google Maps API
- Normalizes data into standard payload format
- Handles timeouts and partial failures

**core/cache.py** (Ref: Product.md > Section 2, lines 68 & Section 5, lines 784-790)

- LRU cache by place_id
- Secondary hash validation
- TTL management (14 days default)

**core/artifact_store.py** (Ref: Product.md > Section 9, lines 856-858)

- Stores generated bundles (index.html, styles.css, app.js)
- Path: `/artifacts/{sessionId}/`
- Inlines CSS/JS if under threshold

### AI Agents Service (`/ai/`)

**app/agent_core.py** - Core agent orchestration logic

**app/agents/orchestrator.py** (Ref: Product.md lines 94-193)

- Coordinates all agents in sequence
- Validates input and data richness flags
- Assembles final response with audit trail

**app/agents/designer/** (Ref: Product.md lines 195-248)

- Proposes design source/template for business category
- Outputs style keywords and layout notes

**app/agents/mapper/** (Ref: Product.md lines 399-516)

- Binds real data to layout plan
- Sanitizes text, curates photos, selects reviews
- Generates alt text for images

**app/agents/generator/** (Ref: Product.md lines 518-574)

- Generates index.html, styles.css, app.js
- Embeds data as window.**PLACE_DATA**
- Implements security and performance optimizations

**app/agents/qa/** (Ref: Product.md lines 576-631)

- Validates bundle for a11y, performance, policy
- Returns machine-readable report
- Applies fixes if possible

### Client (`/client/src/`)

**App.tsx** (Ref: Product.md > Section 1, lines 36-43)

- Main split layout (30/70)
- Manages session state
- Coordinates left/right panels

**LeftPanel/** (Ref: Product.md > Section 1, lines 38-41)

- SearchBox: Google Maps Autocomplete integration
- ProgressLog: Real-time SSE event rendering

**RightPanel/** (Ref: Product.md > Section 1, lines 43)

- SiteFrame: iframe loading generated page
- Updates when session becomes READY

**hooks/useSSE.ts**

- Manages SSE connection to backend
- Parses events (Ref: Product.md lines 728-739)
- Handles reconnection logic

## Environment Variables

```bash
# .env.example (Ref: Product.md lines 909-914)
GOOGLE_MAPS_API_KEY=
OPENAI_API_KEY=
ASSET_STORE=./artifacts
INLINE_THRESHOLD_KB=60
CACHE_TTL_DAYS=14
```

## Next Steps

1. Initialize backend Python environment
2. Initialize frontend React + Tailwind
3. Implement Google Fetcher (backend)
4. Implement AI agents
5. Build client UI components
6. End-to-end integration
