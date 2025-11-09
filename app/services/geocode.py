from typing import Optional, Tuple
from app.config import settings
from app.utils.http import get_http_client


def geocode_address(address: str) -> Optional[Tuple[float, float, str]]:
    """
    Returns (lat, lng, resolved_address) or None.
    Uses Google Geocoding if key present; otherwise Nominatim fallback.
    """
    address = address.strip()
    try:
        if settings.GOOGLE_MAPS_API_KEY:
            url = "https://maps.googleapis.com/maps/api/geocode/json"
            with get_http_client() as client:
                r = client.get(url, params={"address": address, "key": settings.GOOGLE_MAPS_API_KEY})
                if r.status_code == 200:
                    data = r.json()
                    results = data.get("results") or []
                    if results:
                        loc = results[0]["geometry"]["location"]
                        formatted = results[0].get("formatted_address", address)
                        return loc["lat"], loc["lng"], formatted
        # Fallback to Nominatim
        url = "https://nominatim.openstreetmap.org/search"
        with get_http_client() as client:
            r = client.get(url, params={"q": address, "format": "json", "limit": 1})
            if r.status_code == 200:
                arr = r.json()
                if arr:
                    lat = float(arr[0]["lat"])
                    lon = float(arr[0]["lon"])
                    disp = arr[0].get("display_name", address)
                    return lat, lon, disp
    except Exception:
        return None
    return None

