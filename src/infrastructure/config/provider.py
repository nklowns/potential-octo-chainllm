"""Unified configuration provider aggregating quality + pipeline env settings."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict
from pathlib import Path

from src.pipeline import config as pipeline_config
from src.quality.config import QualityConfig


@dataclass(frozen=True)
class PipelineConfigView:
    quality_enabled: bool
    llm_assisted: bool
    script_min_words: int
    script_max_words: int
    audio_min_sample_rate: int
    tts_base_url: str
    ollama_base_url: str
    script_workers: int
    audio_workers: int
    raw_quality: Dict[str, Any]


class ConfigProvider:
    def __init__(self, quality_config_path: Path):
        self._quality = QualityConfig(quality_config_path)

    def load(self) -> PipelineConfigView:
        qc = self._quality
        script_cfg = qc.script_config
        audio_cfg = qc.audio_config
        return PipelineConfigView(
            quality_enabled=qc.enabled,
            llm_assisted=qc.llm_assisted,
            script_min_words=script_cfg.get('min_words', 10),
            script_max_words=script_cfg.get('max_words', 2000),
            audio_min_sample_rate=audio_cfg.get('min_sample_rate', 16000),
            tts_base_url=pipeline_config.TTS_SERVER_URL,
            ollama_base_url=pipeline_config.OLLAMA_BASE_URL,
            script_workers=int(pipeline_config.__dict__.get('SCRIPT_WORKERS', 1)) if hasattr(pipeline_config, 'SCRIPT_WORKERS') else 1,
            audio_workers=int(pipeline_config.__dict__.get('AUDIO_WORKERS', 1)) if hasattr(pipeline_config, 'AUDIO_WORKERS') else 1,
            raw_quality=qc.to_dict()
        )
