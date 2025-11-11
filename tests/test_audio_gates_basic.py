from pathlib import Path
import wave
import struct
import numpy as np
import soundfile as sf

from src.quality.gates.audio_gates import AudioFormatGate, DurationConsistencyGate
from src.quality.base import Severity, QualityStatus


def _write_silence_wav(path: Path, seconds=1.0, sr=16000):
    n = int(seconds * sr)
    data = np.zeros((n,), dtype=np.float32)
    sf.write(str(path), data, sr)


def _write_sine_wav(path: Path, seconds: float = 0.5, freq: float = 440.0, rate: int = 16000):
    import math
    frames = int(seconds * rate)
    with wave.open(str(path), 'w') as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        for i in range(frames):
            val = int(32767 * 0.1 * math.sin(2 * math.pi * freq * i / rate))
            w.writeframes(struct.pack('<h', val))


def test_audio_format_and_duration(tmp_path):
    wav = tmp_path / 'silence.wav'
    _write_silence_wav(wav, seconds=1.0, sr=16000)

    fmt_gate = AudioFormatGate(min_sample_rate=8000, severity=Severity.ERROR)
    res = fmt_gate.check(str(wav))
    assert res.status in (QualityStatus.PASS, QualityStatus.WARN)

    dur_gate = DurationConsistencyGate(severity=Severity.ERROR)
    res2 = dur_gate.check({'audio_path': wav, 'word_count': 2})
    assert res2.status == QualityStatus.PASS


def test_audio_format_gate_tone(tmp_path):
    audio_path = tmp_path / 'tone.wav'
    _write_sine_wav(audio_path)
    gate = AudioFormatGate(min_sample_rate=16000, severity=Severity.ERROR)
    result = gate.check({'audio_path': audio_path})
    assert result.status.value == 'pass'
    assert result.details.get('sample_rate') == 16000
