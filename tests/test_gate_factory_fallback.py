from pathlib import Path
from src.quality.factory import GateFactory
from src.quality.config import QualityConfig
from src.pipeline import config as pipeline_config

# Create a minimal fake config dict for dynamic gate ordering

import json

def test_gate_factory_dynamic_fallback(tmp_path, monkeypatch):
    # Create a temporary JSON quality config with an unknown gate that should trigger discovery
    cfg_path = tmp_path / 'quality.json'
    cfg_json = {
        'enabled': True,
        'script': {},
        'audio': {},
        'severity': {
            'audio_format': 'error'
        },
        'ordering': {
            'script': [],
            'audio': ['audio_format']
        }
    }
    cfg_path.write_text(json.dumps(cfg_json), encoding='utf-8')
    monkeypatch.setattr(pipeline_config, 'CONFIG_DIR', tmp_path)
    qc = QualityConfig(cfg_path)
    factory = GateFactory(qc, pipeline_config.BASE_DIR)
    audio_gates = factory.create_audio_gates()
    assert any(g.name == 'audio_format' for g in audio_gates)
