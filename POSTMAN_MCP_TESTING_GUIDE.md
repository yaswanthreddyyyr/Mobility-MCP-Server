# Testing MCP Server with Postman MCP Support

Postman has built-in MCP (Model Context Protocol) support that allows you to test your MCP server directly.

## Prerequisites

1. **Postman Desktop App** (latest version) - MCP support is available in Postman Desktop
2. Your MCP server code is ready in `D:\Datathon`

## Step-by-Step Guide

### Step 1: Open Postman and Create MCP Request

1. Open **Postman Desktop Application**
2. Click the **New** button (top left)
3. Select **MCP Request** from the dropdown menu
   - If you don't see "MCP Request", make sure you're using the latest version of Postman Desktop

### Step 2: Configure MCP Server Connection

In the MCP request configuration:

1. **Protocol**: Select **STDIO** (Standard Input/Output)

2. **Command**: Enter the full path to your Python executable:
   ```
   D:\Datathon\.venv\Scripts\python.exe
   ```
   Or use the relative path if Postman supports it:
   ```
   python
   ```

3. **Arguments**: Add the module argument:
   ```
   -m
   app.mcp_server
   ```
   (Enter each argument on a new line or as separate items)

4. **Working Directory** (if available):
   ```
   D:\Datathon
   ```

5. **Environment Variables** (if Postman supports it):
   Add these environment variables:
   ```
   PYTHONPATH=D:\Datathon
   HOME_ADDRESS=Times Square, New York, NY
   DEFAULT_CITY=nyc
   PYTHONUNBUFFERED=1
   MOCK_MODE=true
   GOOGLE_CALENDAR_ICS_URL=https://calendar.google.com/calendar/ical/yaswanthreddy%40tamu.edu/public/basic.ics
   GOOGLE_MAPS_API_KEY=<your_maps_key>
   OPENWEATHER_API_KEY=7ccb246835148fcc78e420ac7ba60c6d
   GEMINI_API_KEY=AIzaSyCpEHVUtAPJADqRPRf0QXC44evZPTlNCx8
   LOG_LEVEL=INFO
   ```

### Step 3: Connect to MCP Server

1. Click the **Connect** button
2. Postman will start your MCP server process
3. Wait for the connection to establish
4. You should see available tools listed:
   - `ask` - Accessibility-first: how to reach next meeting
   - `build_context` - Build the full context package

### Step 4: Test Available Tools

#### Test 1: List Tools

Postman should automatically show available tools after connection. If not, you can manually test:

**Request:**
- Method: `tools/list`
- This should return the list of available tools

#### Test 2: Call `ask` Tool

1. Select the **`ask`** tool from the list
2. Fill in the arguments:
   ```json
   {
     "question": "How can I reach my next meeting?",
     "origin": "Times Square, New York, NY",
     "buffer_minutes": 20
   }
   ```
3. Click **Run** or **Send**
4. Review the response - you should get a text answer with bullet points

#### Test 3: Call `build_context` Tool

1. Select the **`build_context`** tool
2. Fill in the arguments (all optional):
   ```json
   {
     "origin": "Times Square, New York, NY",
     "buffer_minutes": 20
   }
   ```
3. Click **Run**
4. Review the response - you should get a JSON context package

#### Test 4: List Resources

1. Select **`resources/list`** method
2. This should return available resources (should show `context/last`)

#### Test 5: Read Resource

1. Select **`resources/read`** method
2. Arguments:
   ```json
   {
     "uri": "context/last"
   }
   ```
3. This should return the last generated context package

## Alternative: Manual JSON-RPC Testing

If Postman's MCP UI doesn't work, you can test using raw JSON-RPC requests:

### Initialize Request

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "initialize",
  "params": {
    "protocolVersion": "2025-06-18",
    "capabilities": {},
    "clientInfo": {
      "name": "postman",
      "version": "1.0.0"
    }
  }
}
```

### Tools List Request

```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "method": "tools/list"
}
```

### Call Tool Request (ask)

```json
{
  "jsonrpc": "2.0",
  "id": 3,
  "method": "tools/call",
  "params": {
    "name": "ask",
    "arguments": {
      "question": "How can I reach my next meeting?",
      "origin": "Times Square, New York, NY",
      "buffer_minutes": 20
    }
  }
}
```

### Call Tool Request (build_context)

```json
{
  "jsonrpc": "2.0",
  "id": 4,
  "method": "tools/call",
  "params": {
    "name": "build_context",
    "arguments": {
      "origin": "Times Square, New York, NY",
      "buffer_minutes": 20
    }
  }
}
```

## Troubleshooting

### Issue: "Connection failed" or "Server not responding"

**Solutions:**
1. Check that Python path is correct: `D:\Datathon\.venv\Scripts\python.exe`
2. Verify the working directory is set to `D:\Datathon`
3. Make sure `PYTHONPATH` environment variable includes `D:\Datathon`
4. Check Postman's console/logs for error messages
5. Verify the server starts correctly by running it manually:
   ```powershell
   cd D:\Datathon
   .\.venv\Scripts\python.exe -m app.mcp_server
   ```

### Issue: "No tools available"

**Solutions:**
1. Make sure the `initialize` request was sent and succeeded
2. Check that `tools/list` returns the tools
3. Verify the server is processing requests (check stderr output if possible)

### Issue: "Invalid JSON-RPC" or "Protocol error"

**Solutions:**
1. Ensure your MCP server is using the correct protocol version (2025-06-18)
2. Check that Content-Length headers are being sent correctly
3. Verify the server is reading from stdin properly

### Issue: Environment variables not working

**Solutions:**
1. Set environment variables in Postman's MCP configuration if available
2. Or create a `.env` file in `D:\Datathon` with your variables
3. Or set them in your system environment variables

## Expected Responses

### Initialize Response
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "protocolVersion": "2025-06-18",
    "capabilities": {
      "tools": {},
      "resources": {}
    },
    "serverInfo": {
      "name": "mobility-mcp",
      "version": "0.1.0"
    }
  }
}
```

### Tools List Response
```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "result": {
    "tools": [
      {
        "name": "ask",
        "description": "Accessibility-first: how to reach next meeting. Returns a concise answer.",
        "inputSchema": {
          "type": "object",
          "properties": {
            "question": {"type": "string"},
            "origin": {"type": "string"},
            "buffer_minutes": {"type": "integer", "default": 20}
          },
          "required": ["question"]
        }
      },
      {
        "name": "build_context",
        "description": "Build the full context package (JSON string).",
        "inputSchema": {
          "type": "object",
          "properties": {
            "origin": {"type": "string"},
            "buffer_minutes": {"type": "integer", "default": 20}
          },
          "required": []
        }
      }
    ]
  }
}
```

### Ask Tool Response
```json
{
  "jsonrpc": "2.0",
  "id": 3,
  "result": {
    "content": [
      {
        "type": "text",
        "text": "- Route summary text\n- Accessibility alert\n- Venue access info\n- Weather risk\n- Buffer recommendation"
      }
    ]
  }
}
```

## Notes

- MCP servers communicate over **stdio** (standard input/output), not HTTP
- Postman's MCP support handles the stdio communication automatically
- The server logs to **stderr**, which Postman may display in a console/logs view
- Make sure your virtual environment is activated or use the full path to Python
- The server will keep running until you disconnect in Postman

## Quick Test Command

To verify your server works before testing in Postman, run this in PowerShell:

```powershell
cd D:\Datathon
$env:PYTHONPATH="D:\Datathon"
$env:HOME_ADDRESS="Times Square, New York, NY"
$env:MOCK_MODE="true"
.\.venv\Scripts\python.exe -m app.mcp_server
```

Then manually send JSON-RPC messages to test (or use Postman's MCP support).

