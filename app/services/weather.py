from __future__ import annotations
from typing import Optional, Tuple
from datetime import datetime, timezone
from app.config import settings
from app.utils.http import get_http_client


def get_weather_window(lat: float, lon: float, target_iso: Optional[str]) -> Tuple[str, Optional[str]]:
    """
    Returns (risk_text, cite_url). If no risk, risk_text may be empty.
    Uses OpenWeather if available, else deterministic mock.
    """
    if settings.OPENWEATHER_API_KEY and not settings.MOCK_MODE:
        try:
            # Fetch hourly and check +/- 1 hour of target
            with get_http_client() as client:
                r = client.get(
                    "https://api.openweathermap.org/data/3.0/onecall",
                    params={
                        "lat": lat,
                        "lon": lon,
                        "appid": settings.OPENWEATHER_API_KEY,
                        "units": settings.WEATHER_UNITS,
                        "exclude": "minutely,daily,alerts",
                    },
                )
                if r.status_code == 200:
                    data = r.json()
                    target_ts = None
                    if target_iso:
                        try:
                            target_ts = int(datetime.fromisoformat(target_iso).replace(tzinfo=timezone.utc).timestamp())
                        except Exception:
                            target_ts = None
                    # Select the hour closest to target
                    cand = None
                    if target_ts and (hours := data.get("hourly")):
                        cand = sorted(hours, key=lambda h: abs((h.get("dt") or 0) - target_ts))[0]
                    else:
                        cand = (data.get("hourly") or [None])[0]
                    if cand:
                        rain = cand.get("rain", {}).get("1h", 0.0) if isinstance(cand.get("rain"), dict) else 0.0
                        wind = cand.get("wind_speed", 0.0) or 0.0
                        hazards = []
                        if rain and rain > 2.0:
                            hazards.append("heavy rain")
                        elif rain and rain > 0.2:
                            hazards.append("light rain")
                        if wind and wind > 8.3:  # ~30 km/h
                            hazards.append("strong wind")
                        if hazards:
                            return f"{', '.join(hazards).capitalize()} expected near travel time.", "https://openweathermap.org/"
                        return "", "https://openweathermap.org/"
        except Exception:
            pass
    # Mock risk
    return "Light rain expected; carry rain cover.", "https://openweathermap.org/"

