from __future__ import annotations

import logging
import requests
from typing import Dict
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from src.domain.tts_models import TTSRequest, AudioResult
from src.infrastructure.tts.base_provider import BaseTTSProvider
from src.infrastructure.config.tts_backends import TTSBackendsConfig
from src.pipeline import config as pipeline_config

logger = logging.getLogger(__name__)


class PiperProvider(BaseTTSProvider):
    def __init__(self, base_url: str | None = None):
        backends = TTSBackendsConfig()
        piper_cfg = backends.get_backend('piper')
        resolved_base = base_url or (piper_cfg.base_url if piper_cfg else '')
        if not resolved_base:
            raise RuntimeError("PiperProvider: base_url ausente. Defina config/voices.json -> available_backends.piper.base_url")
        self.base_url = resolved_base
        # Cache de defaults do backend (evita N leituras)
        self._defaults = {
            "length_scale": getattr(piper_cfg.defaults, 'length_scale', 1.0) if piper_cfg else 1.0,
            "noise_scale": getattr(piper_cfg.defaults, 'noise_scale', 0.667) if piper_cfg else 0.667,
            "noise_w_scale": getattr(piper_cfg.defaults, 'noise_w_scale', 0.8) if piper_cfg else 0.8,
        }
        self.session = self._create_session()
        self._verify()

    def _create_session(self) -> requests.Session:
        s = requests.Session()
        max_retries = getattr(pipeline_config, 'MAX_RETRIES', 3)
        retry_strategy = Retry(
            total=max_retries,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        s.mount("http://", adapter)
        s.mount("https://", adapter)
        return s

    def _verify(self):
        try:
            r = self.session.get(f"{self.base_url}/voices", timeout=10)
            r.raise_for_status()
            logger.info("PiperProvider conectado.")
        except Exception as e:
            logger.warning(f"Falha ao verificar PiperProvider: {e}")

    def capabilities(self) -> Dict[str, bool]:
        return {"supports_tone": False, "supports_ssml": False}

    def synthesize(self, request: TTSRequest) -> AudioResult:
        # Piper atual espera campo 'text' único. Unimos blocos com \n.
        joined = "\n".join(request.text_blocks).strip()
        # Merge params: voz override -> backend defaults
        eff = {
            "length_scale": request.params.get("length_scale", self._defaults["length_scale"]),
            "noise_scale": request.params.get("noise_scale", self._defaults["noise_scale"]),
            "noise_w_scale": request.params.get("noise_w_scale", self._defaults["noise_w_scale"]),
        }
        payload = {
            "text": joined,
            "voice": request.model_id,
            "length_scale": eff["length_scale"],
            "noise_scale": eff["noise_scale"],
            "noise_w_scale": eff["noise_w_scale"],
        }
        try:
            import time
            t0 = time.time()
            resp = self.session.post(self.base_url, json=payload, timeout=180)
            resp.raise_for_status()
            audio = resp.content
            meta = {
                "backend": "piper",
                "voice_alias": request.voice_alias,
                "model_id": request.model_id,
                "chars": len(joined),
            }
            try:
                from src.utils.metrics_exporter import update_http_metrics
                dt = int((time.time() - t0) * 1000)
                from src.pipeline import config as cfg
                update_http_metrics(cfg.OUTPUT_DIR / 'metrics', 'piper_tts', 'POST', 200, dt)
            except Exception:
                pass
            return AudioResult(audio_bytes=audio, meta=meta)
        except Exception as e:
            logger.error(f"Erro na síntese Piper: {e}")
            try:
                import time
                from src.utils.metrics_exporter import update_http_metrics
                from src.pipeline import config as cfg
                dt = int((time.time() - t0) * 1000) if 't0' in locals() else 0
                status = getattr(e, 'response', None).status_code if hasattr(e, 'response') and e.response is not None else 'error'
                update_http_metrics(cfg.OUTPUT_DIR / 'metrics', 'piper_tts', 'POST', status, dt)
            except Exception:
                pass
            raise
