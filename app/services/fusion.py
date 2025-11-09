from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

from app.models.schemas import ContextBullet, AlternativeRoute
from app.services.directions import RouteCandidate


@dataclass
class FusedDecision:
    best: RouteCandidate
    alternative: Optional[RouteCandidate]
    bullets: List[ContextBullet]
    raw_links: List[str]
    leave_by_iso: Optional[str]


def score_route(candidate: RouteCandidate, outage_hits: int, weather_penalty: int) -> float:
    score = 100.0
    score -= candidate.duration_min * 0.5
    score -= candidate.transfers * 5.0
    score -= outage_hits * 30.0
    score -= weather_penalty * 5.0
    if candidate.mode == "drive":
        score += 5.0  # faster, but maybe lower accessibility
    if candidate.mode == "bus":
        score += 2.0  # many buses are accessible; small boost
    return score


def compute_leave_by(arrival_iso: Optional[str], duration_min: int, buffer_min: int) -> Optional[str]:
    if not arrival_iso:
        return None
    try:
        arrival = datetime.fromisoformat(arrival_iso)
        leave_by = arrival - timedelta(minutes=duration_min + buffer_min)
        return leave_by.isoformat()
    except Exception:
        return None


def fuse_context(
    candidates: List[RouteCandidate],
    arrivals_iso: Optional[str],
    buffer_min: int,
    outages_texts: List[str],
    venue_wc: Optional[Tuple[str, str]],
    weather_risk: str,
) -> FusedDecision:
    weather_penalty = 1 if weather_risk else 0
    scored: List[Tuple[float, RouteCandidate]] = []
    for c in candidates:
        # naive: if any known problematic station is embedded in summary text, count one outage hit
        outage_hits = sum(1 for t in outages_texts if t.lower() in c.summary.lower())
        scored.append((score_route(c, outage_hits, weather_penalty), c))
    scored.sort(key=lambda x: x[0], reverse=True)
    best = scored[0][1] if scored else None
    alt = scored[1][1] if len(scored) > 1 else None

    bullets: List[ContextBullet] = []
    raw_links: List[str] = []

    if best:
        bullets.append(
            ContextBullet(
                type="route_summary",
                text=f"{best.summary}.",
                citations=[best.maps_url] if best.maps_url else [],
            )
        )
        if best.maps_url:
            raw_links.append(best.maps_url)

    # Accessibility alert
    if outages_texts:
        bullets.append(
            ContextBullet(
                type="accessibility_alert",
                text="; ".join(outages_texts) + ". Consider alternate stations if applicable.",
                citations=["https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fnyct_ene.json"],
            )
        )
        raw_links.append("https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fnyct_ene.json")

    # Venue wheelchair
    if venue_wc:
        wc, note = venue_wc
        note_part = f" — {note}" if note else ""
        bullets.append(
            ContextBullet(
                type="venue_access",
                text=f"Destination wheelchair access: {wc}{note_part}",
                citations=["https://overpass-api.de/api/interpreter"],
            )
        )
        raw_links.append("https://overpass-api.de/api/interpreter")

    # Weather
    if weather_risk:
        bullets.append(
            ContextBullet(
                type="weather_risk",
                text=weather_risk,
                citations=["https://openweathermap.org/"],
            )
        )
        raw_links.append("https://openweathermap.org/")

    leave_by_iso = compute_leave_by(arrivals_iso, best.duration_min if best else 0, buffer_min)
    if leave_by_iso:
        bullets.append(
            ContextBullet(
                type="buffer_recommendation",
                text=f"Leave by {leave_by_iso} to keep a {buffer_min} minute buffer.",
                citations=[],
            )
        )

    return FusedDecision(best=best, alternative=alt, bullets=bullets, raw_links=raw_links, leave_by_iso=leave_by_iso)

