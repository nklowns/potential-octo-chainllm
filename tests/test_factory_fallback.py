from pathlib import Path

from src.quality.factory import GateFactory
from src.quality.gates.audio_gates import SilenceDetectionGate


class DummyConfig:
    def __init__(self):
        self._enabled = True
        self._llm = False
        self._severity = {
            'silence_detection': 'warn'
        }
        self._audio = {}
        self._script = {}
        # Use a name that is not explicitly handled in factory to force fallback
        self._ordering = {
            'script': [],
            'audio': ['silence_detection']
        }

    @property
    def enabled(self):
        return self._enabled

    @property
    def llm_assisted(self):
        return self._llm

    @property
    def script_config(self):
        return self._script

    @property
    def audio_config(self):
        return self._audio

    @property
    def script_gate_order(self):
        return list(self._ordering['script'])

    @property
    def audio_gate_order(self):
        return list(self._ordering['audio'])

    def get_severity(self, gate_name: str, default: str = 'error') -> str:
        return self._severity.get(gate_name, default)


def test_factory_fallback_dynamic_registry(tmp_path):
    cfg = DummyConfig()
    factory = GateFactory(cfg, base_dir=tmp_path)

    gates = factory.create_audio_gates()

    # Should have instantiated SilenceDetectionGate via dynamic discovery
    assert any(isinstance(g, SilenceDetectionGate) for g in gates), 'Expected SilenceDetectionGate from fallback'
    sd = next(g for g in gates if isinstance(g, SilenceDetectionGate))
    assert getattr(sd, 'name', None) == SilenceDetectionGate.GATE_NAME
