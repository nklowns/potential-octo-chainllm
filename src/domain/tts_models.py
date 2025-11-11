from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass
class ProsodyOptions:
    pace: float = 1.0
    tone: Optional[str] = None  # 'energico', 'calmo', etc.


@dataclass
class TTSRequest:
    text_blocks: List[str]
    voice_alias: str
    backend: str
    model_id: str
    params: Dict[str, float]
    prosody: ProsodyOptions


@dataclass
class AudioResult:
    audio_bytes: bytes
    meta: Dict
