from __future__ import annotations
from typing import Any, Dict, List, Optional
from datetime import datetime
from urllib.parse import urlencode, quote_plus

from app.config import settings
from app.utils.http import get_http_client


class RouteCandidate:
    def __init__(self, summary: str, duration_min: int, transfers: int, mode: str, maps_url: str):
        self.summary = summary
        self.duration_min = duration_min
        self.transfers = transfers
        self.mode = mode
        self.maps_url = maps_url


def google_maps_link(origin: str, destination: str, arrival_time_iso: Optional[str]) -> str:
    params = {
        "saddr": origin,
        "daddr": destination,
    }
    if arrival_time_iso:
        # Google maps supports arrival_time as seconds in some APIs; for link we pass as query note
        params["arrival"] = arrival_time_iso
    return "https://www.google.com/maps/dir/?" + urlencode(params, quote_via=quote_plus)


def get_candidate_routes(origin: str, destination: str, arrival_time_iso: Optional[str]) -> List[RouteCandidate]:
    """
    Returns a small set of candidates. Uses Google Directions if key available;
    otherwise returns mocked deterministic candidates.
    """
    if not origin or not destination:
        return []

    maps_url = google_maps_link(origin, destination, arrival_time_iso)

    if settings.GOOGLE_MAPS_API_KEY and not settings.MOCK_MODE:
        try:
            with get_http_client() as client:
                params: Dict[str, Any] = {
                    "origin": origin,
                    "destination": destination,
                    "mode": "transit",
                    "alternatives": "true",
                    "key": settings.GOOGLE_MAPS_API_KEY,
                }
                if arrival_time_iso:
                    try:
                        ts = int(datetime.fromisoformat(arrival_time_iso).timestamp())
                        params["arrival_time"] = ts
                    except Exception:
                        pass
                r = client.get("https://maps.googleapis.com/maps/api/directions/json", params=params)
                if r.status_code == 200:
                    data = r.json()
                    routes = data.get("routes") or []
                    candidates: List[RouteCandidate] = []
                    for route in routes[:3]:
                        legs = route.get("legs") or []
                        if not legs:
                            continue
                        leg = legs[0]
                        duration_sec = leg.get("duration", {}).get("value", 0)
                        duration_min = max(1, duration_sec // 60)
                        # Estimate transfers: count transit steps minus 1
                        steps = leg.get("steps") or []
                        transit_legs = [s for s in steps if s.get("travel_mode") == "TRANSIT"]
                        transfers = max(0, len(transit_legs) - 1)
                        summary = route.get("summary") or f"Transit route ({duration_min} min)"
                        candidates.append(
                            RouteCandidate(
                                summary=f"{summary} ({duration_min} min, {transfers} transfer{'s' if transfers!=1 else ''})",
                                duration_min=duration_min,
                                transfers=transfers,
                                mode="transit",
                                maps_url=maps_url,
                            )
                        )
                    if candidates:
                        return candidates
        except Exception:
            pass

    # Mock deterministic candidates (NYC flavored)
    mocked: List[RouteCandidate] = [
        RouteCandidate(
            summary="Q line via 57 St (57 min, 1 transfer)",
            duration_min=57,
            transfers=1,
            mode="transit",
            maps_url=maps_url,
        ),
        RouteCandidate(
            summary="M1 → M4 accessible bus (65 min, 1 transfer)",
            duration_min=65,
            transfers=1,
            mode="bus",
            maps_url=maps_url,
        ),
        RouteCandidate(
            summary="Taxi/ride (28 min, no transfers)",
            duration_min=28,
            transfers=0,
            mode="drive",
            maps_url=maps_url,
        ),
    ]
    return mocked

