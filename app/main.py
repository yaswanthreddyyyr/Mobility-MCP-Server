from __future__ import annotations
from datetime import datetime
from typing import Optional, Tuple

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import orjson

from app.config import settings, state
from app.models.schemas import BuildContextRequest, ContextPackage, SetHomeRequest, AskRequest
from app.services.calendar import get_next_event
from app.services.directions import get_candidate_routes
from app.services.fusion import fuse_context
from app.services.formatter import build_context_package
from app.services.geocode import geocode_address
from app.services.osm import get_venue_wheelchair_tag
from app.services.transit import outages_affecting_route_text
from app.services.weather import get_weather_window
from app.services.llm import generate_answer_with_gemini


def _json(obj) -> str:
    return orjson.dumps(obj, option=orjson.OPT_INDENT_2).decode()


app = FastAPI(title="Accessibility Mobility Context Router (MVP)", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok", "mock_mode": settings.MOCK_MODE}


@app.post("/config/home")
def set_home(req: SetHomeRequest):
    state.home_address = req.address
    return {"ok": True, "home_address": state.home_address}


@app.get("/context/last", response_model=Optional[ContextPackage])
def get_last_context():
    return state.last_context_package


def resolve_event_and_origin(
    req: BuildContextRequest,
) -> Tuple[Optional[str], Optional[str], Optional[str], Optional[str]]:
    """
    Returns (event_title, event_start_iso, event_location_text, origin_address)
    """
    event_title: Optional[str] = None
    event_start_iso: Optional[str] = None
    event_location_text: Optional[str] = None
    origin_address: Optional[str] = None

    if req.use_next_event:
        t, s, l = get_next_event()
        event_title, event_start_iso, event_location_text = t, s, l
    else:
        # direct parameters
        event_title = req.query or "Planned Trip"
        event_start_iso = req.arrival_time_iso
        event_location_text = req.destination

    origin_address = req.origin or state.home_address or settings.HOME_ADDRESS
    return event_title, event_start_iso, event_location_text, origin_address


@app.post("/build_context", response_model=ContextPackage)
def build_context(req: BuildContextRequest):
    # Resolve event/origin
    event_title, event_start_iso, event_location_text, origin_address = resolve_event_and_origin(req)
    if not event_location_text:
        raise HTTPException(status_code=400, detail="Destination is required (no calendar integration yet).")
    if not origin_address:
        raise HTTPException(status_code=400, detail="Origin is required (set HOME_ADDRESS or pass 'origin').")

    # Geocode destination for OSM and weather
    dest_geo = geocode_address(event_location_text)
    if not dest_geo:
        raise HTTPException(status_code=400, detail="Failed to geocode destination.")
    dest_lat, dest_lng, resolved_dest = dest_geo

    # Build candidate routes
    candidates = get_candidate_routes(origin_address, resolved_dest, event_start_iso)
    if not candidates:
        raise HTTPException(status_code=502, detail="No routes available.")

    # Transit/elevator outages (MVP text matching on route summaries)
    # A more robust approach would map steps to station IDs.
    station_tokens = ["86 St (Q)", "Times Sq-42 St", "57 St", "96 St"]  # simple tokens to scan
    outage_msgs = outages_affecting_route_text(station_tokens)

    # Venue wheelchair from OSM
    venue_wc = get_venue_wheelchair_tag(dest_lat, dest_lng)

    # Weather around arrival
    weather_risk, weather_cite = get_weather_window(dest_lat, dest_lng, event_start_iso)

    # Fuse into bullets
    fused = fuse_context(
        candidates=candidates,
        arrivals_iso=event_start_iso,
        buffer_min=req.buffer_minutes,
        outages_texts=outage_msgs,
        venue_wc=venue_wc,
        weather_risk=weather_risk,
    )

    alternative_summary = fused.alternative.summary if fused.alternative else None
    sources = [
        "directions",
        "gtfs_rt_elevators",
        "osm_overpass",
        "openweather",
    ]

    pkg = build_context_package(
        event_title=event_title,
        event_start_iso=event_start_iso,
        event_location=resolved_dest,
        origin_label="Home",
        origin_address=origin_address,
        bullets=fused.bullets,
        alternative=alternative_summary,
        raw_links=fused.raw_links,
        sources=sources,
    )

    state.last_context_package = pkg.model_dump()
    return pkg


@app.post("/ask")
def ask(req: AskRequest):
    # Single entry point: assume "next meeting" intent for MVP
    # Resolve event via stub and origin via state or request
    event_title, event_start_iso, event_location_text, origin_address = resolve_event_and_origin(
        BuildContextRequest(use_next_event=True, query=req.question, origin=req.origin, buffer_minutes=req.buffer_minutes)
    )
    if not event_location_text:
        raise HTTPException(status_code=400, detail="No upcoming event with a destination found (stub). Provide destination via /build_context.")
    if not origin_address:
        raise HTTPException(status_code=400, detail="Origin is required (set HOME_ADDRESS or call /config/home).")

    # Geocode destination
    dest_geo = geocode_address(event_location_text)
    if not dest_geo:
        raise HTTPException(status_code=400, detail="Failed to geocode destination.")
    dest_lat, dest_lng, resolved_dest = dest_geo

    # Routes
    candidates = get_candidate_routes(origin_address, resolved_dest, event_start_iso)
    if not candidates:
        raise HTTPException(status_code=502, detail="No routes available.")

    # Outages (simple token-based check for MVP)
    station_tokens = ["86 St (Q)", "Times Sq-42 St", "57 St", "96 St"]
    outage_msgs = outages_affecting_route_text(station_tokens)

    # Venue access
    venue_wc = get_venue_wheelchair_tag(dest_lat, dest_lng)

    # Weather
    weather_risk, _ = get_weather_window(dest_lat, dest_lng, event_start_iso)

    # Fuse
    fused = fuse_context(
        candidates=candidates,
        arrivals_iso=event_start_iso,
        buffer_min=req.buffer_minutes,
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

    # Call Gemini (or synth fallback) and return answer + context
    answer = generate_answer_with_gemini(req.question, pkg)
    state.last_context_package = pkg.model_dump()
    return {"answer": answer, "context": pkg}

