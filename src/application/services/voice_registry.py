from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Any

from src.pipeline import config


class VoiceRegistry:
    def __init__(self, path: Path | None = None):
        self.path = path or config.VOICES_CONFIG_PATH
        self._data: Dict[str, Any] = {}
        self._schema_path = config.CONFIG_DIR / 'schemas' / 'voices_config_v2.json'
        self._load()

    def _validate_v2(self, data: Dict[str, Any]) -> bool:
        try:
            from jsonschema import Draft7Validator  # type: ignore
        except Exception:
            # jsonschema não instalado no ambiente do editor: pular validação
            return True

        try:
            with open(self._schema_path, 'r', encoding='utf-8') as f:
                schema = json.load(f)
            Draft7Validator(schema).validate(data)
            return True
        except (FileNotFoundError, json.JSONDecodeError):
            # Sem schema, seguimos adiante (modo permissivo)
            return True
        except Exception as e:
            # Invalida
            raise ValueError(f"voices.json inválido segundo schema v2: {e}")

    def _load(self):
        try:
            with open(self.path, 'r', encoding='utf-8') as f:
                raw = json.load(f)
        except FileNotFoundError:
            raw = {"version": 1, "available_voices": {}}
        except json.JSONDecodeError:
            raw = {"version": 1, "available_voices": {}}

        version = int(raw.get('version', 0))
        if version != 2:
            # Somente modelo v2 é aceito para manter simples
            self._data = {"version": 2, "available_voices": {}}
            return
        self._validate_v2(raw)
        self._data = raw

    def reload(self):
        self._load()

    def version(self) -> int:
        return int(self._data.get("version", 2))

    def default_voice(self) -> str | None:
        dv = self._data.get("default_voice")
        voices = self.voices()
        if dv and dv in voices:
            return dv
        # fallback para a primeira voz disponível, se houver
        if voices:
            try:
                return next(iter(voices.keys()))
            except Exception:
                pass
        return None

    def voices(self) -> Dict[str, Dict]:
        return self._data.get("available_voices", {})

    def get(self, alias: str) -> Dict | None:
        return self.voices().get(alias)

    def list_aliases(self):
        return list(self.voices().keys())

    def backends(self):
        return sorted({v.get('available_backends', 'piper') for v in self.voices().values()})
