from __future__ import annotations

from typing import Dict
from src.infrastructure.tts.base_provider import BaseTTSProvider
from src.domain.tts_models import TTSRequest, AudioResult


class MockProvider(BaseTTSProvider):
    def __init__(self, fail: bool = False, payload: bytes | None = None):
        self.fail = fail
        self.payload = payload or b"RIFF\x00\x00\x00\x00WAVEfmt "  # header fake

    def capabilities(self) -> Dict[str, bool]:
        return {"supports_tone": False, "supports_ssml": False}

    def synthesize(self, request: TTSRequest) -> AudioResult:
        if self.fail:
            raise RuntimeError("Mock failure")
        text = "\n".join(request.text_blocks)
        meta = {
            "backend": request.backend,
            "voice_alias": request.voice_alias,
            "model_id": request.model_id,
            "chars": len(text),
        }
        return AudioResult(audio_bytes=self.payload, meta=meta)
