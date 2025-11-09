from __future__ import annotations
from typing import List, Optional
from app.models.schemas import AlternativeRoute, ContextBullet, ContextPackage, EventRef, OriginRef


def estimate_tokens(texts: List[str]) -> int:
    # Rudimentary token estimate (~4 chars per token)
    chars = sum(len(t) for t in texts)
    return max(1, chars // 4)


def build_context_package(
    event_title: Optional[str],
    event_start_iso: Optional[str],
    event_location: Optional[str],
    origin_label: Optional[str],
    origin_address: Optional[str],
    bullets: List[ContextBullet],
    alternative: Optional[str],
    raw_links: List[str],
    sources: List[str],
) -> ContextPackage:
    alts: List[AlternativeRoute] = []
    if alternative:
        alts.append(AlternativeRoute(summary=alternative, citations=raw_links[:1]))

    texts = [b.text for b in bullets] + ([alternative] if alternative else [])  # for token estimate
    token_est = estimate_tokens(texts)

    pkg = ContextPackage(
        query_intent="route_to_event",
        sources_used=sources,
        event=EventRef(title=event_title, start_time_iso=event_start_iso, location_text=event_location),
        origin=OriginRef(label=origin_label, address=origin_address),
        highlights=bullets[:5],
        alternatives=alts,
        raw_citations=list(dict.fromkeys(raw_links))[:6],
        token_estimate=token_est,
        meta={},
    )
    return pkg

