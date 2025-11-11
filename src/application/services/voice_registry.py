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
        self._validate_consistency()

    def _validate_consistency(self):
        """Validações consistentes porém pragmáticas:
        - default_voice deve existir dentro de available_voices
        - cada voz deve possuir backend e model_id
        - se available_backends existir, cada backend referenciado por uma voz deve estar declarado
        - params conhecidos (length_scale, noise_scale, noise_w_scale) devem ser numéricos, se presentes
        """
        voices = self._data.get('available_voices', {}) or {}
        dv = self._data.get('default_voice')
        if dv is not None and voices and dv not in voices:
            raise ValueError(f"default_voice '{dv}' não encontrado em available_voices")

        for alias, info in voices.items():
            if not isinstance(info, dict):
                raise ValueError(f"Voz '{alias}' inválida: esperado objeto")
            backend = info.get('backend')
            model_id = info.get('model_id')
            if not backend or not isinstance(backend, str):
                raise ValueError(f"Voz '{alias}' sem backend válido")
            if not model_id or not isinstance(model_id, str):
                raise ValueError(f"Voz '{alias}' sem model_id válido")
            # Se available_backends existe, validar referência
            if 'available_backends' in self._data:
                ab = self._data.get('available_backends') or {}
                if backend not in ab:
                    raise ValueError(f"Voz '{alias}' referencia backend '{backend}' não declarado em available_backends")
            # Validar params numéricos conhecidos (se existirem)
            params = info.get('params') or {}
            if not isinstance(params, dict):
                raise ValueError(f"Voz '{alias}' possui params inválidos (esperado objeto)")
            for k in ('length_scale', 'noise_scale', 'noise_w_scale'):
                if k in params and params[k] is not None:
                    try:
                        float(params[k])
                    except Exception:
                        raise ValueError(f"Voz '{alias}' param '{k}' deve ser numérico")

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

    def used_backends(self):
        """Retorna lista ordenada dos backends realmente REFERENCIADOS pelas vozes.

        Diferença em relação a available_backends():
        - used_backends(): derivado de available_voices.*.backend (estado real de uso)
        - available_backends(): bloco declarativo de configuração (pode conter backends ainda não usados ou
          faltar algum se mal configurado — o que será pego nas validações de consistência).
        """
        return sorted({v.get('backend', 'piper') for v in self.voices().values()})

    def available_backends(self) -> Dict[str, Any]:
        """Retorna o bloco cru de configuração 'available_backends' do voices.json.

        NÃO confundir com used_backends(), que representa o subconjunto efetivamente em uso.
        """
        return self._data.get('available_backends', {})
