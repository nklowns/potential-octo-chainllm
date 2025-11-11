from pathlib import Path
import json

from src.application.orchestrators.audio_orchestrator import AudioOrchestrator
from src.application.services.voice_registry import VoiceRegistry
from src.infrastructure.tts.mock_provider import MockProvider
from src.pipeline import config


def write_voice_config(tmp_path: Path):
    voices_cfg = {
        "version": 2,
        "default_voice": "mock_voice",
        "available_voices": {
            "mock_voice": {"backend": "mock", "model_id": "mock_model", "params": {}}
        }
    }
    cfg_path = tmp_path / 'voices.json'
    cfg_path.write_text(json.dumps(voices_cfg), encoding='utf-8')
    return cfg_path


def write_script(tmp_path: Path, name: str, content: str):
    (tmp_path / name).write_text(content, encoding='utf-8')


def test_orchestrator_uses_default_voice(tmp_path, monkeypatch):
    # Isola diretórios
    monkeypatch.setattr(config, 'SCRIPTS_OUTPUT_DIR', tmp_path)
    monkeypatch.setattr(config, 'AUDIO_OUTPUT_DIR', tmp_path / 'audio')
    monkeypatch.setattr(config, 'OUTPUT_DIR', tmp_path)
    monkeypatch.setattr(config, 'VOICES_CONFIG_PATH', write_voice_config(tmp_path))

    config.ensure_dirs()

    # Roteiro com duas falas
    write_script(tmp_path, 'script_001_test.txt', '"Ola"\n"Mundo"')

    registry = VoiceRegistry(path=config.VOICES_CONFIG_PATH)
    orchestrator = AudioOrchestrator(registry=registry, providers={'mock': MockProvider()}, metrics_dir=tmp_path / 'metrics')
    orchestrator.run()

    # Verifica arquivo de áudio criado
    outputs = list((tmp_path / 'audio').glob('*__mock_voice.wav'))
    assert len(outputs) == 1, 'Áudio não foi gerado com a voz default mock_voice'

    # Verifica métrica de síntese
    metrics_file = (tmp_path / 'metrics' / 'tts_metrics.prom')
    assert metrics_file.exists()
    content = metrics_file.read_text(encoding='utf-8')
    assert 'tts_synth_total{backend="mock",voice="mock_voice",status="ok"} 1' in content


def test_orchestrator_cache_hit(tmp_path, monkeypatch):
    from src.utils.metrics_exporter import reset_all_metrics
    reset_all_metrics()
    monkeypatch.setattr(config, 'SCRIPTS_OUTPUT_DIR', tmp_path)
    monkeypatch.setattr(config, 'AUDIO_OUTPUT_DIR', tmp_path / 'audio')
    monkeypatch.setattr(config, 'OUTPUT_DIR', tmp_path)
    monkeypatch.setattr(config, 'VOICES_CONFIG_PATH', write_voice_config(tmp_path))

    config.ensure_dirs()
    write_script(tmp_path, 'script_001_cache.txt', '"Cache Test"')

    registry = VoiceRegistry(path=config.VOICES_CONFIG_PATH)
    orchestrator = AudioOrchestrator(registry=registry, providers={'mock': MockProvider()}, metrics_dir=tmp_path / 'metrics')
    orchestrator.run()  # miss
    orchestrator.run()  # hit

    cache_metrics = (tmp_path / 'metrics' / 'cache_metrics.prom').read_text(encoding='utf-8')
    assert 'audio_cache_hits_total{kind="segment"} 1' in cache_metrics
    # Esperado: 1 miss (primeira síntese), 1 hit (segunda) para kind=segment
    assert 'audio_cache_misses_total{kind="segment"} 1' in cache_metrics
