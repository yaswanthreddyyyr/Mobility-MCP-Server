from __future__ import annotations
import sys
import json
import traceback
import os
import time
from datetime import datetime
from typing import Optional, Tuple, List, Dict, Any

from app.config import state, settings
from app.models.schemas import ContextPackage
from app.services.calendar import get_next_event
from app.services.directions import get_candidate_routes
from app.services.fusion import fuse_context
from app.services.formatter import build_context_package
from app.services.geocode import geocode_address
from app.services.osm import get_venue_wheelchair_tag
from app.services.transit import outages_affecting_route_text
from app.services.weather import get_weather_window


def _log(level: str, message: str, **kwargs) -> None:
	"""Log a message with timestamp and optional context"""
	timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
	ctx = " ".join([f"{k}={v}" for k, v in kwargs.items()]) if kwargs else ""
	log_msg = f"[{timestamp}] [{level}] {message}"
	if ctx:
		log_msg += f" | {ctx}"
	sys.stderr.write(f"{log_msg}\n")
	sys.stderr.flush()


def _orchestrate_build_context(
	use_next_event: bool,
	origin: Optional[str],
	buffer_minutes: int,
	question: Optional[str] = None,
) -> ContextPackage:
	_log("INFO", "Starting context orchestration", 
		 use_next_event=use_next_event, 
		 origin=origin or "default", 
		 buffer_minutes=buffer_minutes,
		 has_question=question is not None)
	
	start_time = time.time()
	
	try:
		if use_next_event:
			_log("DEBUG", "Fetching next event from calendar")
			t, s, l = get_next_event()
			event_title, event_start_iso, event_location_text = t, s, l
			_log("INFO", "Next event retrieved", 
				 title=event_title, 
				 start=event_start_iso, 
				 location=event_location_text)
		else:
			raise ValueError("Direct destination mode not implemented in MCP MVP; set use_next_event=True")

		origin_address = origin or state.home_address
		if not origin_address:
			_log("ERROR", "Origin address not set", state_home=state.home_address, provided_origin=origin)
			raise ValueError("Origin is required (set via REST /config/home or pass origin)")
		_log("DEBUG", "Using origin address", address=origin_address)
		
		if not event_location_text:
			_log("ERROR", "No event location available")
			raise ValueError("No next event destination available")

		_log("DEBUG", "Geocoding destination", location=event_location_text)
		dest_geo = geocode_address(event_location_text)
		if not dest_geo:
			_log("ERROR", "Geocoding failed", location=event_location_text)
			raise ValueError("Failed to geocode destination")
		dest_lat, dest_lng, resolved_dest = dest_geo
		_log("INFO", "Destination geocoded", 
			 lat=dest_lat, 
			 lng=dest_lng, 
			 resolved=resolved_dest)

		_log("DEBUG", "Fetching candidate routes", 
			 origin=origin_address, 
			 destination=resolved_dest, 
			 arrival=event_start_iso)
		candidates = get_candidate_routes(origin_address, resolved_dest, event_start_iso)
		if not candidates:
			_log("ERROR", "No routes found", origin=origin_address, dest=resolved_dest)
			raise ValueError("No routes available")
		_log("INFO", "Routes retrieved", count=len(candidates))

		station_tokens = ["86 St (Q)", "Times Sq-42 St", "57 St", "96 St"]
		_log("DEBUG", "Checking transit outages", stations=len(station_tokens))
		outage_msgs = outages_affecting_route_text(station_tokens)
		_log("INFO", "Outage check complete", outage_count=len(outage_msgs))
		
		_log("DEBUG", "Checking venue wheelchair accessibility", lat=dest_lat, lng=dest_lng)
		venue_wc = get_venue_wheelchair_tag(dest_lat, dest_lng)
		_log("INFO", "Venue accessibility checked", wheelchair_accessible=venue_wc)
		
		_log("DEBUG", "Fetching weather window", lat=dest_lat, lng=dest_lng, time=event_start_iso)
		weather_risk, _ = get_weather_window(dest_lat, dest_lng, event_start_iso)
		_log("INFO", "Weather check complete", risk=weather_risk)

		_log("DEBUG", "Fusing context data", 
			 candidates=len(candidates), 
			 outages=len(outage_msgs),
			 buffer_min=buffer_minutes)
		fused = fuse_context(
			candidates=candidates,
			arrivals_iso=event_start_iso,
			buffer_min=buffer_minutes,
			outages_texts=outage_msgs,
			venue_wc=venue_wc,
			weather_risk=weather_risk,
		)
		_log("INFO", "Context fusion complete", bullets=len(fused.bullets), has_alternative=fused.alternative is not None)

		_log("DEBUG", "Building context package")
		pkg = build_context_package(
			event_title=event_title,
			event_start_iso=event_start_iso,
			event_location=resolved_dest,
			origin_label="Home",
			origin_address=origin_address,
			bullets=fused.bullets,
			alternative=fused.alternative.summary if fused.alternative else None,
			raw_links=fused.raw_links,
			sources=["directions", "gtfs_rt_elevators", "osm_overpass", "openweather"],
		)
		state.last_context_package = pkg.model_dump()
		
		elapsed = time.time() - start_time
		_log("INFO", "Context orchestration complete", 
			 elapsed_seconds=f"{elapsed:.2f}",
			 highlights=len(pkg.highlights),
			 alternatives=len(pkg.alternatives) if pkg.alternatives else 0)
		
		return pkg
	except Exception as e:
		elapsed = time.time() - start_time
		_log("ERROR", "Context orchestration failed", 
			 error=str(e), 
			 error_type=type(e).__name__,
			 elapsed_seconds=f"{elapsed:.2f}")
		sys.stderr.write(traceback.format_exc())
		sys.stderr.flush()
		raise


def _send(obj: Dict[str, Any]) -> None:
	"""Send a JSON-RPC response using MCP stdio format (always with headers)"""
	try:
		data = json.dumps(obj, ensure_ascii=False).encode("utf-8")
		header = f"Content-Length: {len(data)}\r\n".encode("ascii")
		content_type = b"Content-Type: application/json; charset=utf-8\r\n\r\n"
		
		_log("DEBUG", "Sending response", size=len(data), id=obj.get("id"), has_result="result" in obj, has_error="error" in obj)
		
		sys.stdout.buffer.write(header)
		sys.stdout.buffer.write(content_type)
		sys.stdout.buffer.write(data)
		sys.stdout.buffer.flush()
		
		# Force flush stderr too to ensure logs are visible
		sys.stderr.flush()
		
		_log("INFO", "Response sent successfully", size=len(data), id=obj.get("id"))
	except Exception as e:
		_log("ERROR", "Failed to send response", error=str(e), error_type=type(e).__name__)
		sys.stderr.write(traceback.format_exc())
		sys.stderr.flush()
		raise


def _result(id_: Any, result: Any) -> None:
	_send({"jsonrpc": "2.0", "id": id_, "result": result})


def _error(id_: Any, code: int, message: str) -> None:
	_send({"jsonrpc": "2.0", "id": id_, "error": {"code": code, "message": message}})


def _initialize_result(requested_version: Optional[str]) -> Dict[str, Any]:
	version = requested_version or "2025-06-18"
	return {
		"protocolVersion": version,
		"capabilities": {
			"tools": {},
			"resources": {},
		},
		"serverInfo": {"name": "mobility-mcp", "version": "0.1.0"},
	}


def _tools_list() -> Dict[str, Any]:
	return {
		"tools": [
			{
				"name": "ask",
				"description": "Accessibility-first: how to reach next meeting. Returns a concise answer.",
				"inputSchema": {
					"type": "object",
					"properties": {
						"question": {"type": "string"},
						"origin": {"type": "string"},
						"buffer_minutes": {"type": "integer", "default": 20},
					},
					"required": ["question"],
				},
			},
			{
				"name": "build_context",
				"description": "Build the full context package (JSON string).",
				"inputSchema": {
					"type": "object",
					"properties": {
						"origin": {"type": "string"},
						"buffer_minutes": {"type": "integer", "default": 20},
					},
					"required": [],
				},
			},
		]
	}


def _resources_list() -> Dict[str, Any]:
	return {
		"resources": [
			{"uri": "context/last", "name": "Last Context", "mimeType": "application/json"},
		]
	}


def _resources_read(uri: str) -> Dict[str, Any]:
	if uri != "context/last":
		raise ValueError("Unknown resource")
	text = json.dumps(state.last_context_package or {}, ensure_ascii=False, indent=2)
	return {"contents": [{"type": "text", "text": text}]}


def _read_message(stdin) -> Optional[Dict[str, Any]]:
	"""
	Read a single JSON-RPC message from stdin.
	Handles both MCP stdio format (with headers) and raw JSON format.
	"""
	# Read first byte to detect format (non-blocking detection)
	first_byte = stdin.read(1)
	if not first_byte:
		return None
	
	buffer = bytearray(first_byte)
	
	# Read a bit more to determine format (up to 100 bytes)
	peek_size = 99
	peek = stdin.read(peek_size)
	if peek:
		buffer += peek
	
	text = buffer.decode("utf-8", errors="replace")
	
	# Check if it's raw JSON (starts with {) or has headers
	if text.strip().startswith("{"):
		_log("DEBUG", "Detected raw JSON format", preview=text[:100])
		# Read until we have complete JSON
		max_size = 100000  # 100KB limit
		while len(buffer) < max_size:
			try:
				json_text = buffer.decode("utf-8").strip()
				# Try parsing - if successful, we're done
				result = json.loads(json_text)
				_log("DEBUG", "Successfully parsed raw JSON", size=len(buffer))
				return result
			except json.JSONDecodeError as e:
				# Incomplete - read more (read in smaller chunks to avoid blocking)
				more = stdin.read(256)  # Read 256 bytes at a time
				if not more:
					# EOF - try to parse what we have (might be complete)
					try:
						json_text = buffer.decode("utf-8").strip()
						result = json.loads(json_text)
						_log("DEBUG", "Parsed JSON at EOF", size=len(buffer))
						return result
					except:
						_log("ERROR", "Incomplete JSON at EOF", size=len(buffer), error_pos=getattr(e, "pos", "unknown"))
						return None
				buffer += more
		_log("ERROR", "Message too large", size=len(buffer))
		return None
	
	# Otherwise, it's MCP stdio format with headers
	_log("DEBUG", "Detected MCP stdio format")
	
	# Find header delimiter
	header_end = -1
	delimiter_len = 0
	
	# Look for \r\n\r\n or \n\n
	if b"\r\n\r\n" in buffer:
		header_end = buffer.find(b"\r\n\r\n")
		delimiter_len = 4
	elif b"\n\n" in buffer:
		header_end = buffer.find(b"\n\n")
		delimiter_len = 2
	
	# If delimiter not found, read more
	while header_end == -1 and len(buffer) < 8192:
		more = stdin.read(256)
		if not more:
			_log("ERROR", "EOF before header delimiter", size=len(buffer))
			return None
		buffer += more
		if b"\r\n\r\n" in buffer:
			header_end = buffer.find(b"\r\n\r\n")
			delimiter_len = 4
		elif b"\n\n" in buffer:
			header_end = buffer.find(b"\n\n")
			delimiter_len = 2
	
	if header_end == -1:
		_log("ERROR", "Header delimiter not found", size=len(buffer), preview=buffer[:200].decode("utf-8", errors="replace"))
		return None
	
	# Parse headers
	header_text = buffer[:header_end].decode("utf-8", errors="replace")
	headers = {}
	for line in header_text.splitlines():
		line = line.strip()
		if ":" in line:
			k, v = line.split(":", 1)
			headers[k.strip().lower()] = v.strip()
	
	_log("DEBUG", "Parsed headers", headers=list(headers.keys()))
	
	# Get content length
	try:
		content_length = int(headers.get("content-length", "0"))
	except (ValueError, TypeError):
		_log("ERROR", "Invalid content-length header", value=headers.get("content-length"))
		return None
	
	if content_length <= 0:
		_log("ERROR", "Invalid content length", content_length=content_length)
		return None
	
	# Read payload
	payload_start = header_end + delimiter_len
	payload = bytearray(buffer[payload_start:])
	remaining = content_length - len(payload)
	
	_log("DEBUG", "Reading payload", expected=content_length, already_have=len(payload), remaining=remaining)
	
	while remaining > 0:
		chunk = stdin.read(remaining)
		if not chunk:
			_log("ERROR", "Incomplete payload", expected=content_length, received=len(payload))
			return None
		payload += chunk
		remaining -= len(chunk)
	
	# Parse JSON payload
	try:
		json_text = payload.decode("utf-8")
		result = json.loads(json_text)
		_log("DEBUG", "Parsed JSON payload", size=len(payload))
		return result
	except Exception as e:
		_log("ERROR", "Failed to parse JSON payload", error=str(e), error_type=type(e).__name__)
		return None


def main() -> None:
	"""Main MCP server loop"""
	try:
		_log("INFO", "MCP Server starting", 
			 mock_mode=settings.MOCK_MODE,
			 python_version=sys.version.split()[0],
			 platform=sys.platform,
			 working_dir=os.getcwd(),
			 pythonpath=os.environ.get("PYTHONPATH", "not set"),
			 pythonunbuffered=os.environ.get("PYTHONUNBUFFERED", "not set"))
	except Exception:
		pass

	stdin = sys.stdin.buffer
	
	# Configure stdin for Windows
	try:
		if sys.platform == "win32":
			import msvcrt
			msvcrt.setmode(stdin.fileno(), os.O_BINARY)
			_log("DEBUG", "Set stdin to binary mode (Windows)")
	except Exception as e:
		_log("WARN", "Could not configure stdin", error=str(e))
	
	_log("INFO", "MCP Server ready, waiting for requests")
	request_count = 0
	
	while True:
		try:
			request_count += 1
			_log("DEBUG", "Reading request", request_number=request_count)
			
			req = _read_message(stdin)
			if req is None:
				_log("INFO", "No more messages, shutting down")
				break
			
			id_ = req.get("id")
			method = req.get("method", "")
			params = req.get("params") or {}
			
			_log("INFO", "Received request", method=method, id=id_, request_number=request_count)
			
			try:
				if method == "initialize":
					client_version = params.get("protocolVersion")
					_log("INFO", "Handling initialize", client_version=client_version, request_id=id_)
					_result(id_, _initialize_result(client_version))
					
				elif method == "tools/list":
					_log("INFO", "Handling tools/list", request_id=id_)
					_result(id_, _tools_list())
					
				elif method == "tools/call":
					name = (params.get("name") or "").strip()
					args = params.get("arguments") or {}
					_log("INFO", "Handling tools/call", tool_name=name, request_id=id_)
					
					try:
						if name == "ask":
							pkg = _orchestrate_build_context(
								use_next_event=True,
								origin=args.get("origin"),
								buffer_minutes=int(args.get("buffer_minutes") or 20),
								question=args.get("question"),
							)
							lines: List[str] = [f"- {b.text}" for b in pkg.highlights[:5]]
							if pkg.alternatives:
								lines.append(f"- Alternative: {pkg.alternatives[0].summary}")
							answer_text = "\n".join(lines)
							# Return both answer text and full context package
							content = [
								{"type": "text", "text": answer_text},
								{"type": "text", "text": json.dumps({"context": pkg.model_dump()}, ensure_ascii=False)}
							]
							_result(id_, {"content": content})
							
						elif name == "build_context":
							pkg = _orchestrate_build_context(
								use_next_event=True,
								origin=args.get("origin"),
								buffer_minutes=int(args.get("buffer_minutes") or 20),
							)
							content = [{"type": "text", "text": json.dumps(pkg.model_dump(), ensure_ascii=False)}]
							_result(id_, {"content": content})
						else:
							_log("WARN", "Unknown tool", tool_name=name, request_id=id_)
							_error(id_, -32601, f"Unknown tool: {name}")
					except Exception as tool_error:
						error_msg = str(tool_error)
						_log("ERROR", "Tool execution failed", tool_name=name, error=error_msg, request_id=id_)
						sys.stderr.write(traceback.format_exc())
						sys.stderr.flush()
						_error(id_, -32000, f"Tool execution failed: {error_msg}")
						
				elif method == "resources/list":
					_log("INFO", "Handling resources/list", request_id=id_)
					_result(id_, _resources_list())
					
				elif method == "resources/read":
					uri = params.get("uri") or ""
					_log("INFO", "Handling resources/read", uri=uri, request_id=id_)
					try:
						result = _resources_read(uri)
						_result(id_, result)
					except Exception as e:
						_log("ERROR", "Resource read failed", uri=uri, error=str(e), request_id=id_)
						_error(id_, -32000, f"Resource read failed: {str(e)}")
					
				elif method == "notifications/cancelled":
					_log("DEBUG", "Received cancellation notification")
					continue
					
				elif method == "notifications/initialized":
					_log("DEBUG", "Received initialized notification")
					continue
					
				else:
					if method.startswith("notifications/"):
						_log("DEBUG", "Ignoring notification", method=method)
						continue
					_log("WARN", "Unknown method", method=method, request_id=id_)
					if id_ is not None:
						_error(id_, -32601, f"Unknown method: {method}")
				
			except Exception as e:
				_log("ERROR", "Error handling method", method=method, error=str(e), request_id=id_)
				sys.stderr.write(traceback.format_exc())
				sys.stderr.flush()
				if id_ is not None:
					_error(id_, -32000, str(e))
				
		except KeyboardInterrupt:
			_log("INFO", "Server interrupted by user")
			break
		except Exception as e:
			_log("ERROR", "Main loop error", error=str(e), error_type=type(e).__name__)
			sys.stderr.write(traceback.format_exc())
			sys.stderr.flush()
			# Continue processing
			continue


if __name__ == "__main__":
	try:
		main()
	except KeyboardInterrupt:
		_log("INFO", "Server shutdown by user interrupt")
		sys.exit(0)
	except Exception as e:
		_log("FATAL", "Fatal error causing server exit", error=str(e), error_type=type(e).__name__)
		sys.stderr.write(traceback.format_exc())
		sys.stderr.flush()
		sys.exit(1)
