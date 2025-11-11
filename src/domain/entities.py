"""Domain entities (immutable) for pipeline artifacts and quality outcomes."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any


def _utc_now_iso() -> str:
    return datetime.utcnow().isoformat() + "Z"


@dataclass(frozen=True)
class Script:
    script_id: str
    topic: str
    content: str
    word_count: int
    created_at: str = field(default_factory=_utc_now_iso)

    @staticmethod
    def from_content(script_id: str, topic: str, content: str) -> "Script":
        return Script(script_id=script_id, topic=topic, content=content, word_count=len(content.split()))


@dataclass(frozen=True)
class AudioArtifact:
    audio_id: str
    script_id: str
    path: str
    duration: float | None
    created_at: str = field(default_factory=_utc_now_iso)


@dataclass(frozen=True)
class QualityGateOutcome:
    gate_name: str
    status: str  # pass|fail|warn|error
    severity: str  # error|warn|info
    message: str
    details: Dict[str, Any]
    duration_ms: int
    created_at: str = field(default_factory=_utc_now_iso)
