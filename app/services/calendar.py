from __future__ import annotations
from typing import Optional, Tuple
from datetime import datetime, timezone

from ics import Calendar  # type: ignore

from app.config import settings
from app.utils.http import get_http_client


def _parse_event_fields(e) -> Tuple[str, str, str]:
    title = (e.name or "Calendar Event").strip()
    # ics.Event.begin is an Arrow object; convert to ISO with tz
    begin_dt = e.begin.datetime if hasattr(e.begin, "datetime") else None
    if begin_dt and begin_dt.tzinfo is None:
        begin_dt = begin_dt.replace(tzinfo=timezone.utc)
    start_iso = begin_dt.isoformat() if begin_dt else None
    location = (getattr(e, "location", None) or "").strip()
    return title, start_iso, location


def get_next_event_from_ics() -> Optional[Tuple[str, str, str]]:
    """
    Returns the next upcoming event with a non-empty location as (title, start_iso, location).
    Source: Google Calendar private ICS URL (no OAuth needed).
    """
    ics_url = settings.GOOGLE_CALENDAR_ICS_URL
    if not ics_url:
        return None
    try:
        with get_http_client() as client:
            r = client.get(ics_url)
            if r.status_code != 200 or not r.text:
                return None
            cal = Calendar(r.text)
            now = datetime.now(timezone.utc)
            candidates = []
            for e in cal.events:
                try:
                    title, start_iso, location = _parse_event_fields(e)
                    if not location or not start_iso:
                        continue
                    start_dt = datetime.fromisoformat(start_iso)
                    if start_dt > now:
                        candidates.append((start_dt, (title, start_iso, location)))
                except Exception:
                    continue
            if not candidates:
                return None
            candidates.sort(key=lambda x: x[0])
            return candidates[0][1]
    except Exception:
        return None


def get_next_event() -> Optional[Tuple[str, str, str]]:
    ev = get_next_event_from_ics()
    if ev:
        return ev
    # Fallback deterministic stub
    return "Museum Visit", "2025-11-08T16:00:00-05:00", "The Met, 1000 5th Ave, New York, NY"

