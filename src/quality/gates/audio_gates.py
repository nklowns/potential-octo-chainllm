"""Audio quality gates."""

import logging
from pathlib import Path
from typing import Dict, Any

from ..base import QualityGate, QualityStatus, Severity, GateResult

logger = logging.getLogger(__name__)


class AudioFormatGate(QualityGate):
    """Validates audio file format and basic properties."""
    
    def __init__(self, min_sample_rate: int = 16000, severity: Severity = Severity.ERROR):
        super().__init__("audio_format", severity)
        self.min_sample_rate = min_sample_rate
    
    def check(self, artifact: Path) -> GateResult:
        """
        Check if audio file has valid format.
        
        Args:
            artifact: Path to the audio file.
        """
        try:
            import soundfile as sf
        except ImportError:
            logger.error("soundfile library not installed. Install with: pip install soundfile")
            return self._create_result(
                QualityStatus.FAIL,
                "soundfile library not available",
                {"error": "ImportError: soundfile"}
            )
        
        if not artifact.exists():
            return self._create_result(
                QualityStatus.FAIL,
                f"Audio file not found: {artifact}",
                {"path": str(artifact)}
            )
        
        try:
            # Read audio file metadata
            info = sf.info(artifact)
            
            # Validate sample rate
            if info.samplerate < self.min_sample_rate:
                return self._create_result(
                    QualityStatus.FAIL,
                    f"Sample rate too low: {info.samplerate}Hz (minimum: {self.min_sample_rate}Hz)",
                    {
                        "sample_rate": info.samplerate,
                        "min_sample_rate": self.min_sample_rate,
                        "channels": info.channels,
                        "duration": info.duration,
                        "format": info.format
                    }
                )
            
            # Validate channels (1-2)
            if info.channels < 1 or info.channels > 2:
                return self._create_result(
                    QualityStatus.FAIL,
                    f"Invalid channel count: {info.channels} (expected: 1-2)",
                    {
                        "channels": info.channels,
                        "sample_rate": info.samplerate,
                        "duration": info.duration
                    }
                )
            
            # Validate duration
            if info.duration <= 0:
                return self._create_result(
                    QualityStatus.FAIL,
                    f"Invalid duration: {info.duration}s",
                    {
                        "duration": info.duration,
                        "sample_rate": info.samplerate,
                        "channels": info.channels
                    }
                )
            
            return self._create_result(
                QualityStatus.PASS,
                f"Audio format valid: {info.samplerate}Hz, {info.channels}ch, {info.duration:.2f}s",
                {
                    "sample_rate": info.samplerate,
                    "channels": info.channels,
                    "duration": round(info.duration, 2),
                    "frames": info.frames,
                    "format": info.format,
                    "subtype": info.subtype
                }
            )
            
        except Exception as e:
            logger.error(f"Error reading audio file {artifact}: {e}")
            return self._create_result(
                QualityStatus.FAIL,
                f"Failed to read audio file: {str(e)}",
                {"path": str(artifact), "error": str(e)}
            )


class DurationConsistencyGate(QualityGate):
    """Validates audio duration is consistent with script word count."""
    
    def __init__(self, severity: Severity = Severity.ERROR):
        super().__init__("duration_consistency", severity)
        # Typical reading speed: 2-3 words per second
        # We'll be lenient: 1-5 words per second
        self.min_words_per_second = 1.0
        self.max_words_per_second = 5.0
    
    def check(self, artifact: Dict[str, Any]) -> GateResult:
        """
        Check if audio duration is consistent with word count.
        
        Args:
            artifact: Dict with 'audio_path' (Path) and 'word_count' (int).
        """
        audio_path = artifact.get('audio_path')
        word_count = artifact.get('word_count', 0)
        
        if not audio_path or not isinstance(audio_path, Path):
            return self._create_result(
                QualityStatus.FAIL,
                "Audio path not provided",
                {}
            )
        
        if word_count <= 0:
            return self._create_result(
                QualityStatus.WARN,
                "Word count not available, cannot verify duration consistency",
                {}
            )
        
        try:
            import soundfile as sf
            info = sf.info(audio_path)
            duration = info.duration
            
            # Calculate words per second
            words_per_second = word_count / duration if duration > 0 else 0
            
            if words_per_second < self.min_words_per_second:
                return self._create_result(
                    QualityStatus.FAIL,
                    f"Audio too slow: {words_per_second:.2f} words/sec (minimum: {self.min_words_per_second})",
                    {
                        "words_per_second": round(words_per_second, 2),
                        "duration": round(duration, 2),
                        "word_count": word_count,
                        "min_wps": self.min_words_per_second,
                        "max_wps": self.max_words_per_second
                    }
                )
            
            if words_per_second > self.max_words_per_second:
                return self._create_result(
                    QualityStatus.FAIL,
                    f"Audio too fast: {words_per_second:.2f} words/sec (maximum: {self.max_words_per_second})",
                    {
                        "words_per_second": round(words_per_second, 2),
                        "duration": round(duration, 2),
                        "word_count": word_count,
                        "min_wps": self.min_words_per_second,
                        "max_wps": self.max_words_per_second
                    }
                )
            
            return self._create_result(
                QualityStatus.PASS,
                f"Duration consistent: {words_per_second:.2f} words/sec",
                {
                    "words_per_second": round(words_per_second, 2),
                    "duration": round(duration, 2),
                    "word_count": word_count
                }
            )
            
        except ImportError:
            return self._create_result(
                QualityStatus.FAIL,
                "soundfile library not available",
                {"error": "ImportError: soundfile"}
            )
        except Exception as e:
            logger.error(f"Error checking duration consistency: {e}")
            return self._create_result(
                QualityStatus.FAIL,
                f"Failed to check duration: {str(e)}",
                {"error": str(e)}
            )
