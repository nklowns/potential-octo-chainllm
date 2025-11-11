from __future__ import annotations

import logging
from pathlib import Path
import hashlib
from typing import List, Dict
import time

from src.application.services.voice_registry import VoiceRegistry
from src.infrastructure.tts.piper_provider import PiperProvider
from src.domain.tts_models import TTSRequest, ProsodyOptions
from src.utils.script_sanitizer import extract_narration, list_visual_cues, parse_control_tags
from src.pipeline import config

logger = logging.getLogger(__name__)


class AudioOrchestrator:
    def __init__(self, registry: VoiceRegistry | None = None, providers: Dict[str, object] | None = None, metrics_dir: Path | None = None):
        self.registry = registry or VoiceRegistry()
        # Se o chamador fornece providers explicitamente, usamos somente eles (sem defaults implícitos).
        if providers is not None:
            self._providers = providers
        else:
            # Descobre quais backends estão presentes entre as vozes e instancia apenas os necessários,
            # usando a API explícita do registro (used_backends) para evitar ambiguidades.
            discovered_backends = set(self.registry.used_backends())
            base_providers: Dict[str, object] = {}
            if 'piper' in discovered_backends:
                try:
                    base_providers['piper'] = PiperProvider()
                except Exception as e:
                    logger.warning(f"Falha ao inicializar PiperProvider: {e}")
            # Espaço futuro para outros backends (ex: 'mock', 'coqui'). Mock é geralmente injetado em testes.
            self._providers = base_providers
        self._metrics_dir = metrics_dir or (config.OUTPUT_DIR / 'metrics')

    def _select_provider(self, backend: str):
        provider = self._providers.get(backend)
        if not provider:
            raise RuntimeError(f"Backend '{backend}' não suportado.")
        return provider

    def process_script_file(self, path: Path):
        script_name = path.stem
        try:
            raw = path.read_text(encoding='utf-8')
        except Exception as e:
            logger.error(f"Falha ao ler {path}: {e}")
            return

        narration = extract_narration(raw)
        if not narration.strip():
            logger.info(f"{script_name}: sem conteúdo narrável.")
            return

        tags = parse_control_tags(raw)
        prosody = ProsodyOptions()
        pace = tags.get('pace')
        if pace == 'rapido' or pace == 'rápido':
            prosody.pace = 0.85
        elif pace == 'lento':
            prosody.pace = 1.15
        prosody.tone = tags.get('tone')

        voices = self.registry.voices()
        if not voices:
            logger.warning("Nenhuma voz disponível no VoiceRegistry. Abortando geração de áudio.")
            return
        aliases = list(voices.keys())
        dv = self.registry.default_voice()
        if dv and dv in aliases:
            # Move default para frente
            aliases = [dv] + [a for a in aliases if a != dv]

        # cues
        cues = list_visual_cues(raw)
        for alias in aliases:
            cues_dir = config.IMAGES_OUTPUT_DIR / 'cues'
            cues_dir.mkdir(parents=True, exist_ok=True)
            (cues_dir / f"{script_name}_visual_cues.txt").write_text('\n'.join(cues), encoding='utf-8')

        text_blocks: List[str] = narration.split('\n')

        for alias in aliases:
            info = voices.get(alias) or {"backend": "piper", "model_id": alias, "params": {}}
            backend = info.get('backend', 'piper')
            model_id = info.get('model_id', alias)
            params = info.get('params', {})
            provider = self._select_provider(backend)
            request = TTSRequest(
                text_blocks=text_blocks,
                voice_alias=alias,
                backend=backend,
                model_id=model_id,
                params=params,
                prosody=prosody,
            )
            try:
                # Cache key
                hasher = hashlib.sha256()
                hasher.update("\n".join(text_blocks).encode('utf-8'))
                hasher.update(alias.encode('utf-8'))
                hasher.update(backend.encode('utf-8'))
                hasher.update(str(sorted(params.items())).encode('utf-8'))
                cache_key = hasher.hexdigest()
                cache_dir = config.AUDIO_OUTPUT_DIR / 'cache'
                cache_dir.mkdir(parents=True, exist_ok=True)
                cache_wav = cache_dir / f"{cache_key}.wav"

                if cache_wav.exists():
                    # Cache hit
                    audio_bytes = cache_wav.read_bytes()
                    result = type('R', (), {'audio_bytes': audio_bytes, 'meta': {'cache_hit': True, 'chars': len("\n".join(text_blocks))}})()
                    try:
                        from src.utils.metrics_exporter import update_cache_metric
                        update_cache_metric(self._metrics_dir, 'segment', True)
                    except Exception:  # pragma: no cover
                        pass
                else:
                    # Cache miss - gerar áudio
                    t0 = time.time()
                    result = provider.synthesize(request)
                    dt_ms = int((time.time() - t0) * 1000)
                    cache_wav.write_bytes(result.audio_bytes)
                    try:
                        from src.utils.metrics_exporter import update_cache_metric, update_tts_metrics
                        update_cache_metric(self._metrics_dir, 'segment', False)
                        update_tts_metrics(self._metrics_dir, backend=backend, voice=alias, status='ok', chars=result.meta.get('chars', 0), duration_ms=dt_ms)
                    except Exception:  # pragma: no cover
                        pass
                out_path = config.AUDIO_OUTPUT_DIR / f"{script_name}__{alias}.wav"
                out_path.write_bytes(result.audio_bytes)
                logger.info(f"Áudio salvo: {out_path}")
                # Atualiza tamanho do cache
                try:
                    from src.utils.metrics_exporter import update_cache_sizes
                    total_entries = len(list((config.AUDIO_OUTPUT_DIR / 'cache').glob('*.wav')))
                    update_cache_sizes(self._metrics_dir, meta_count=0, segment_count=total_entries)
                except Exception:  # pragma: no cover
                    pass
            except Exception as e:
                logger.error(f"Falha ao gerar áudio para {alias}: {e}")
                try:
                    from src.utils.metrics_exporter import update_tts_metrics
                    update_tts_metrics(self._metrics_dir, backend=backend, voice=alias, status='error', chars=0, duration_ms=0)
                except Exception:  # pragma: no cover
                    pass

    def run(self):
        config.ensure_dirs()
        # Usa apenas .txt como fonte da verdade para áudio
        script_files = [p for p in config.SCRIPTS_OUTPUT_DIR.glob('script_*.txt') if not p.name.endswith('_visual_cues.txt')]
        if not script_files:
            logger.info("Nenhum script para processar.")
            return
        for p in script_files:
            self.process_script_file(p)
