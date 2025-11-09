from typing import Dict, List
from app.config import settings
from app.utils.http import get_http_client


def _parse_mta_outages_json(arr: list) -> Dict[str, str]:
    """
    Parse MTA JSON arrays (current or upcoming). Each element includes:
      station, equipmenttype (EL/ES), etc.
    Aggregate to station -> status string.
    """
    stations: Dict[str, int] = {}
    for item in arr or []:
        try:
            station = (item.get("station") or "").strip()
            equipment_type = (item.get("equipmenttype") or "").strip().upper()
            if not station:
                continue
            weight = 2 if equipment_type == "EL" else 1  # elevators have higher accessibility impact
            stations[station] = stations.get(station, 0) + weight
        except Exception:
            continue
    result: Dict[str, str] = {}
    for st, count in stations.items():
        if count >= 2:
            result[st] = "Multiple accessibility equipment outages"
        else:
            result[st] = "Accessibility equipment outage"
    return result


def get_elevator_outages_nyc() -> Dict[str, str]:
    """
    Returns a map of station name -> status string.
    Uses public MTA JSON feeds; falls back to a deterministic mock in MOCK_MODE or on error.
    """
    if not settings.MOCK_MODE:
        urls = [
            "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fnyct_ene.json",  # current
            "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fnyct_ene_upcoming.json",  # upcoming
        ]
        combined: Dict[str, str] = {}
        try:
            with get_http_client() as client:
                for url in urls:
                    r = client.get(url)
                    if r.status_code == 200:
                        try:
                            parsed = _parse_mta_outages_json(r.json())
                            combined.update(parsed)
                        except Exception:
                            continue
            if combined:
                return combined
        except Exception:
            pass
    # Mock: example outages for demo
    return {
        "86 St (Q)": "Elevator outage",
        "59 St-Columbus Circle": "Accessibility equipment outage",
    }


def outages_affecting_route_text(candidates: List[str]) -> List[str]:
    """
    Given a list of station-like strings appearing in a candidate route,
    return human-readable outage messages if any.
    """
    statuses = get_elevator_outages_nyc()
    msgs: List[str] = []
    for station in candidates:
        if station in statuses and "outage" in statuses[station].lower():
            msgs.append(f"Elevator outage at {station}")
    return msgs

