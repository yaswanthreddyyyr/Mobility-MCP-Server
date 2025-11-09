from typing import Optional, Tuple
from app.config import settings
from app.utils.http import get_http_client


def get_venue_wheelchair_tag(lat: float, lon: float) -> Optional[Tuple[str, str]]:
    """
    Query a small bbox around the destination for wheelchair tags.
    Returns (tag_value, note) where tag_value in {"yes","limited","no","unknown"}.
    """
    overpass = settings.OSM_OVERPASS_URL
    # small bbox around lat,lon
    d = 0.0008
    bbox = f"{lat-d},{lon-d},{lat+d},{lon+d}"
    query = f"""
    [out:json][timeout:10];
    (
      node[\"wheelchair\"]({bbox});
      way[\"wheelchair\"]({bbox});
      relation[\"wheelchair\"]({bbox});
    );
    out tags center 10;
    """
    try:
        with get_http_client() as client:
            r = client.post(overpass, data={"data": query})
            if r.status_code == 200:
                data = r.json()
                elements = data.get("elements") or []
                for el in elements:
                    tags = el.get("tags") or {}
                    wc = tags.get("wheelchair")
                    if wc:
                        note = tags.get("wheelchair:description", "") or tags.get("description", "")
                        if wc not in {"yes", "limited", "no"}:
                            wc = "unknown"
                        return wc, note
    except Exception:
        pass
    return None

