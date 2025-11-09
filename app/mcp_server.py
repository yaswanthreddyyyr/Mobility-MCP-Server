from __future__ import annotations
import sys
import json
import traceback
import os
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


def _orchestrate_build_context(
	use_next_event: bool,
	origin: Optional[str],
	buffer_minutes: int,
	question: Optional[str] = None,
) -> ContextPackage:
	if use_next_event:
		t, s, l = get_next_event()
		event_title, event_start_iso, event_location_text = t, s, l
	else:
		raise ValueError("Direct destination mode not implemented in MCP MVP; set use_next_event=True")

	origin_address = origin or state.home_address
	if not origin_address:
		raise ValueError("Origin is required (set via REST /config/home or pass origin)")
	if not event_location_text:
		raise ValueError("No next event destination available")

	dest_geo = geocode_address(event_location_text)
	if not dest_geo:
		raise ValueError("Failed to geocode destination")
	dest_lat, dest_lng, resolved_dest = dest_geo

	candidates = get_candidate_routes(origin_address, resolved_dest, event_start_iso)
	if not candidates:
		raise ValueError("No routes available")

	station_tokens = ["86 St (Q)", "Times Sq-42 St", "57 St", "96 St"]
	outage_msgs = outages_affecting_route_text(station_tokens)
	venue_wc = get_venue_wheelchair_tag(dest_lat, dest_lng)
	weather_risk, _ = get_weather_window(dest_lat, dest_lng, event_start_iso)

	fused = fuse_context(
		candidates=candidates,
		arrivals_iso=event_start_iso,
		buffer_min=buffer_minutes,
		outages_texts=outage_msgs,
		venue_wc=venue_wc,
		weather_risk=weather_risk,
	)

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
	return pkg


def _send(obj: Dict[str, Any]) -> None:
	try:
		data = json.dumps(obj, ensure_ascii=False).encode("utf-8")
		# Include Content-Type per MCP stdio expectations
		sys.stdout.buffer.write(f"Content-Length: {len(data)}\r\n".encode("ascii"))
		sys.stdout.buffer.write(b"Content-Type: application/json; charset=utf-8\r\n\r\n")
		sys.stdout.buffer.write(data)
		sys.stdout.buffer.flush()
		
		sys.stderr.write(f"[mobility-mcp] sent {len(data)} bytes\n")
		sys.stderr.flush()
	except Exception as e:
		sys.stderr.write(f"[mobility-mcp] send error: {e}\n")
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
			"tools": {},        # advertise tools support
			"resources": {},    # advertise resources support
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


def main() -> None:
	# Simple JSON-RPC over stdio with Content-Length framing
	# Log to stderr to avoid corrupting stdio protocol
	try:
		sys.stderr.write(f"[mobility-mcp] server started (MOCK_MODE={settings.MOCK_MODE})\n")
		sys.stderr.write(f"[mobility-mcp] Python version: {sys.version}\n")
		sys.stderr.write(f"[mobility-mcp] Working directory: {os.getcwd()}\n")
		sys.stderr.flush()
	except Exception as e:
		# If we can't even write to stderr, something is very wrong
		pass

	stdin = sys.stdin.buffer
	
	# IMPORTANT: Set stdin to unbuffered/blocking mode for proper stdio handling
	try:
		if hasattr(os, 'set_blocking'):
			os.set_blocking(stdin.fileno(), True)
		# On Windows, ensure stdin is in binary mode
		if sys.platform == "win32":
			try:
				import msvcrt
				msvcrt.setmode(stdin.fileno(), os.O_BINARY)
			except ImportError:
				pass  # msvcrt not available (unlikely on Windows, but handle gracefully)
	except Exception as e:
		sys.stderr.write(f"[mobility-mcp] warning: could not configure stdin: {e}\n")
		sys.stderr.flush()
	
	while True:
		try:
			# Read headers: accumulate bytes until we see \r\n\r\n or \n\n
			headers: Dict[str, str] = {}
			header_buffer = bytearray()
			max_header_size = 8192  # Prevent infinite loops
			
			while len(header_buffer) < max_header_size:
				try:
					chunk = stdin.read(1)
					if not chunk:
						if len(header_buffer) == 0:
							# EOF before any data - normal shutdown
							sys.stderr.write("[mobility-mcp] stdin closed (EOF)\n")
							sys.stderr.flush()
							return
						raise IOError("Unexpected EOF while reading headers")
					
					header_buffer += chunk
					
					# Check for end of headers: \r\n\r\n or \n\n
					if header_buffer.endswith(b"\r\n\r\n"):
						break
					if len(header_buffer) >= 2 and header_buffer.endswith(b"\n\n"):
						break
					
				except IOError as e:
					sys.stderr.write(f"[mobility-mcp] stdin read error: {e}\n")
					sys.stderr.flush()
					return
				except Exception as e:
					sys.stderr.write(f"[mobility-mcp] header read error: {e}\n")
					sys.stderr.flush()
					return
			
			if len(header_buffer) >= max_header_size:
				sys.stderr.write(f"[mobility-mcp] header too large (>{max_header_size} bytes)\n")
				sys.stderr.flush()
				continue
			
			# Parse headers
			try:
				header_text = header_buffer.decode("utf-8", errors="replace")
				for line in header_text.splitlines():
					line = line.strip()
					if not line:
						continue
					if ":" in line:
						k, v = line.split(":", 1)
						headers[k.strip().lower()] = v.strip()
			except Exception as e:
				sys.stderr.write(f"[mobility-mcp] header parsing error: {e}\n")
				sys.stderr.flush()
				continue
			
			# Get content length
			try:
				content_length = int(headers.get("content-length", "0"))
			except (ValueError, TypeError):
				sys.stderr.write(f"[mobility-mcp] invalid content-length header: {headers.get('content-length')}\n")
				sys.stderr.flush()
				continue
			
			if content_length <= 0:
				sys.stderr.write(f"[mobility-mcp] invalid content-length: {content_length}\n")
				sys.stderr.flush()
				continue
			
			# Read the exact payload
			payload = b""
			remaining = content_length
			while remaining > 0:
				chunk = stdin.read(remaining)
				if not chunk:
					sys.stderr.write(f"[mobility-mcp] incomplete payload: expected {content_length}, got {len(payload)}\n")
					sys.stderr.flush()
					return
				payload += chunk
				remaining -= len(chunk)
			
			if len(payload) != content_length:
				sys.stderr.write(f"[mobility-mcp] payload length mismatch: expected {content_length}, got {len(payload)}\n")
				sys.stderr.flush()
				continue
			
			try:
				req = json.loads(payload.decode("utf-8"))
				sys.stderr.write(f"[mobility-mcp] recv len={len(payload)} method={req.get('method')} id={req.get('id')}\n")
				sys.stderr.flush()
			except Exception as e:
				sys.stderr.write(f"[mobility-mcp] json decode error: {e}\n")
				sys.stderr.flush()
				continue

			id_ = req.get("id")
			method = req.get("method", "")
			params = req.get("params") or {}

			try:
				if method == "initialize":
					client_version = None
					try:
						client_version = (params or {}).get("protocolVersion")
					except Exception:
						client_version = None
					_result(id_, _initialize_result(client_version))
					sys.stderr.write("[mobility-mcp] sent initialize result\n")
					sys.stderr.flush()
					
				elif method == "tools/list":
					_result(id_, _tools_list())
					sys.stderr.write("[mobility-mcp] sent tools/list result\n")
					sys.stderr.flush()
					
				elif method == "tools/call":
					name = (params.get("name") or "").strip()
					args = params.get("arguments") or {}
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
						content = [{"type": "text", "text": "\n".join(lines)}]
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
						_error(id_, -32601, f"Unknown tool: {name}")
						
				elif method == "resources/list":
					_result(id_, _resources_list())
					sys.stderr.write("[mobility-mcp] sent resources/list result\n")
					sys.stderr.flush()
					
				elif method == "resources/read":
					uri = params.get("uri") or ""
					_result(id_, _resources_read(uri))
					sys.stderr.write(f"[mobility-mcp] sent resources/read result for {uri}\n")
					sys.stderr.flush()
					
				elif method == "notifications/cancelled":
					# Ignore cancellation notifications (no response needed)
					sys.stderr.write(f"[mobility-mcp] received cancellation: {params}\n")
					sys.stderr.flush()
					continue
					
				elif method == "notifications/initialized":
					# Ignore initialized notifications (no response needed)
					sys.stderr.write("[mobility-mcp] received initialized notification\n")
					sys.stderr.flush()
					continue
					
				else:
					# Don't error on unknown notifications (they don't expect responses)
					if method.startswith("notifications/"):
						sys.stderr.write(f"[mobility-mcp] ignoring notification: {method}\n")
						sys.stderr.flush()
						continue
					_error(id_, -32601, f"Unknown method: {method}")
					
			except Exception as e:
				sys.stderr.write(f"[mobility-mcp] error handling {method}: {e}\n")
				sys.stderr.write(traceback.format_exc())
				sys.stderr.flush()
				if id_ is not None:  # Only send error if there's an ID
					_error(id_, -32000, str(e))
				
		except KeyboardInterrupt:
			sys.stderr.write("[mobility-mcp] interrupted\n")
			sys.stderr.flush()
			return
		except Exception as e:
			sys.stderr.write(f"[mobility-mcp] main loop error: {e}\n")
			sys.stderr.write(traceback.format_exc())
			sys.stderr.flush()
			# Don't return here, try to continue processing
			continue


if __name__ == "__main__":
	try:
		main()
	except KeyboardInterrupt:
		sys.stderr.write("[mobility-mcp] interrupted by user\n")
		sys.stderr.flush()
		sys.exit(0)
	except Exception as e:
		sys.stderr.write(f"[mobility-mcp] fatal error: {e}\n")
		sys.stderr.write(traceback.format_exc())
		sys.stderr.flush()
		sys.exit(1)