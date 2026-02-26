import json
import hashlib
from typing import Literal

import httpx
from pydantic import BaseModel, Field

from .config import settings
from .models import Chunk


AtomType = Literal["decision", "commitment", "preference", "objective", "blocker", "insight"]


class ExtractedAtom(BaseModel):
    type: AtomType
    summary: str = Field(min_length=5, max_length=280)
    confidence: float = Field(ge=0.0, le=1.0, default=0.7)
    tags: list[str] = Field(default_factory=list)


class ExtractionResult(BaseModel):
    atoms: list[ExtractedAtom] = Field(default_factory=list)


def _atom_id(chunk: Chunk, idx: int, summary: str) -> str:
    raw = f"{chunk.file}:{chunk.line_start}:{idx}:{summary}".encode("utf-8")
    return "atom_" + hashlib.sha1(raw).hexdigest()[:12]


def extract_atoms(chunk: Chunk) -> list[dict]:
    if not settings.comet_api_key:
        return []

    system = (
        "Extract structured memory atoms from user notes. "
        "Return strict JSON only with key 'atoms'. "
        "Each atom: type (decision|commitment|preference|objective|blocker|insight), "
        "summary (short), confidence (0..1), tags (string[]). "
        "No prose outside JSON."
    )

    user = f"SOURCE FILE: {chunk.file}\nLINES: {chunk.line_start}-{chunk.line_end}\nTEXT:\n{chunk.text}"

    payload = {
        "model": settings.extraction_model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": 0.1,
        "response_format": {"type": "json_object"},
    }

    headers = {
        "Authorization": f"Bearer {settings.comet_api_key}",
        "Content-Type": "application/json",
    }

    with httpx.Client(timeout=60.0, follow_redirects=True) as client:
        resp = client.post(settings.chat_url, headers=headers, json=payload)
        resp.raise_for_status()
        data = resp.json()

    content = data.get("choices", [{}])[0].get("message", {}).get("content", "{}")
    parsed = ExtractionResult.model_validate(json.loads(content))

    atoms: list[dict] = []
    seen = set()
    for i, atom in enumerate(parsed.atoms):
        summary = " ".join((atom.summary or "").split()).strip()
        if len(summary) < 8:
            continue
        dedup = f"{atom.type}::{summary.lower()}"
        if dedup in seen:
            continue
        seen.add(dedup)

        atoms.append(
            {
                "id": _atom_id(chunk, i, summary),
                "type": atom.type,
                "summary": summary,
                "source_file": chunk.file,
                "source_line_start": chunk.line_start,
                "source_line_end": chunk.line_end,
                "confidence": atom.confidence,
                "tags": atom.tags,
                "status": "active",
            }
        )
    return atoms
