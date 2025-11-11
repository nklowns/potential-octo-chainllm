from __future__ import annotations
from typing import Protocol, Dict
from src.domain.tts_models import TTSRequest, AudioResult


class BaseTTSProvider(Protocol):
    def synthesize(self, request: TTSRequest) -> AudioResult: ...
    def capabilities(self) -> Dict[str, bool]: ...
