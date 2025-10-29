# API Documentation

Ref: Product.md > Section 4

## Endpoints

### POST /api/build

Start or replay a build for a `place_id`.

**Request:**

```json
{
  "place_id": "ChIJN1t_tDeuEmsRUsoyG83frY4",
  "render_prefs": {
    "language": "en",
    "direction": "ltr",
    "allow_external_cdns": true,
    "max_reviews": 6
  }
}
```

**Response:**

```json
{
  "session_id": "abc123",
  "cached": false
}
```

### GET /api/result/{sessionId}

Get the generated landing page bundle.

**Response:**
HTML document with embedded CSS/JS

### GET /sse/progress/{sessionId}

Stream build progress as Server-Sent Events.

**Event Format:**

```
data: {
  "ts": "2025-10-27T10:00:00Z",
  "session_id": "abc123",
  "phase": "GENERATING",
  "step": "Bundle generation",
  "detail": "Generating CSS",
  "progress": 0.75
}
```

## Error Responses

```json
{
  "error_id": "uuid",
  "code": "INVALID_PLACE_ID",
  "message": "human-friendly message",
  "hint": "possible next action",
  "retryable": false,
  "session_id": "abc123"
}
```

## HTTP Status Codes

- 200: Success
- 202: Build accepted
- 400: Invalid input
- 404: Not found
- 429: Rate limited
- 500: Internal error

