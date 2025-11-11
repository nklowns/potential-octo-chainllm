from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict
from pathlib import Path

from src.pipeline import config as pipeline_config


@dataclass(frozen=True)
class BackendDefaults:
    length_scale: float = 1.0
    noise_scale: float = 0.667
    noise_w_scale: float = 0.8


@dataclass(frozen=True)
class TTSBackend:
    name: str
    base_url: str
    defaults: BackendDefaults


class TTSBackendsConfig:
    def __init__(self, path: Path | None = None, voices_path: Path | None = None):
        # Fonte de verdade: available_backends em voices.json (v2)
        self.voices_path = voices_path or pipeline_config.VOICES_CONFIG_PATH
        # "path" legado ignorado por design (sem fallback para tts_backends.json)
        self._data: Dict[str, Any] = {"backends": {}}
        self._load()

    def _load(self):
        # Lê voices.json e extrai available_backends (ou 'backends' se presente para compat interna)
        try:
            raw_voices = json.loads(Path(self.voices_path).read_text(encoding='utf-8'))
            if isinstance(raw_voices, dict):
                if 'available_backends' in raw_voices:
                    self._data['backends'] = raw_voices.get('available_backends', {})
                elif 'backends' in raw_voices:
                    # Compatibilidade limitada: aceita 'backends' mas preferir available_backends
                    self._data['backends'] = raw_voices.get('backends', {})
        except Exception:
            pass
        # Sem fallbacks: se vazio, mantém estrutura vazia; consumidores decidem como proceder

    def get_backend(self, name: str) -> TTSBackend | None:
        cfg = self._data.get('backends', {}).get(name)
        if not cfg:
            return None
        defaults = cfg.get('defaults', {})
        return TTSBackend(
            name=name,
            base_url=str(cfg.get('base_url', '')),
            defaults=BackendDefaults(
                length_scale=float(defaults.get('length_scale', 1.0)),
                noise_scale=float(defaults.get('noise_scale', 0.667)),
                noise_w_scale=float(defaults.get('noise_w_scale', 0.8)),
            ),
        )
