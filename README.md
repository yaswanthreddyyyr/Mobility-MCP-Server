# Accessibility Mobility Context Router (MVP Backend)

FastAPI backend that answers “How do I get there?” for wheelchair users by fusing calendar intent with accessible transit/venue context, returning a compact, evidence‑linked context package for an AI assistant.

## Features (Day‑1 MVP)

- Build a 5‑bullet “context package” with citations
  - Directions candidates (transit/walk/drive) with arrival feasibility
  - Elevator/outage risks on the path (city adapter; NYC mocked or live)
  - Venue wheelchair tag from OpenStreetMap (Overpass API)
  - Weather risks around travel time (OpenWeather, or mock)
  - “Leave by” time with configurable buffer
- Mock mode when API keys are absent (deterministic demo)

## Endpoints

- POST `/build_context` — Orchestrates data fetching and fusion
- POST `/config/home` — Set home address (origin)
- GET `/context/last` — Returns last emitted context package
- GET `/health` — Liveness probe

## MCP server (optional wrapper)

- Tools:
  - `ask(question, origin?, buffer_minutes=20)` → concise answer (synthesized from bullets)
  - `build_context(origin?, buffer_minutes=20)` → returns context package JSON
- Resource:
  - `context/last` → last context package JSON

Run (stdio MCP):

```bash
python -m app.mcp_server
```

The MCP server reuses the same orchestrator logic and does not require the REST API to be running.

## MCP quickstart and env keys

### Quickstart

- Start server (stdio):

```bash
python -m app.mcp_server
```

- Tools
  - `ask(question, origin?, buffer_minutes=20)` → concise accessibility-first answer (text)
  - `build_context(origin?, buffer_minutes=20)` → context package JSON (string)
- Resource
  - `context/last` → last context package JSON

### Example MCP tool calls (JSON-RPC over stdio)

- Call `ask`

```json
{
  "jsonrpc": "2.0",
  "id": "1",
  "method": "tools/call",
  "params": {
    "name": "ask",
    "arguments": {
      "question": "How can I reach my next meeting?",
      "buffer_minutes": 20
    }
  }
}
```

- Call `build_context`

```json
{
  "jsonrpc": "2.0",
  "id": "2",
  "method": "tools/call",
  "params": { "name": "build_context", "arguments": { "buffer_minutes": 20 } }
}
```

- Read resource `context/last`

```json
{
  "jsonrpc": "2.0",
  "id": "3",
  "method": "resources/read",
  "params": { "uri": "context/last" }
}
```

### Environment keys

| Key                     | Required | Purpose                                                    |
| ----------------------- | -------- | ---------------------------------------------------------- |
| GOOGLE_CALENDAR_ICS_URL | No       | Real “next event” (title/time/location) via private ICS    |
| GOOGLE_MAPS_API_KEY     | No       | Live Directions + Geocoding (fallbacks exist)              |
| OPENWEATHER_API_KEY     | No       | Weather risk near travel time (fallback exists)            |
| MTA_API_KEY             | No       | Not required (MTA JSON is public); leave empty             |
| GEMINI_API_KEY          | No       | If set, `/ask` uses Gemini for the natural-language answer |
| HOME_ADDRESS            | No       | Default origin (can be set via REST `/config/home`)        |
| DEFAULT_CITY            | No       | Default `nyc`                                              |
| MOCK_MODE               | No       | `true/false` (auto-true if keys missing)                   |
| REQUEST_TIMEOUT_SECONDS | No       | HTTP timeouts (default 3.0)                                |
| WEATHER_UNITS           | No       | `metric` or `imperial`                                     |
| OSM_OVERPASS_URL        | No       | Overpass endpoint (defaults provided)                      |

## Quickstart

### 1) Python env

```bash
python -m venv .venv
.\.venv\Scripts\activate  # Windows PowerShell
pip install -r requirements.txt
```

### 2) Env config

Copy `.env.example` to `.env` and fill keys if available. Without keys, server runs in MOCK mode.

Required (optional for mock):

- `GOOGLE_MAPS_API_KEY` — Directions + Geocoding (or Nominatim fallback)
- `OPENWEATHER_API_KEY` — Weather (mock fallback)
- `MTA_API_KEY` — NYC elevator status (mock fallback)

Optional:

- `HOME_ADDRESS` — Default origin (e.g., "123 Main St, New York, NY")
- `DEFAULT_CITY` — Default city code, default `nyc`
- `MOCK_MODE` — `true`/`false` (auto‑true if keys missing)

### Google Calendar (no OAuth, ICS feed)

- `GOOGLE_CALENDAR_ICS_URL` — Private iCal URL for your calendar (read‑only). Find it in Google Calendar → Settings → your calendar → Integrate calendar → “Secret address in iCal format”. Paste that URL here.

Example:

```
GOOGLE_CALENDAR_ICS_URL=https://calendar.google.com/calendar/ical/your_secret_hash/basic.ics
```

### 3) Run

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 4) Example request

```bash
curl -X POST http://localhost:8000/build_context ^
  -H "Content-Type: application/json" ^
  -d "{ \"use_next_event\": false, \"destination\": \"The Met, 1000 5th Ave, New York, NY\", \"arrival_time_iso\": \"2025-11-08T16:00:00-05:00\", \"origin\": \"350 5th Ave, New York, NY\", \"buffer_minutes\": 20 }"
```

## Architecture

- `app/main.py` — FastAPI app and routes
- `app/config.py` — Env settings
- `app/models/schemas.py` — Pydantic models
- `app/services/` — Integrations and fusion
  - `calendar.py` (stub for future Calendar integration)
  - `geocode.py` (Google or Nominatim fallback)
  - `directions.py` (Google Directions, mock fallback)
  - `transit.py` (NYC MTA elevator status, mock fallback)
  - `osm.py` (Overpass wheelchair tags)
  - `weather.py` (OpenWeather, mock fallback)
  - `fusion.py` (scoring + bullet generation)
  - `formatter.py` (context package building)
- `app/utils/http.py` — Shared HTTP client helpers

## Notes

- This MVP focuses on NYC and mockable flows for deterministic demos.
- Calendar integration is stubbed; pass destination/time directly for now.
- All external calls have timeouts and degrade gracefully to mock data.

## Example prompts

- “How do I get to my next event?”
- “Plan an accessible route to The Met by 4 pm with a 20‑minute buffer.”
- “Is there an elevator outage that affects my trip?”

## License

MIT
