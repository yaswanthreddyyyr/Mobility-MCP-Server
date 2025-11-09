from __future__ import annotations
from typing import Any, Dict, List
import json
import httpx

from app.config import settings
from app.models.schemas import ContextPackage


def _format_prompt(question: str, context_pkg: ContextPackage) -> Dict[str, Any]:
    # Keep prompt compact; rely on citations from context
    parts = [
        {
            "text": (
                "You are an accessibility-focused mobility assistant. "
                "Answer concisely how to reach the destination, citing links from the context. "
                "Include leave-by time if present. If any outages/uncertainties exist, state them briefly."
            )
        },
        {"text": f"Question: {question}"},
        {"text": "Context package JSON:"},
        {"text": json.dumps(context_pkg.model_dump(), ensure_ascii=False)},
    ]
    return {"contents": [{"role": "user", "parts": parts}]}


def _answer_from_context_only(context_pkg: ContextPackage) -> str:
    # Fallback if no Gemini key: synthesize a compact answer from bullets
    lines: List[str] = []
    for b in context_pkg.highlights[:5]:
        lines.append(f"- {b.text}")
    if context_pkg.alternatives:
        lines.append(f"- Alternative: {context_pkg.alternatives[0].summary}")
    return "\n".join(lines)


def generate_answer_with_gemini(question: str, context_pkg: ContextPackage) -> str:
    api_key = None
    try:
        # Read from environment via pydantic settings (pass-through); not stored in config by default
        import os
        api_key = os.getenv("GEMINI_API_KEY")
    except Exception:
        api_key = None

    if not api_key:
        return _answer_from_context_only(context_pkg)

    body = _format_prompt(question, context_pkg)
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
    try:
        with httpx.Client(timeout=10.0) as client:
            r = client.post(url, json=body, headers={"Content-Type": "application/json"})
            if r.status_code != 200:
                return _answer_from_context_only(context_pkg)
            data = r.json()
            # Extract text from candidates
            candidates = (data.get("candidates") or [])
            if not candidates:
                return _answer_from_context_only(context_pkg)
            parts = candidates[0].get("content", {}).get("parts") or []
            texts = [p.get("text", "") for p in parts if isinstance(p, dict)]
            text = "\n".join([t for t in texts if t]).strip()
            return text or _answer_from_context_only(context_pkg)
    except Exception:
        return _answer_from_context_only(context_pkg)

