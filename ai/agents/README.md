# New Agents Implementation

This directory contains the recreated AI agent logic based on the markdown specifications in `ai/logic_and_docs/`.

## Structure

```
ai/agents/
├── base_agent.py              # Base class with JSON response file handling
├── mapper/
│   ├── mapper_agent.py       # Mapper agent implementation
│   ├── mapper_prompt.py      # Mapper system prompt
│   ├── mapper_schemas.py     # Mapper schemas
│   ├── mapper_response.json  # JSON response file (cleared on each request)
│   └── __init__.py
├── generator/
│   ├── generator_agent.py
│   ├── generator_prompt.py
│   ├── generator_schemas.py
│   ├── generator_response.json
│   └── __init__.py
├── validator/
│   ├── validator_agent.py
│   ├── validator_prompt.py
│   ├── validator_schemas.py
│   ├── validator_response.json
│   └── __init__.py
├── orchestrator/
│   ├── orchestrator_agent.py
│   ├── orchestrator_response.json
│   └── __init__.py
└── main.py                    # FastAPI service entry point (port 8002)
```

## Features

### JSON Response Files

Each agent directory contains a `*_response.json` file that:

- **Writes** the agent's response in JSON format after each call
- **Clears** its contents (sets to `{}`) before each agent request
- Provides a way to inspect agent outputs without modifying code

### Agents

#### 1. **Mapper Agent** (`mapper/`)

Based on `mapper_agent_prompt_with_qa.md`

- Enriches Google Maps business data with web research
- Extracts business summary, logo, images, brand colors
- Runs QA/validator suite with self-healing loop (max 3 retries)
- Outputs normalized JSON with QA report

#### 2. **Generator Agent** (`generator/`)

Based on `landing-page-agent-with-qa.md`

- Generates static landing page (HTML, CSS, JS)
- Implements QA/validation loop for structure, accessibility, performance
- Supports interactivity tiers: basic, enhanced (default), highend
- Includes QA REPORT comment in generated HTML

#### 3. **Validator Agent** (`validator/`)

Based on `validator_agent.md`

- Independent, strict final QA for generated bundle
- Validates structure, HTML semantics, accessibility, CSS quality, JS behavior, performance, business fit
- Returns violations with severity and actionable hints
- Suggests repairs for generator or mapper

#### 4. **Orchestrator Agent** (`orchestrator/`)

Based on `orchestrator.md`

- Coordinates mapper → generator → validator workflow
- Handles retries and targeted repairs
- Creates bundle.zip with QA reports
- Emits progress events via callback

## Usage

### Running the Service

```bash
cd ai/agents
python main.py
```

Service runs on port **8002** (old service runs on 8001).

### API Endpoint

```
POST /build
{
  "session_id": "string",
  "place_data": {...},  // Google Maps business data
  "render_prefs": {},
  "interactivity_tier": "enhanced",
  "max_attempts": 3,
  "asset_budget": 3
}
```

### Response Format

```json
{
  "session_id": "string",
  "success": true,
  "bundle": {
    "index_html": "...",
    "styles_css": "...",
    "app_js": "..."
  },
  "qa_report": {...},
  "mapper_out": {...}
}
```

## Backend Integration

The backend's `agents_client.py` has been updated to support both old and new services:

```python
# Use new agents (default)
client = AgentsServiceClient(use_new_agents=True)  # Port 8002

# Use old agents
client = AgentsServiceClient(use_new_agents=False)  # Port 8001
```

## Differences from Old Implementation

1. **Structure**: New agents based on markdown specs, old based on different architecture
2. **QA Loop**: New agents have built-in QA/validation with self-healing
3. **Response Files**: New agents write JSON responses to files for inspection
4. **Port**: New service runs on 8002 (old on 8001) to allow side-by-side testing
5. **Schemas**: New agents use schemas matching the markdown specifications exactly

## Files Based On

- `mapper/` → `ai/logic_and_docs/mapper_agent_prompt_with_qa.md`
- `generator/` → `ai/logic_and_docs/landing-page-agent-with-qa.md`
- `validator/` → `ai/logic_and_docs/validator_agent.md`
- `orchestrator/` → `ai/logic_and_docs/orchestrator.md`
