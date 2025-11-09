# Accessibility Mobility Context Router - MCP Server

## 🎯 The Idea

**Problem**: People with disabilities face significant challenges when planning trips. Standard navigation apps don't account for:

- Elevator/escalator outages in transit systems that block accessible routes
- Venue accessibility information (wheelchair access, audio guides, tactile paths, etc.)
- Weather conditions that affect mobility (rain, snow, extreme temperatures)
- The need for extra buffer time for accessible travel
- Integration with calendar events to proactively plan trips
- Real-time accessibility barriers that can disrupt travel plans

**Solution**: An MCP (Model Context Protocol) server that fuses multiple data sources to provide people with disabilities a comprehensive, accessibility-first context package for trip planning. Instead of just "how to get there," it answers "how to get there safely and accessibly."

**Key Innovation**: By combining calendar intent (next meeting), real-time transit accessibility data (elevator/escalator outages), venue accessibility tags (OpenStreetMap), weather risks, and route planning, we create a **context package** that gives AI assistants everything they need to provide informed, accessibility-aware guidance.

**Impact**: This transforms trip planning from a multi-step, error-prone process into a single question: "How do I get to my next meeting?" The system automatically considers accessibility barriers, suggests alternatives, and provides evidence-linked recommendations.

### 🌍 Who This Helps

This MCP server benefits people across the accessibility spectrum:

- **Wheelchair Users**: Real-time elevator/escalator outage alerts, venue wheelchair accessibility verification, accessible route planning with buffer time
- **Blind and Visually Impaired**: Detailed route descriptions, alternative route options when primary paths are blocked, weather conditions that affect navigation
- **Mobility Impairments**: Accessible transit options, venue accessibility information, weather-aware planning for conditions that affect mobility
- **People with Chronic Conditions**: Buffer time recommendations, weather risk assessment, alternative routes when primary options are unavailable
- **Elderly Travelers**: Comprehensive accessibility information, clear route alternatives, proactive barrier detection

The system's context package provides structured, evidence-backed information that AI assistants can adapt to each user's specific needs, whether they require wheelchair-accessible routes, detailed verbal descriptions, or weather-sensitive planning.

---

## 🚀 What This MCP Server Does

This MCP server is a specialized tool for AI assistants (like Claude) that helps people with disabilities plan accessible trips. When you ask "How do I get to my next meeting?", the server:

1. **Fetches your next calendar event** (title, time, location) from Google Calendar via ICS feed
2. **Finds multiple route candidates** (transit, walking, driving) using Google Maps Directions API
3. **Checks for elevator/escalator outages** on NYC MTA transit routes that could block accessible paths
4. **Verifies venue accessibility** (wheelchair access, accessibility features) using OpenStreetMap Overpass API
5. **Assesses weather risks** around travel time using OpenWeather API
6. **Calculates optimal departure time** with configurable buffer minutes
7. **Fuses everything into a compact context package** with citations and evidence

The result is a structured JSON package containing:

- **Highlights**: 5 key bullets summarizing route, accessibility alerts, venue access, weather, and timing
- **Alternatives**: Backup route options if the primary route has issues
- **Citations**: Links to source data (maps, transit status, weather forecasts)
- **Metadata**: Event details, origin/destination, sources used

This context package enables AI assistants to provide natural, evidence-backed answers like:

> "Take the Q train from Times Square to 86th St (20 min). Leave by 3:40 PM to arrive by 4:00 PM with a 20-minute buffer. Note: There's an elevator outage at 57th St station—consider the alternative route via 96th St. The Met is wheelchair accessible. Light rain expected—bring an umbrella."

---

## 🛠️ Available Tools

The MCP server exposes two tools and one resource:

### Tools

#### 1. `ask`

**Purpose**: Get a concise, natural-language answer about how to reach your next meeting.

**Parameters**:

- `question` (required, string): Your question, e.g., "How can I reach my next meeting?"
- `origin` (optional, string): Starting address. If omitted, uses `HOME_ADDRESS` from config.
- `buffer_minutes` (optional, integer, default: 20): Extra time buffer in minutes for accessible travel.

**Returns**: A text response with key highlights and recommendations, plus the full context package.

**Example Request**:

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

**Example Response**:

```json
{
  "jsonrpc": "2.0",
  "id": "1",
  "result": {
    "content": [
      {
        "type": "text",
        "text": "- Take Q train from Times Sq-42 St to 86 St (20 min)\n- Elevator outage at 57th St station - consider alternative route\n- The Met is wheelchair accessible\n- Light rain expected around arrival time - bring an umbrella\n- Leave by 3:40 PM to arrive by 4:00 PM (20 min buffer)\n- Alternative: Take 1 train to 96th St, then walk (25 min)"
      },
      {
        "type": "text",
        "text": "{\"context\":{\"query_intent\":\"route_to_event\",\"sources_used\":[\"directions\",\"gtfs_rt_elevators\",\"osm_overpass\",\"openweather\"],\"event\":{\"title\":\"Museum Visit\",\"start_time_iso\":\"2025-11-08T16:00:00-05:00\",\"location_text\":\"The Met, 1000 5th Ave, New York, NY\"},\"origin\":{\"label\":\"Home\",\"address\":\"Times Square, New York, NY\"},\"highlights\":[{\"type\":\"route_summary\",\"text\":\"Take Q train from Times Sq-42 St to 86 St (20 min)\",\"citations\":[\"https://www.google.com/maps/dir/?saddr=Times+Square%2C+New+York%2C+NY&daddr=The+Met%2C+1000+5th+Ave%2C+New+York%2C+NY\"]},{\"type\":\"accessibility_alert\",\"text\":\"Elevator outage at 57th St station\",\"citations\":[\"https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fnyct_ene.json\"]},{\"type\":\"venue_access\",\"text\":\"The Met is wheelchair accessible\",\"citations\":[\"https://overpass-api.de/api/interpreter\"]},{\"type\":\"weather_risk\",\"text\":\"Light rain expected around arrival time\",\"citations\":[\"https://api.openweathermap.org/data/2.5/forecast\"]},{\"type\":\"buffer_recommendation\",\"text\":\"Leave by 3:40 PM to arrive by 4:00 PM (20 min buffer)\",\"citations\":[]}],\"alternatives\":[{\"summary\":\"Alternative: Take 1 train to 96th St, then walk (25 min)\",\"citations\":[\"https://www.google.com/maps/dir/?saddr=Times+Square%2C+New+York%2C+NY&daddr=The+Met%2C+1000+5th+Ave%2C+New+York%2C+NY\"]}],\"raw_citations\":[\"https://www.google.com/maps/dir/?saddr=Times+Square%2C+New+York%2C+NY&daddr=The+Met%2C+1000+5th+Ave%2C+New+York%2C+NY\",\"https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fnyct_ene.json\",\"https://overpass-api.de/api/interpreter\",\"https://api.openweathermap.org/data/2.5/forecast\"],\"token_estimate\":156,\"meta\":{}}}"
      }
    ]
  }
}
```

**Note**: The response contains two text items:

1. **First item**: A concise bullet-point summary answer
2. **Second item**: A JSON string containing the full `context` object with complete `ContextPackage` details, citations, and metadata

When parsed, the second item yields:

```json
{
  "context": {
    "query_intent": "route_to_event",
    "sources_used": ["directions", "gtfs_rt_elevators", "osm_overpass", "openweather"],
    "event": {
      "title": "Museum Visit",
      "start_time_iso": "2025-11-08T16:00:00-05:00",
      "location_text": "The Met, 1000 5th Ave, New York, NY"
    },
    "origin": {
      "label": "Home",
      "address": "Times Square, New York, NY"
    },
    "highlights": [...],
    "alternatives": [...],
    "raw_citations": [...],
    "token_estimate": 156,
    "meta": {}
  }
}
```

#### 2. `build_context`

**Purpose**: Build the full context package with all details, citations, and alternatives.

**Parameters**:

- `origin` (optional, string): Starting address. If omitted, uses `HOME_ADDRESS` from config.
- `buffer_minutes` (optional, integer, default: 20): Extra time buffer in minutes.

**Returns**: A JSON string containing the complete `ContextPackage` object.

**Example Request**:

```json
{
  "jsonrpc": "2.0",
  "id": "2",
  "method": "tools/call",
  "params": {
    "name": "build_context",
    "arguments": {
      "buffer_minutes": 20
    }
  }
}
```

**Example Response**:

```json
{
  "jsonrpc": "2.0",
  "id": "2",
  "result": {
    "content": [
      {
        "type": "text",
        "text": "{\"query_intent\":\"route_to_event\",\"sources_used\":[\"directions\",\"gtfs_rt_elevators\",\"osm_overpass\",\"openweather\"],\"event\":{\"title\":\"Museum Visit\",\"start_time_iso\":\"2025-11-08T16:00:00-05:00\",\"location_text\":\"The Met, 1000 5th Ave, New York, NY\"},\"origin\":{\"label\":\"Home\",\"address\":\"Times Square, New York, NY\"},\"highlights\":[{\"type\":\"route_summary\",\"text\":\"Take Q train from Times Sq-42 St to 86 St (20 min)\",\"citations\":[\"https://www.google.com/maps/dir/?saddr=Times+Square%2C+New+York%2C+NY&daddr=The+Met%2C+1000+5th+Ave%2C+New+York%2C+NY\"]},{\"type\":\"accessibility_alert\",\"text\":\"Elevator outage at 57th St station\",\"citations\":[\"https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fnyct_ene.json\"]},{\"type\":\"venue_access\",\"text\":\"The Met is wheelchair accessible\",\"citations\":[\"https://overpass-api.de/api/interpreter\"]},{\"type\":\"weather_risk\",\"text\":\"Light rain expected around arrival time\",\"citations\":[\"https://api.openweathermap.org/data/2.5/forecast\"]},{\"type\":\"buffer_recommendation\",\"text\":\"Leave by 3:40 PM to arrive by 4:00 PM (20 min buffer)\",\"citations\":[]}],\"alternatives\":[{\"summary\":\"Alternative: Take 1 train to 96th St, then walk (25 min)\",\"citations\":[\"https://www.google.com/maps/dir/?saddr=Times+Square%2C+New+York%2C+NY&daddr=The+Met%2C+1000+5th+Ave%2C+New+York%2C+NY\"]}],\"raw_citations\":[\"https://www.google.com/maps/dir/?saddr=Times+Square%2C+New+York%2C+NY&daddr=The+Met%2C+1000+5th+Ave%2C+New+York%2C+NY\",\"https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fnyct_ene.json\",\"https://overpass-api.de/api/interpreter\",\"https://api.openweathermap.org/data/2.5/forecast\"],\"token_estimate\":156,\"meta\":{}}"
      }
    ]
  }
}
```

**Note**: The response contains a JSON string. When parsed, it yields a `ContextPackage` object with the following structure:

```json
{
  "query_intent": "route_to_event",
  "sources_used": [
    "directions",
    "gtfs_rt_elevators",
    "osm_overpass",
    "openweather"
  ],
  "event": {
    "title": "Museum Visit",
    "start_time_iso": "2025-11-08T16:00:00-05:00",
    "location_text": "The Met, 1000 5th Ave, New York, NY"
  },
  "origin": {
    "label": "Home",
    "address": "Times Square, New York, NY"
  },
  "highlights": [
    {
      "type": "route_summary",
      "text": "Take Q train from Times Sq-42 St to 86 St (20 min)",
      "citations": ["https://www.google.com/maps/dir/..."]
    },
    {
      "type": "accessibility_alert",
      "text": "Elevator outage at 57th St station",
      "citations": ["https://api-endpoint.mta.info/..."]
    },
    {
      "type": "venue_access",
      "text": "The Met is wheelchair accessible",
      "citations": ["https://overpass-api.de/..."]
    },
    {
      "type": "weather_risk",
      "text": "Light rain expected around arrival time",
      "citations": ["https://api.openweathermap.org/..."]
    },
    {
      "type": "buffer_recommendation",
      "text": "Leave by 3:40 PM to arrive by 4:00 PM (20 min buffer)",
      "citations": []
    }
  ],
  "alternatives": [
    {
      "summary": "Alternative: Take 1 train to 96th St, then walk (25 min)",
      "citations": ["https://www.google.com/maps/dir/..."]
    }
  ],
  "raw_citations": [
    "https://www.google.com/maps/dir/...",
    "https://api-endpoint.mta.info/...",
    "https://overpass-api.de/...",
    "https://api.openweathermap.org/..."
  ],
  "token_estimate": 156,
  "meta": {}
}
```

### Resources

#### `context/last`

**Purpose**: Access the last generated context package.

**URI**: `context/last`

**Returns**: The most recent `ContextPackage` as JSON.

**Example Request**:

```json
{
  "jsonrpc": "2.0",
  "id": "3",
  "method": "resources/read",
  "params": {
    "uri": "context/last"
  }
}
```

**Example Response**:

```json
{
  "jsonrpc": "2.0",
  "id": "3",
  "result": {
    "contents": [
      {
        "type": "text",
        "text": "{\n  \"query_intent\": \"route_to_event\",\n  \"sources_used\": [\"directions\", \"gtfs_rt_elevators\", \"osm_overpass\", \"openweather\"],\n  \"event\": {\n    \"title\": \"Museum Visit\",\n    \"start_time_iso\": \"2025-11-08T16:00:00-05:00\",\n    \"location_text\": \"The Met, 1000 5th Ave, New York, NY\"\n  },\n  \"origin\": {\n    \"label\": \"Home\",\n    \"address\": \"Times Square, New York, NY\"\n  },\n  \"highlights\": [\n    {\n      \"type\": \"route_summary\",\n      \"text\": \"Take Q train from Times Sq-42 St to 86 St (20 min)\",\n      \"citations\": [\"https://www.google.com/maps/dir/?saddr=Times+Square%2C+New+York%2C+NY&daddr=The+Met%2C+1000+5th+Ave%2C+New+York%2C+NY\"]\n    },\n    {\n      \"type\": \"accessibility_alert\",\n      \"text\": \"Elevator outage at 57th St station\",\n      \"citations\": [\"https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fnyct_ene.json\"]\n    },\n    {\n      \"type\": \"venue_access\",\n      \"text\": \"The Met is wheelchair accessible\",\n      \"citations\": [\"https://overpass-api.de/api/interpreter\"]\n    },\n    {\n      \"type\": \"weather_risk\",\n      \"text\": \"Light rain expected around arrival time\",\n      \"citations\": [\"https://api.openweathermap.org/data/2.5/forecast\"]\n    },\n    {\n      \"type\": \"buffer_recommendation\",\n      \"text\": \"Leave by 3:40 PM to arrive by 4:00 PM (20 min buffer)\",\n      \"citations\": []\n    }\n  ],\n  \"alternatives\": [\n    {\n      \"summary\": \"Alternative: Take 1 train to 96th St, then walk (25 min)\",\n      \"citations\": [\"https://www.google.com/maps/dir/?saddr=Times+Square%2C+New+York%2C+NY&daddr=The+Met%2C+1000+5th+Ave%2C+New+York%2C+NY\"]\n    }\n  ],\n  \"raw_citations\": [\n    \"https://www.google.com/maps/dir/?saddr=Times+Square%2C+New+York%2C+NY&daddr=The+Met%2C+1000+5th+Ave%2C+New+York%2C+NY\",\n    \"https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fnyct_ene.json\",\n    \"https://overpass-api.de/api/interpreter\",\n    \"https://api.openweathermap.org/data/2.5/forecast\"\n  ],\n  \"token_estimate\": 156,\n  \"meta\": {}\n}"
      }
    ]
  }
}
```

**Note**: The response contains a formatted JSON string of the last generated `ContextPackage`. If no context has been built yet, it returns an empty object `{}`.

---

## 📦 Setup Instructions

### Prerequisites

- Python 3.9 or higher
- Virtual environment tool (recommended: `uv` or `venv`)
- (Optional) API keys for enhanced functionality (see below)

### Step 1: Clone and Navigate

```bash
cd D:\Datathon
```

### Step 2: Create Virtual Environment

**Using `uv` (recommended)**:

```bash
# Install uv if not already installed
# Windows PowerShell:
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# Create virtual environment
uv venv

# Activate (Windows PowerShell)
.\.venv\Scripts\activate
```

**Using `venv`**:

```bash
python -m venv .venv

# Activate (Windows PowerShell)
.\.venv\Scripts\activate
```

### Step 3: Install Dependencies

```bash
# Using uv
uv pip install -r requirements.txt

# Or using pip
pip install -r requirements.txt
```

### Step 4: Configure Environment Variables

Create a `.env` file in the project root:

```env
# Required: Set your home address (origin for trips)
HOME_ADDRESS=Times Square, New York, NY

# Optional: Default city code
DEFAULT_CITY=nyc

# Optional: Google Calendar ICS URL (private read-only feed)
# Get this from: Google Calendar → Settings → Your Calendar → Integrate Calendar → "Secret address in iCal format"
GOOGLE_CALENDAR_ICS_URL=https://calendar.google.com/calendar/ical/your_secret_hash/basic.ics

# Optional: Google Maps API Key (for live directions)
GOOGLE_MAPS_API_KEY=your_google_maps_api_key_here

# Optional: OpenWeather API Key (for weather forecasts)
OPENWEATHER_API_KEY=your_openweather_api_key_here

# Optional: MTA API Key (not required - MTA JSON feeds are public)
MTA_API_KEY=

# Optional: Mock mode (auto-enabled if API keys missing)
MOCK_MODE=false

# Optional: Request timeout in seconds
REQUEST_TIMEOUT_SECONDS=3.0

# Optional: Weather units (metric or imperial)
WEATHER_UNITS=metric
```

**Note**: The server works in **mock mode** if API keys are missing, providing deterministic demo data. This is perfect for testing and demos.

### Step 5: Run the MCP Server

**For stdio mode (used by Claude Desktop)**:

```bash
python -m app.mcp_server
```

The server will wait for JSON-RPC messages on stdin and respond on stdout.

**For REST API mode (optional)**:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

---

## 🔌 Connecting to Claude Desktop

To use this MCP server with Claude Desktop:

1. **Locate Claude Desktop config file**:

   - Windows: `%APPDATA%\Claude\claude_desktop_config.json`
   - Or: `C:\Users\<YourUsername>\AppData\Roaming\Claude\claude_desktop_config.json`

2. **Edit or create the config file**:

```json
{
  "mcpServers": {
    "mobility": {
      "command": "D:\\Datathon\\.venv\\Scripts\\python.exe",
      "args": ["-m", "app.mcp_server"],
      "workingDirectory": "D:\\Datathon",
      "env": {
        "PYTHONPATH": "D:\\Datathon",
        "PYTHONUNBUFFERED": "1",
        "HOME_ADDRESS": "Times Square, New York, NY",
        "DEFAULT_CITY": "nyc",
        "MOCK_MODE": "false"
      }
    }
  }
}
```

**Important**:

- Use forward slashes or escaped backslashes (`\\`) in paths
- Set `PYTHONPATH` to your project root
- Set `PYTHONUNBUFFERED=1` for proper stdio communication
- Add any environment variables you need in the `env` section

3. **Restart Claude Desktop** completely

4. **Test in Claude**: Ask "How do I get to my next meeting?" or "Use the ask tool to help me plan my route"

---

## 🏗️ Architecture

```
app/
├── mcp_server.py          # MCP server entry point (stdio JSON-RPC)
├── main.py                # FastAPI REST API (optional)
├── config.py              # Settings and runtime state
├── models/
│   └── schemas.py         # Pydantic models (ContextPackage, etc.)
└── services/
    ├── calendar.py        # Google Calendar ICS integration
    ├── directions.py      # Google Maps Directions API
    ├── geocode.py         # Address geocoding (Google/Nominatim)
    ├── transit.py         # NYC MTA elevator/escalator outages
    ├── osm.py             # OpenStreetMap venue accessibility
    ├── weather.py         # OpenWeather API integration
    ├── fusion.py          # Route scoring and context fusion
    ├── formatter.py       # Context package building
    └── llm.py             # Gemini integration (optional)
└── utils/
    └── http.py           # Shared HTTP client with timeouts
```

### Data Flow

1. **Input**: User asks "How do I get to my next meeting?" via MCP tool
2. **Calendar**: Fetch next event (title, time, location) from ICS feed
3. **Geocoding**: Resolve location text to lat/lng coordinates
4. **Parallel Data Fetching**:
   - Directions API → Route candidates
   - MTA API → Elevator/escalator outages
   - OSM Overpass → Venue wheelchair tag
   - OpenWeather → Weather forecast
5. **Fusion**: Score routes, identify best option, generate context bullets
6. **Output**: Structured context package with highlights, alternatives, citations

### Key Design Decisions

- **Mock Mode**: Graceful degradation when API keys are missing (deterministic demo data)
- **Timeout Protection**: All HTTP requests have configurable timeouts (default 3s)
- **Citation Links**: Every piece of information includes source links for verification
- **Buffer Time**: Configurable extra time for accessible travel (default 20 minutes)
- **Error Handling**: Server continues processing even if individual data sources fail

---

## 📊 Context Package Structure

The `ContextPackage` returned by tools includes:

```json
{
  "query_intent": "route_to_event",
  "sources_used": [
    "directions",
    "gtfs_rt_elevators",
    "osm_overpass",
    "openweather"
  ],
  "event": {
    "title": "Museum Visit",
    "start_time_iso": "2025-11-08T16:00:00-05:00",
    "location_text": "The Met, 1000 5th Ave, New York, NY"
  },
  "origin": {
    "label": "Home",
    "address": "Times Square, New York, NY"
  },
  "highlights": [
    {
      "type": "route_summary",
      "text": "Take Q train from Times Sq-42 St to 86 St (20 min)",
      "citations": ["https://www.google.com/maps/dir/..."]
    },
    {
      "type": "accessibility_alert",
      "text": "Elevator outage at 57th St station",
      "citations": ["https://api-endpoint.mta.info/..."]
    },
    {
      "type": "venue_access",
      "text": "The Met is wheelchair accessible",
      "citations": ["https://overpass-api.de/..."]
    },
    {
      "type": "weather_risk",
      "text": "Light rain expected around arrival time",
      "citations": ["https://api.openweathermap.org/..."]
    },
    {
      "type": "buffer_recommendation",
      "text": "Leave by 3:40 PM to arrive by 4:00 PM (20 min buffer)",
      "citations": []
    }
  ],
  "alternatives": [
    {
      "summary": "Alternative: Take 1 train to 96th St, then walk (25 min)",
      "citations": ["https://www.google.com/maps/dir/..."]
    }
  ],
  "raw_citations": [
    "https://www.google.com/maps/dir/...",
    "https://api-endpoint.mta.info/..."
  ]
}
```

---

## 🔑 API Keys (Optional)

The server works without API keys (mock mode), but for production use:

### Google Calendar ICS URL

- **How to get**: Google Calendar → Settings → Your Calendar → Integrate Calendar → Copy "Secret address in iCal format"
- **Why**: Fetches your next event automatically

### Google Maps API Key

- **How to get**: [Google Cloud Console](https://console.cloud.google.com/) → Enable "Directions API" → Create API key
- **Why**: Provides live route planning with transit, walking, and driving options

### OpenWeather API Key

- **How to get**: [OpenWeatherMap](https://openweathermap.org/api) → Sign up → Get API key
- **Why**: Weather forecasts around travel time

### MTA API Key

- **Not required**: MTA JSON feeds are public (no key needed)
- **Why**: Real-time elevator/escalator outage data for NYC transit

---

## 🧪 Testing

### Manual Testing (stdio mode)

The MCP server communicates via JSON-RPC over stdio. You can test it manually:

```bash
python -m app.mcp_server
```

Then send JSON-RPC messages (the server will respond).

### REST API Testing (optional)

If you run the FastAPI server:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Test endpoints:

- `GET /health` - Health check
- `POST /config/home` - Set home address
- `POST /build_context` - Build context package
- `GET /context/last` - Get last context package

---

## 🎯 Use Cases

1. **Proactive Trip Planning**: "How do I get to my next meeting?" → Automatic route planning with accessibility checks
2. **Accessibility Alerts**: Real-time notifications about elevator outages that affect your route
3. **Venue Verification**: Check if a destination is wheelchair accessible before you go
4. **Weather-Aware Planning**: Know if weather will affect your travel
5. **Alternative Routes**: Get backup options if your primary route has issues

---

## 📝 License

MIT

---

## 🤝 Contributing

This is a production-ready MCP server for accessibility-aware trip planning. The codebase is structured for easy extension:

- Add new transit systems (currently NYC MTA)
- Integrate additional data sources
- Enhance route scoring algorithms
- Add support for other calendar providers

---

## 🐛 Troubleshooting

### Server won't start

- Check Python version: `python --version` (needs 3.9+)
- Verify dependencies: `pip list`
- Check `PYTHONPATH` is set correctly

### Tools not working in Claude

- Verify MCP server config JSON syntax
- Check Claude Desktop logs: `%APPDATA%\Claude\Logs\`
- Ensure `PYTHONUNBUFFERED=1` is set in config
- Restart Claude Desktop after config changes

### No calendar events found

- Verify `GOOGLE_CALENDAR_ICS_URL` is correct
- Check that your calendar has upcoming events with locations
- Server falls back to mock event if ICS fails

### Mock mode always enabled

- Set `MOCK_MODE=false` in `.env` or config
- Provide at least one API key (Google Maps recommended)

---

## 📚 Additional Resources

- [MCP Protocol Specification](https://modelcontextprotocol.io/)
- [Google Calendar ICS Format](https://en.wikipedia.org/wiki/ICalendar)
- [NYC MTA Real-Time Feeds](https://api.mta.info/)
- [OpenStreetMap Overpass API](https://wiki.openstreetmap.org/wiki/Overpass_API)

---

## 🔮 Future Improvements

This MVP provides a solid foundation for accessibility-aware trip planning. Potential future enhancements include:

- **Expanded Transit Coverage**: Support for additional transit systems beyond NYC MTA (e.g., other major cities' transit APIs)
- **Enhanced Accessibility Data**: Integration with crowdsourced accessibility platforms and venue-specific accessibility databases
- **Personalization**: User preference profiles for accessibility needs, preferred transit modes, and buffer time preferences
- **Advanced Route Intelligence**: Machine learning-based route scoring and predictive outage detection using historical patterns
- **Multi-Calendar Support**: Integration with additional calendar providers (Outlook, Apple Calendar, etc.)

These improvements would enhance the MCP server's capabilities while building on the current accessibility-first foundation.
