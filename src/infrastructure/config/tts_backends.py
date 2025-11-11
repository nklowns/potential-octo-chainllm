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
        # Fonte de verdade única: available_backends em voices.json (v2)
        self.voices_path = voices_path or pipeline_config.VOICES_CONFIG_PATH
        # Mantenha o nome alinhado com a chave real do arquivo para evitar ambiguidades
        self._available_backends: Dict[str, Any] = {}
        self._load()

    def _load(self):
        # Lê voices.json e extrai available_backends. Não há fallback.
        try:
            raw_voices = json.loads(Path(self.voices_path).read_text(encoding='utf-8'))
            if isinstance(raw_voices, dict) and 'available_backends' in raw_voices:
                self._available_backends = raw_voices.get('available_backends', {}) or {}
            else:
                self._available_backends = {}
        except Exception:
            # Em caso de erro de leitura/parse, mantém estrutura vazia; consumidores decidem como proceder
            self._available_backends = {}
        # Sem fallbacks: se vazio, mantém estrutura vazia; consumidores decidem como proceder

    def get_backend(self, name: str) -> TTSBackend | None:
        cfg = self._available_backends.get(name)
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

    def available_backends(self) -> Dict[str, Any]:
        """Retorna o dicionário bruto de available_backends do voices.json."""
        return dict(self._available_backends)

    def list_backends(self) -> list[str]:
        """Lista os nomes de backends disponíveis no voices.json (chave available_backends)."""
        return sorted(self._available_backends.keys())
