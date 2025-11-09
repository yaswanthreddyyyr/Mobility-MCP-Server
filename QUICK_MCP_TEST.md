# Quick MCP Server Test Guide for Postman

## Postman MCP Configuration

### Basic Setup in Postman

1. **Open Postman Desktop** → Click **New** → **MCP Request**

2. **Configure STDIO Connection:**
   - **Protocol**: `STDIO`
   - **Command**: `D:\Datathon\.venv\Scripts\python.exe`
   - **Arguments** (one per line):
     ```
     -m
     app.mcp_server
     ```
   - **Working Directory**: `D:\Datathon`

3. **Environment Variables** (if Postman supports):
   ```
   PYTHONPATH=D:\Datathon
   HOME_ADDRESS=Times Square, New York, NY
   MOCK_MODE=true
   PYTHONUNBUFFERED=1
   ```

4. **Click Connect** - Postman will start your server

## Quick Test Sequence

### 1. Initialize (usually automatic)
Postman should send this automatically when connecting.

### 2. List Tools
Should show:
- `ask` - How to reach next meeting
- `build_context` - Build context package

### 3. Test `ask` Tool
**Arguments:**
```json
{
  "question": "How can I reach my next meeting?",
  "origin": "Times Square, New York, NY",
  "buffer_minutes": 20
}
```

### 4. Test `build_context` Tool
**Arguments:**
```json
{
  "origin": "Times Square, New York, NY",
  "buffer_minutes": 20
}
```

## If Postman MCP UI Doesn't Work

Use **Postman Console** or create a **New Request** with these settings:

1. **Request Type**: Raw
2. **Protocol**: STDIO (if available)
3. **Send JSON-RPC messages** manually

### Manual JSON-RPC Test Messages

**Initialize:**
```json
Content-Length: 123

{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"postman","version":"1.0"}}}
```

**List Tools:**
```json
Content-Length: 45

{"jsonrpc":"2.0","id":2,"method":"tools/list"}
```

**Call ask:**
```json
Content-Length: 150

{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"ask","arguments":{"question":"How can I reach my next meeting?","origin":"Times Square, New York, NY","buffer_minutes":20}}}
```

## Verify Server Works First

Test the server manually before using Postman:

```powershell
cd D:\Datathon
$env:PYTHONPATH="D:\Datathon"
$env:HOME_ADDRESS="Times Square, New York, NY"
$env:MOCK_MODE="true"
.\.venv\Scripts\python.exe -m app.mcp_server
```

The server should start and wait for input. If it crashes immediately, check the error messages.

## Troubleshooting

- **"Command not found"**: Use full path: `D:\Datathon\.venv\Scripts\python.exe`
- **"Module not found"**: Set `PYTHONPATH=D:\Datathon` and `Working Directory=D:\Datathon`
- **"Connection timeout"**: Server might be crashing on startup - check stderr logs
- **"No response"**: Server might be waiting for input - verify stdio is connected

## Expected Behavior

✅ Server starts without errors
✅ Initialize request returns protocol version
✅ Tools list returns 2 tools (ask, build_context)
✅ Tool calls return content with text responses
✅ Resources list shows `context/last`

