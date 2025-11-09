from typing import List, Literal, Optional
from pydantic import BaseModel, Field


class BuildContextRequest(BaseModel):
    use_next_event: bool = Field(description="If true, use the next calendar event (stubbed in MVP)")
    query: Optional[str] = None
    origin: Optional[str] = None
    destination: Optional[str] = None
    arrival_time_iso: Optional[str] = None
    buffer_minutes: int = 20
    city: Optional[str] = None


class ContextBullet(BaseModel):
    type: Literal[
        "route_summary",
        "accessibility_alert",
        "venue_access",
        "weather_risk",
        "buffer_recommendation",
    ]
    text: str
    citations: List[str] = []


class AlternativeRoute(BaseModel):
    summary: str
    citations: List[str] = []


class EventRef(BaseModel):
    title: Optional[str] = None
    start_time_iso: Optional[str] = None
    location_text: Optional[str] = None


class OriginRef(BaseModel):
    label: Optional[str] = None
    address: Optional[str] = None


class ContextPackage(BaseModel):
    query_intent: Literal["route_to_event"]
    sources_used: List[str]
    event: EventRef
    origin: OriginRef
    highlights: List[ContextBullet]
    alternatives: List[AlternativeRoute] = []
    raw_citations: List[str] = []
    token_estimate: int = 0
    meta: dict = {}


class SetHomeRequest(BaseModel):
    address: str


class AskRequest(BaseModel):
    question: str
    origin: Optional[str] = None
    buffer_minutes: int = 20
    # For MVP, we assume "next meeting"; future: explicit destination in NL


class AskResponse(BaseModel):
    answer: str
    context: ContextPackage

