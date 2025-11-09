# Postman Testing Guide for Mobility Context API

## Step 1: Start the FastAPI Server

1. Open PowerShell/Terminal in `D:\Datathon`
2. Activate your virtual environment:
   ```powershell
   .\.venv\Scripts\activate
   ```
3. Start the server:
   ```powershell
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```
4. You should see: `Uvicorn running on http://0.0.0.0:8000`

## Step 2: Set Up Postman

1. Open Postman
2. Create a new Collection: "Mobility Context API"
3. Set base URL variable:
   - Go to Collection → Variables
   - Add variable: `base_url` = `http://localhost:8000`

## Step 3: Test Endpoints

### 3.1 Health Check (GET)

**Request:**
- Method: `GET`
- URL: `{{base_url}}/health`
- Headers: None needed

**Expected Response:**
```json
{
  "status": "ok",
  "mock_mode": true
}
```

---

### 3.2 Set Home Address (POST)

**Request:**
- Method: `POST`
- URL: `{{base_url}}/config/home`
- Headers:
  - `Content-Type: application/json`
- Body (raw JSON):
```json
{
  "address": "Times Square, New York, NY"
}
```

**Expected Response:**
```json
{
  "ok": true,
  "home_address": "Times Square, New York, NY"
}
```

---

### 3.3 Build Context (POST) - Using Next Event

**Request:**
- Method: `POST`
- URL: `{{base_url}}/build_context`
- Headers:
  - `Content-Type: application/json`
- Body (raw JSON):
```json
{
  "use_next_event": true,
  "buffer_minutes": 20
}
```

**Expected Response:**
A `ContextPackage` object with:
- `query_intent`: "route_to_event"
- `event`: Event details
- `origin`: Origin details
- `highlights`: Array of context bullets
- `alternatives`: Alternative routes
- `sources_used`: Data sources

---

### 3.4 Build Context (POST) - Direct Destination

**Request:**
- Method: `POST`
- URL: `{{base_url}}/build_context`
- Headers:
  - `Content-Type: application/json`
- Body (raw JSON):
```json
{
  "use_next_event": false,
  "destination": "The Met, 1000 5th Ave, New York, NY",
  "arrival_time_iso": "2025-11-08T16:00:00-05:00",
  "origin": "350 5th Ave, New York, NY",
  "buffer_minutes": 20
}
```

**Expected Response:**
Same as above, but with your specified destination.

---

### 3.5 Ask Question (POST)

**Request:**
- Method: `POST`
- URL: `{{base_url}}/ask`
- Headers:
  - `Content-Type: application/json`
- Body (raw JSON):
```json
{
  "question": "How can I reach my next meeting?",
  "origin": "Times Square, New York, NY",
  "buffer_minutes": 20
}
```

**Expected Response:**
```json
{
  "answer": "Generated answer text...",
  "context": { /* ContextPackage object */ }
}
```

---

### 3.6 Get Last Context (GET)

**Request:**
- Method: `GET`
- URL: `{{base_url}}/context/last`
- Headers: None needed

**Expected Response:**
The last generated `ContextPackage` (or `null` if none exists).

---

## Step 4: Testing Workflow

### Recommended Testing Sequence:

1. **Health Check** → Verify server is running
2. **Set Home Address** → Configure your origin
3. **Build Context** → Generate context package
4. **Get Last Context** → Retrieve the generated context
5. **Ask Question** → Get natural language answer

---

## Common Issues & Solutions

### Issue: "Origin is required"
**Solution:** Call `/config/home` first or include `origin` in the request body.

### Issue: "No upcoming event with a destination found"
**Solution:** 
- Set `use_next_event: false` and provide `destination` directly
- Or configure `GOOGLE_CALENDAR_ICS_URL` in your `.env` file

### Issue: Connection refused
**Solution:** 
- Make sure the server is running on port 8000
- Check if another service is using port 8000: `netstat -ano | findstr :8000`

### Issue: Mock mode responses
**Solution:** This is expected if API keys are not set. Add your API keys to `.env`:
- `GOOGLE_MAPS_API_KEY`
- `OPENWEATHER_API_KEY`
- `GOOGLE_CALENDAR_ICS_URL`

---

## Postman Collection JSON

You can import this collection directly into Postman:

```json
{
  "info": {
    "name": "Mobility Context API",
    "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
  },
  "variable": [
    {
      "key": "base_url",
      "value": "http://localhost:8000"
    }
  ],
  "item": [
    {
      "name": "Health Check",
      "request": {
        "method": "GET",
        "header": [],
        "url": {
          "raw": "{{base_url}}/health",
          "host": ["{{base_url}}"],
          "path": ["health"]
        }
      }
    },
    {
      "name": "Set Home Address",
      "request": {
        "method": "POST",
        "header": [
          {
            "key": "Content-Type",
            "value": "application/json"
          }
        ],
        "body": {
          "mode": "raw",
          "raw": "{\n  \"address\": \"Times Square, New York, NY\"\n}"
        },
        "url": {
          "raw": "{{base_url}}/config/home",
          "host": ["{{base_url}}"],
          "path": ["config", "home"]
        }
      }
    },
    {
      "name": "Build Context (Next Event)",
      "request": {
        "method": "POST",
        "header": [
          {
            "key": "Content-Type",
            "value": "application/json"
          }
        ],
        "body": {
          "mode": "raw",
          "raw": "{\n  \"use_next_event\": true,\n  \"buffer_minutes\": 20\n}"
        },
        "url": {
          "raw": "{{base_url}}/build_context",
          "host": ["{{base_url}}"],
          "path": ["build_context"]
        }
      }
    },
    {
      "name": "Build Context (Direct)",
      "request": {
        "method": "POST",
        "header": [
          {
            "key": "Content-Type",
            "value": "application/json"
          }
        ],
        "body": {
          "mode": "raw",
          "raw": "{\n  \"use_next_event\": false,\n  \"destination\": \"The Met, 1000 5th Ave, New York, NY\",\n  \"arrival_time_iso\": \"2025-11-08T16:00:00-05:00\",\n  \"origin\": \"350 5th Ave, New York, NY\",\n  \"buffer_minutes\": 20\n}"
        },
        "url": {
          "raw": "{{base_url}}/build_context",
          "host": ["{{base_url}}"],
          "path": ["build_context"]
        }
      }
    },
    {
      "name": "Ask Question",
      "request": {
        "method": "POST",
        "header": [
          {
            "key": "Content-Type",
            "value": "application/json"
          }
        ],
        "body": {
          "mode": "raw",
          "raw": "{\n  \"question\": \"How can I reach my next meeting?\",\n  \"origin\": \"Times Square, New York, NY\",\n  \"buffer_minutes\": 20\n}"
        },
        "url": {
          "raw": "{{base_url}}/ask",
          "host": ["{{base_url}}"],
          "path": ["ask"]
        }
      }
    },
    {
      "name": "Get Last Context",
      "request": {
        "method": "GET",
        "header": [],
        "url": {
          "raw": "{{base_url}}/context/last",
          "host": ["{{base_url}}"],
          "path": ["context", "last"]
        }
      }
    }
  ]
}
```

Save this as a `.json` file and import it into Postman via File → Import.

