# Google Maps → AI Landing: Concept Brief + Early PRD

\_Last updated: 2025-10-27 10:50:10

This single document is designed for an AI IDE to implement the complete system. It includes the original JSON contracts you provided (verbatim), plus tightened specifications, schemas, state machines, acceptance tests, and security/perf constraints.

---

## 0. Intent

Build a web app where a user searches for a business via Google Maps. After selection, the backend builds an informational, single-page landing (no CTAs) inside a right-hand iframe, while the left panel shows progress via SSE.

The backend uses an Orchestrator with domain-specific agents (Selector, Architect, Mapper, Generator, QA) to convert Google data → safe, static bundle (index.html, styles.css, app.js). The page is self-contained (no runtime network calls unless explicitly allowed).

---

## 1. Core Narrative (Verbatim From User, Preserved)

### Project Overview

I want to build a web application that allows users to search for businesses using Google Maps.
When a user selects a business, the system will automatically generate and display a dynamic landing page for that business within a designated section of the site.

Using data retrieved from the Google Maps API, the system will build a unique, data-driven page tailored to each business.

The site’s logic will be inspired by **Base 44 – AI-powered application generation**.
Behind the scenes, a fixed system prompt will guide the backend to construct the landing page based on the data collected from the Google Maps API.

### Tech Stack

1. **Server:** Python
2. **Client:** React

### Page Layout

The layout will mirror the **Base 44 editor** interface — a horizontally split, full-height page:

- **Section A (Left Panel – 30% width):** Handles the business search and shows AI generation progress.

  - **Top Area (30% height):** A static header containing an autocomplete search box connected to the Google Maps Places Autocomplete API.
  - **Bottom Area (70% height):** Displays a real-time text log showing the creation steps after a user selects a business — including data fetching, color palette generation, template selection, and live build progress.

- **Section B (Right Panel – 70% width):** Displays the dynamically generated landing page for the selected business. iframe connected to the backend.

### System Architecture (as provided)

```
Client repo (React tailwind light  css ganaral site theme (not in the iframe))
│
├─ Left Panel
│   • Google Maps Search (Autocomplete)
│   • Live progress log (via SSE)
│
├─ Right Panel
│   • Site Pane (iframe)
│
└─ API Calls → FastAPI Backend
      ├─ /api/build
      ├─ /api/result/{sessionId}
      └─ /sse/progress/{sessionId}

Backend repo (FastAPI)
│
├─ Google Fetcher → retrieves business data.
    Once the user selects a business, func recives place_id from client.

    if cached by place id the fire "Dynamic Page Renderer" with cached site.
    else
    the system retrieves the following data from Google:

   * **Place Details**
   * **Place Photos**
   * **Place Reviews**

   The data should be collected using the most efficient methods described in the Google Maps Platform documentation:

   * Place Details
   * Place Photos
   * Place Reviews
   * Main API Reference

├─ Agent Launcher → Sends data to the Backend OpenAI’s Agents SDK Orchestrator.
├─ Dynamic Page Renderer → The function that is in charge of rendering the iframe in the clinet and to update the Live progress log via sse.
├─ Cache Layer -> in charge of checking and fetching cached pages.
```

---

Agents repo: Prompts and Contracts - Open AI agents using https://github.com/openai/openai-python


build each agent with the provided prompt and expected input and output

### Orchestrator

**Prompt (system message):**

```
You are the Orchestrator. You receive normalized place data and render preferences.
Your job: validate inputs, derive business intent (data-display only), coordinate the other agents,
and assemble a final single-page bundle (index.html, styles.css, app.js) with zero runtime API calls.

Steps:
1) Validate and normalize the input payload. Infer data richness flags (has_photos, has_reviews, has_hours, has_site).
2) Ask Design-Source Selector to propose a reference design source suitable for the category and tone.
3) Ask Layout Architect to produce an explicit section/Component plan based on data richness and the chosen source.
4) Ask Content Mapper to bind real data to the plan, including safe text, curated photos, and selected reviews.
5) Ask Bundle Generator to produce index.html, styles.css, app.js with embedded data (window.__PLACE_DATA__).
6) Ask QA & Packager to validate a11y, size, no external calls (unless allow_external_cdns), then return the final bundle.

Constraints:
- Single page only.
- Strict escaping for any user text.
- Include alt text for every image.
- If a section lacks data, hide it gracefully.
- Preserve attributions for photos (render next to the image or in a credits block).
- Provide a minimal light contrast-safe theme derived from render_prefs.brand_colors or a neutral palette.
- No CTAs. The page is informational only.

Return:
- A final object with audit trail + final bundle.
```

**Response schema (Orchestrator → caller):**

```json
{
  "orchestrator_version": "1.0",
  "input_validation": {
    "valid": true,
    "warnings": ["string"],
    "errors": []
  },
  "context": {
    "business_name": "string",
    "category": "string",
    "data_richness": {
      "has_photos": true,
      "has_reviews": true,
      "has_hours": true,
      "has_site": true
    }
  },
  "design_source": {
    "name": "string",
    "url": "string",
    "style_keywords": ["string"],
    "license_note": "string"
  },
  "layout_plan": {
    "sections": [
      {
        "id": "hero",
        "title": "string",
        "components": [
          { "type": "headline", "props": { "level": "h1" } },
          { "type": "gallery", "props": { "max": 6, "lazy": true } }
        ]
      }
    ],
    "empty_state_rules": ["string"],
    "a11y_notes": ["string"]
  },
  "content_map": {
    "sections": [
      {
        "id": "hero",
        "resolved_content": {
          "headline": "Domino's Pizza",
          "subheadline": "Restaurant • Pizza",
          "gallery": [{ "url": "...", "alt": "...", "attribution_html": "..." }]
        }
      }
    ],
    "reviews_policy": {
      "max": 6,
      "language_filter": ["en"],
      "moderation": ["no_profanity", "min_length=20"]
    }
  },
  "bundle": {
    "index_html": "<!doctype html>...",
    "styles_css": "/* css */",
    "app_js": "// js"
  },
  "qa_report": {
    "a11y": { "passed": true, "issues": [] },
    "performance": { "total_kb": 88, "external_requests": 0 },
    "security": { "unsafe_html_found": false },
    "conformance": { "single_page": true, "no_runtime_calls": true }
  }
}
```

### Design-Source Selector

**Prompt (system message):**

```
You select a reference design source (template/theme) for a single informational landing page.
Input: business_name, category, render_prefs, data_richness.
Output: 1 design source that best fits tone and category, with rationale and style keywords.

Rules:
- Must suit a data-display page (no CTA emphasis).
- Favor clean, content-first layouts (good typography, card/grid sections).
- Provide license/usage note.
- Assume the final page will be custom-built; your source is inspiration and structure guidance.
- No external dependency is required from the chosen source; it’s a reference.
```

**Input from Orchestrator → Selector:**

```json
{
  "business_name": "string",
  "category": "string",
  "render_prefs": {
    "language": "en",
    "direction": "ltr",
    "brand_colors": { "primary": "#0f766e", "accent": "#22d3ee" },
    "font_stack": "system-ui",
    "allow_external_cdns": false
  },
  "data_richness": {
    "has_photos": true,
    "has_reviews": true,
    "has_hours": true,
    "has_site": true
  }
}
```

**Response schema (Selector → Orchestrator):**

```json
{
  "name": "UIdeck - Solid Content",
  "url": "https://example.com/template",
  "style_keywords": ["content-first", "grid", "cards", "accessible", "neutral"],
  "layout_notes": [
    "Hero with name + category",
    "Responsive grid for photos",
    "Readable reviews section with avatars"
  ],
  "license_note": "Free for personal/commercial with attribution (verify)"
}
```

### Layout Architect

**Prompt (system message):**

```
Design a section/component blueprint for a single-page informational landing page.
Inputs: business_name, category, design_source, data_richness, render_prefs.

Output: ordered sections with explicit component types, props, and visibility rules based on data availability.

Constraints:
- Single page.
- Avoid CTA-oriented components.
- Include empty-state and fallback rules.
- Include accessibility requirements (headings, alt text, focus styles).
```

**Input from Orchestrator → Architect:**

```json
{
  "business_name": "string",
  "category": "string",
  "design_source": {
    "name": "string",
    "url": "string",
    "style_keywords": ["string"]
  },
  "data_richness": {
    "has_photos": true,
    "has_reviews": true,
    "has_hours": true,
    "has_site": true
  },
  "render_prefs": {
    "language": "en",
    "direction": "ltr"
  }
}
```

**Response schema (Architect → Orchestrator):**

```json
{
  "sections": [
    {
      "id": "hero",
      "title": "Top",
      "components": [
        {
          "type": "headline",
          "props": { "level": "h1", "bind": "place.name" }
        },
        {
          "type": "subheadline",
          "props": { "text_from": ["category", "place.types"] }
        },
        {
          "type": "metaRow",
          "props": {
            "fields": [
              "rating",
              "user_ratings_total",
              "price_level",
              "formatted_address"
            ]
          }
        }
      ],
      "visible_if": "true"
    },
    {
      "id": "gallery",
      "title": "Photos",
      "components": [
        {
          "type": "imageGrid",
          "props": { "bind": "photos", "max": 8, "lazy": true }
        }
      ],
      "visible_if": "has_photos"
    },
    {
      "id": "about",
      "title": "About",
      "components": [
        {
          "type": "keyValueList",
          "props": {
            "items": [
              { "label": "Address", "bind": "place.formatted_address" },
              { "label": "Website", "bind": "place.website" },
              { "label": "Phone", "bind": "place.formatted_phone_number" },
              { "label": "Hours", "bind": "place.opening_hours.weekday_text" }
            ],
            "linkify": ["place.website"]
          }
        }
      ],
      "visible_if": "true"
    },
    {
      "id": "reviews",
      "title": "Reviews",
      "components": [
        {
          "type": "reviewList",
          "props": { "bind": "reviews", "max": 6, "avatar": true }
        }
      ],
      "visible_if": "has_reviews"
    },
    {
      "id": "credits",
      "title": "Attributions",
      "components": [
        {
          "type": "attributionList",
          "props": { "bind": "photos.attributions" }
        }
      ],
      "visible_if": "has_photos"
    },
    {
      "id": "map",
      "title": "Location",
      "components": [
        {
          "type": "staticMapPlaceholder",
          "props": { "bind": "place.geometry" }
        }
      ],
      "visible_if": "true"
    }
  ],
  "empty_state_rules": [
    "Hide section if data_richness flag is false",
    "If no photos: render a 3-col color block with business initials"
  ],
  "a11y_notes": [
    "Single H1 in hero",
    "Alt text for every image",
    "Sufficient color contrast for text/background",
    "Keyboard-focus outlines on interactive items"
  ]
}
```

### Content Mapper

**Prompt (system message):**

```
Bind real data into the layout plan. Sanitize and format for safe HTML output.
Select up to render_prefs.max_reviews reviews, filter by language, drop profanity, trim long texts with “Read more” expansion handled by app.js (no external code).

Also: derive alt text for photos. Preserve attribution HTML safely in a dedicated credits section (rendered as sanitized allowed tags: <a>, <span>).
```

**Input from Orchestrator → Mapper:**

```json
{
  "layout_plan": {
    "sections": [
      /* from Architect */
    ]
  },
  "place_payload": {
    /* full normalized payload from backend as above */
  }
}
```

**Response schema (Mapper → Orchestrator):**

```json
{
  "sections": [
    {
      "id": "hero",
      "resolved_content": {
        "headline": "Domino's Pizza",
        "subheadline": "Restaurant • Pizza",
        "meta": {
          "rating": "4.2",
          "user_ratings_total": "127",
          "price_level": "$$",
          "formatted_address": "123 King St, City"
        }
      }
    },
    {
      "id": "gallery",
      "resolved_content": {
        "images": [
          {
            "url": "https://.../1.jpg",
            "alt": "Front of Domino's Pizza",
            "attribution_html": "<a href='...'>User A</a>"
          },
          {
            "url": "https://.../2.jpg",
            "alt": "Interior seating",
            "attribution_html": "<a href='...'>User B</a>"
          }
        ]
      }
    },
    {
      "id": "about",
      "resolved_content": {
        "key_values": [
          { "label": "Address", "value": "123 King St" },
          { "label": "Website", "value": "https://dominos.com" },
          { "label": "Phone", "value": "+1 555-1234" },
          { "label": "Hours", "value": ["Mon: 10–22", "Tue: 10–22"] }
        ]
      }
    },
    {
      "id": "reviews",
      "resolved_content": {
        "items": [
          {
            "author": "Jane D.",
            "avatar": "https://.../avatar.jpg",
            "rating": 5,
            "relative_time": "2 weeks ago",
            "text": "Great pie.",
            "language": "en"
          }
        ]
      },
      "policy": {
        "max": 6,
        "language_filter": ["en"],
        "moderation": ["no_profanity", "min_length=20"]
      }
    },
    {
      "id": "credits",
      "resolved_content": {
        "attributions": [
          { "html": "<a href='...'>User A</a>" },
          { "html": "<a href='...'>User B</a>" }
        ]
      }
    },
    {
      "id": "map",
      "resolved_content": {
        "geometry": { "lat": 32.07, "lng": 34.78 },
        "alt": "Map location for Domino's Pizza"
      }
    }
  ],
  "sanitization": {
    "html_escaped_fields": [
      "reviews.items[].text",
      "credits.attributions[].html"
    ],
    "policy": "Escape all text; allow <a> with href + rel=noopener noreferrer; strip other tags"
  }
}
```

### Bundle Generator

**Prompt (system message):**

```
Generate a single-page bundle: index.html, styles.css, app.js.
Embed the mapped content as a JSON blob on window.__PLACE_DATA__.
No external network calls at runtime. No external libraries unless allow_external_cdns=true.

Requirements:
- index.html: semantic structure matching the layout plan; include <meta> for viewport and language dir; include credits section.
- styles.css: responsive grid, readable typography, accessible color contrast. If brand_colors exist, use them; if not, neutral palette.
- app.js: hydrate content, lazy-load images, “Read more” toggles for long review text, zero third-party dependencies.
- Security: escape text nodes; for allowed attributions, safely set via a sanitizer that only allows <a> with href + rel attrs.
- Performance: defer JS; preload hero image if present; compress whitespace in output if possible.

Return the 3 files as strings. Do not truncate.
```

**Input from Orchestrator → Generator:**

```json
{
  "business_name": "string",
  "render_prefs": {
    "language": "en",
    "direction": "ltr",
    "brand_colors": { "primary": "#0f766e", "accent": "#22d3ee" },
    "font_stack": "system-ui",
    "allow_external_cdns": false
  },
  "layout_plan": {
    "sections": [
      /* from Architect */
    ]
  },
  "content_map": {
    "sections": [
      /* from Mapper */
    ]
  }
}
```

**Response schema (Generator → Orchestrator):**

```json
{
  "index_html": "<!doctype html><html lang='en' dir='ltr'>...</html>",
  "styles_css": "/* responsive, accessible styles */",
  "app_js": "window.__PLACE_DATA__=...;(()=>{ /* hydrate DOM safely */ })();",
  "meta": {
    "estimated_total_kb": 85,
    "external_requests": 0
  }
}
```

### QA & Packager

**Prompt (system message):**

```
Validate the bundle for a11y, performance, and policy conformance.
- A11y checklist: single H1, labeled landmarks, alt text on images, focus-visible styles, color contrast.
- Performance: total size under 250 KB uncompressed; inline data OK; lazy-load images.
- Policy: no external requests unless allow_external_cdns=true; no forms/CTAs; single page only.

If issues are fixable via light edits (whitespace trim, minor style tweaks), do it and document.
Return final bundle + machine-readable report.
```

**Input from Orchestrator → QA:**

```json
{
  "bundle": {
    "index_html": "string",
    "styles_css": "string",
    "app_js": "string"
  },
  "render_prefs": { "allow_external_cdns": false }
}
```

**Response schema (QA → Orchestrator):**

```json
{
  "report": {
    "a11y": {
      "passed": true,
      "issues": []
    },
    "performance": {
      "total_kb": 82,
      "largest_asset_kb": 40,
      "external_requests": 0,
      "lazy_images": true
    },
    "policy": {
      "single_page": true,
      "no_cta": true,
      "no_runtime_calls": true
    },
    "fixes_applied": ["trimmed whitespace in styles.css"]
  },
  "final_bundle": {
    "index_html": "<!doctype html>...",
    "styles_css": "/* ... */",
    "app_js": "// ..."
  }
}
```

---

## 3. End-to-End Flow

1. Client sends `/api/build` with `{ place_id }`.
2. Backend checks cache by `place_id`. If hit → respond with cached `session_id` and stream build log replay over `/sse/progress/{session_id}`; iframe loads `/api/result/{session_id}`.
3. If miss → Google Fetcher gathers details, photos, reviews; normalize payload.
4. Agent Orchestrator executes Selector → Architect → Mapper → Generator → QA.
5. Cache final bundle by `place_id` (and content hash of normalized payload). Write immutable artifact.
6. SSE streams progress steps + timings. Iframe points to `/api/result/{session_id}` which returns `index.html` with links to `/assets/{session_id}/styles.css` and `/assets/{session_id}/app.js` or inlined CSS/JS (configurable).

### State machine

```
IDLE → FETCHING → ORCHESTRATING → GENERATING → QA → READY
                       ↘───────────────ERROR────────────↗
```

---

## 4. API: OpenAPI Sketch

```yaml
openapi: 3.0.3
info:
  title: Maps-to-Landing Builder
  version: 0.1.0
servers:
  - url: /
paths:
  /api/build:
    post:
      summary: Start/Replay a build for a place_id
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              required: [place_id]
              properties:
                place_id: { type: string }
                render_prefs:
                  type: object
                  properties:
                    language: { type: string, default: en }
                    direction: { type: string, enum: [ltr, rtl], default: ltr }
                    brand_colors:
                      type: object
                      properties:
                        primary: { type: string }
                        accent: { type: string }
                    font_stack: { type: string, default: system-ui }
                    allow_external_cdns: { type: boolean, default: false }
                    max_reviews: { type: integer, default: 6 }
      responses:
        "202":
          description: Build accepted
          content:
            application/json:
              schema:
                type: object
                properties:
                  session_id: { type: string }
                  cached: { type: boolean }
  /api/result/{sessionId}:
    get:
      summary: Get final index.html or bundle descriptor
      parameters:
        - in: path
          name: sessionId
          required: true
          schema: { type: string }
      responses:
        "200":
          description: HTML
          content:
            text/html:
              schema: { type: string }
  /sse/progress/{sessionId}:
    get:
      summary: Server-sent events for build progress
      parameters:
        - in: path
          name: sessionId
          required: true
          schema: { type: string }
      responses:
        "200":
          description: text/event-stream
          content:
            text/event-stream:
              schema: { type: string }
```

**Event model (SSE data field / JSON):**

```json
{
  "ts": "2025-10-27T10:00:00Z",
  "session_id": "abc123",
  "phase": "FETCHING|ORCHESTRATING|GENERATING|QA|READY|ERROR",
  "step": "Google.PlaceDetails",
  "detail": "Fetched 6 photos, 123 reviews",
  "progress": 0.42
}
```

---

## 5. Data Contracts (Backend)

### Normalized Place Payload

```json
{
  "place": {
    "place_id": "string",
    "name": "string",
    "types": ["restaurant", "pizza"],
    "formatted_address": "string",
    "geometry": { "lat": 0, "lng": 0 },
    "website": "https://...",
    "formatted_phone_number": "string",
    "opening_hours": { "weekday_text": ["Mon: 10–22"] },
    "rating": 4.2,
    "user_ratings_total": 127,
    "price_level": 2
  },
  "photos": [
    {
      "url": "https://...",
      "width": 800,
      "height": 600,
      "attribution_html": "<a href='...'>User A</a>",
      "alt": "derived alt"
    }
  ],
  "reviews": [
    {
      "author": "string",
      "avatar": "https://...",
      "rating": 5,
      "relative_time": "2 weeks ago",
      "text": "Great pie.",
      "language": "en"
    }
  ]
}
```

### Cache key

```
primary: place_id
secondary hash: sha256(normalized_payload without volatile fields)
ttl: 14 days (configurable); eviction LRU + size cap
```

---

## 6. Security, Compliance, Legal

- **No PII beyond what Google Places returns intentionally.** Do not attempt to scrape sites.
- **Google TOS:** use Places Web Service/JS per license; preserve required attributions.
- **Sanitization:** all text escaped; only allow `<a>` in attribution with `rel="noopener noreferrer nofollow"` and `target="_blank"` optional.
- **Headers:** set `Content-Security-Policy` to disallow external networks unless `allow_external_cdns=true`.
- **Secrets:** store API keys in server-side env (12-factor); never expose to client or bundle.
- **Logging:** avoid logging raw review text; log counts and hashes only.

---

## 7. Performance SLOs

- First usable render in iframe ≤ 2.0s on repeat (cache hit), ≤ 5.0s on cold build.
- Bundle size ≤ 250 KB uncompressed; images lazy-loaded.
- SSE heartbeat every 10s; retry with backoff on disconnects.

---

## 8. Error Model

```json
{
  "error_id": "uuid",
  "code": "INVALID_PLACE_ID|GOOGLE_RATE_LIMIT|GENERATION_FAILED|BUNDLE_INVALID|NOT_FOUND",
  "message": "human-friendly",
  "hint": "possible next action",
  "retryable": true,
  "session_id": "abc123"
}
```

HTTP mappings:

- 400 invalid input
- 404 not found
- 409 already building
- 429 rate limited
- 500 internal error

---

## 9. Implementation Notes (Concrete)

### Client (React + Tailwind)

- Left panel: Google Places Autocomplete, then a scrollable log area that appends SSE events.
- Right panel: `<iframe src="/api/result/{sessionId}">` swaps on READY event.
- light theme outside iframe; bundle inside uses its own minimal theme.

### FastAPI

- `POST /api/build`: idempotent on place_id; returns `{session_id, cached}` (202).
- `GET /api/result/{sessionId}`: returns index.html (200) or 404 while not READY (or 425 Too Early configurable).
- `GET /sse/progress/{sessionId}`: stream progress.

### Google Fetch

- Use server-side Places Details / Photos / Reviews. Respect quotas; set timeouts and partial-fail fallback.
- Enrich with alt text heuristics: "{{name}} - {{category or type}}" or derived from photo metadata.

### Artifact Store

- Filesystem or object storage: `/artifacts/{sessionId}/{index.html,styles.css,app.js}`.
- Index can inline CSS/JS for minimal latency for small bundles (config: INLINE_THRESHOLD_KB).

---

## 10. Acceptance Criteria

- Selecting a place with photos and reviews yields a page with hero, gallery, about, reviews, credits, map sections; sections without data are hidden.
- No external requests are made by the generated page when `allow_external_cdns=false`.
- All images have alt and optional attribution near image or in credits.
- SSE progress shows at least 6 distinct steps spanning fetch → orchestration → QA → ready.

---

## 11. Test Strategy

- Unit tests for sanitization, review filtering, alt-text generation.
- Contract tests for agent I/O JSON shapes (fixtures of the schemas above).
- E2E: mock Google API; verify bundle + size; axe-core accessibility scan on final HTML.
- Load: 50 concurrent builds, p95 ≤ 6s cold; 500 cache hits/min with p95 ≤ 300ms.

---

## 12. Observability

- Trace IDs per session; log phase timings; metrics: build_duration_ms, cache_hit_rate, bundle_kb, external_requests.
- Redact or hash user content fields in logs.

---

## 13. Roadmap (Current vs Future Behavior)

- **Current**: All pages follow the same minimal informational layout; content varies by data richness.
- **Future**: The agents will pick and adapt different design inspirations per category and dynamically vary layout blocks and styles for truly unique appearances per business.

---

## 14. Developer Quickstart

```bash
# server
uv venv && source .venv/bin/activate  # or python -m venv .venv
pip install fastapi uvicorn httpx jinja2 orjson pydantic[dotenv]
uvicorn app.main:app --reload

# client (separate)
npm create vite@latest maps-landing -- --template react-ts
cd maps-landing && npm i && npm run dev
```

Environment:

```
GOOGLE_MAPS_API_KEY=...
OPENAI_API_KEY=...
ASSET_STORE=./artifacts
INLINE_THRESHOLD_KB=60
```

---

## 15. Non-Goals

- No multi-page sites.
- No booking/ordering CTAs.
- No runtime calls from the bundle except optional CDN fonts if explicitly allowed.

---

**End of PRD.**
