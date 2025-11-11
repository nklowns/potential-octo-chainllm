"""Audio quality gates."""

import logging
from pathlib import Path
from typing import Dict, Any, Optional

from ..base import QualityGate, QualityStatus, Severity, GateResult
from src.utils.audio_cache import audio_cache

logger = logging.getLogger(__name__)


def _extract_audio_path(artifact: Any) -> Optional[Path]:
    """Best-effort extraction of an audio Path from different artifact shapes.

    Supports:
    - pathlib.Path
    - str (file path)
    - dict with keys: 'audio_path', 'path', 'file_path', 'filepath'
    Values for these keys can be Path or str.
    """
    # Direct Path
    if isinstance(artifact, Path):
        return artifact
    # String path
    if isinstance(artifact, str):
        return Path(artifact)
    # Dict-like
    if isinstance(artifact, dict):
        for key in ("audio_path", "path", "file_path", "filepath"):
            if key in artifact and artifact[key]:
                value = artifact[key]
                if isinstance(value, Path):
                    return value
                if isinstance(value, str):
                    return Path(value)
    return None


class AudioFormatGate(QualityGate):
    """Validates audio file format and basic properties."""
    GATE_NAME = "audio_format"

    def __init__(self, min_sample_rate: int = 16000, severity: Severity = Severity.ERROR):
        super().__init__(AudioFormatGate.GATE_NAME, severity)
        self.min_sample_rate = min_sample_rate

    def check(self, artifact: Any) -> GateResult:
        """
        Check if audio file has valid format.

        Args:
            artifact: Path/dict/str referencing the audio file.
        """
        # Resolve audio path from artifact
        audio_path = _extract_audio_path(artifact)

        if not audio_path or not audio_path.exists():
            return self._create_result(
                QualityStatus.FAIL,
                f"Audio file not found: {audio_path or artifact}",
                {"path": str(audio_path or artifact), "code": "Q_ERR_AUDIO_NOT_FOUND"}
            )

        try:
            meta = audio_cache.get_metadata(audio_path)
            if not meta:
                return self._create_result(
                    QualityStatus.FAIL,
                    "Unable to read audio metadata",
                    {"path": str(audio_path), "code": "Q_ERR_AUDIO_META"}
                )

            # Validate sample rate
            if meta['sample_rate'] < self.min_sample_rate:
                return self._create_result(
                    QualityStatus.FAIL,
                    f"Sample rate too low: {meta['sample_rate']}Hz (minimum: {self.min_sample_rate}Hz)",
                    {
                        "sample_rate": meta['sample_rate'],
                        "min_sample_rate": self.min_sample_rate,
                        "channels": meta['channels'],
                        "duration": meta['duration'],
                        "format": meta.get('format'),
                        "code": "Q_ERR_SR_TOO_LOW"
                    }
                )

            # Validate channels (1-2)
            if meta['channels'] < 1 or meta['channels'] > 2:
                return self._create_result(
                    QualityStatus.FAIL,
                    f"Invalid channel count: {meta['channels']} (expected: 1-2)",
                    {
                        "channels": meta['channels'],
                        "sample_rate": meta['sample_rate'],
                        "duration": meta['duration'],
                        "code": "Q_ERR_BAD_CHANNELS"
                    }
                )

            # Validate duration
            if meta['duration'] <= 0:
                return self._create_result(
                    QualityStatus.FAIL,
                    f"Invalid duration: {meta['duration']}s",
                    {
                        "duration": meta['duration'],
                        "sample_rate": meta['sample_rate'],
                        "channels": meta['channels'],
                        "code": "Q_ERR_BAD_DURATION"
                    }
                )

            return self._create_result(
                QualityStatus.PASS,
                f"Audio format valid: {meta['sample_rate']}Hz, {meta['channels']}ch, {meta['duration']:.2f}s",
                {
                    "sample_rate": meta['sample_rate'],
                    "channels": meta['channels'],
                    "duration": round(meta['duration'], 2),
                    "frames": meta.get('frames'),
                    "format": meta.get('format'),
                    "subtype": meta.get('subtype'),
                    "code": "Q_PASS_AUDIO_FORMAT"
                }
            )

        except Exception as e:
            logger.error(f"Error reading audio file {audio_path}: {e}")
            return self._create_result(
                QualityStatus.FAIL,
                f"Failed to read audio file: {str(e)}",
                {"path": str(audio_path), "error": str(e), "code": "Q_ERR_AUDIO_IO"}
            )


class DurationConsistencyGate(QualityGate):
    """Validates audio duration is consistent with script word count."""
    GATE_NAME = "duration_consistency"

    def __init__(self, severity: Severity = Severity.ERROR):
        super().__init__(DurationConsistencyGate.GATE_NAME, severity)
        # Typical reading speed: 2-3 words per second
        # We'll be lenient: 1-5 words per second
        self.min_words_per_second = 1.0
        self.max_words_per_second = 5.0

    def check(self, artifact: Any) -> GateResult:
        """
        Check if audio duration is consistent with word count.

        Args:
            artifact: Dict with 'audio_path' (Path) and 'word_count' (int),
                      or a Path/str (word_count assumed unknown).
        """
        # Extract audio_path regardless of input shape
        audio_path = _extract_audio_path(artifact)
        # Extract word_count if dict, otherwise assume 0 (unknown)
        word_count = artifact.get('word_count', 0) if isinstance(artifact, dict) else 0

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
            meta = audio_cache.get_metadata(audio_path)
            if not meta:
                return self._create_result(
                    QualityStatus.FAIL,
                    "Unable to read audio metadata",
                    {"path": str(audio_path), "code": "Q_ERR_AUDIO_META"}
                )
            duration = meta['duration']

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

        except Exception as e:
            logger.error(f"Error checking duration consistency: {e}")
            return self._create_result(
                QualityStatus.FAIL,
                f"Failed to check duration: {str(e)}",
                {"error": str(e), "code": "Q_ERR_DURATION_CHECK"}
            )


class SilenceDetectionGate(QualityGate):
    """
    Detects excessive silence at the beginning, end, or throughout the audio.

    Uses amplitude-based detection to identify silent regions.
    """
    GATE_NAME = "silence_detection"

    def __init__(
        self,
        max_leading_silence_ms: int = 1000,
        max_trailing_silence_ms: int = 1000,
        max_silence_proportion: float = 0.3,
        silence_threshold_db: float = -40.0,
        severity: Severity = Severity.WARN
    ):
        super().__init__(SilenceDetectionGate.GATE_NAME, severity)
        self.max_leading_silence_ms = max_leading_silence_ms
        self.max_trailing_silence_ms = max_trailing_silence_ms
        self.max_silence_proportion = max_silence_proportion
        self.silence_threshold_db = silence_threshold_db

    def check(self, artifact: Any) -> GateResult:
        """
        Check for excessive silence in audio file.

        Args:
            artifact: Path/dict/str referencing the audio file.
        """
        try:
            from pydub.silence import detect_leading_silence
        except ImportError:
            logger.warning("pydub library not installed. Install with: pip install pydub")
            return self._create_result(
                QualityStatus.WARN,
                "pydub library not available, skipping silence detection",
                {"error": "ImportError: pydub", "code": "Q_WARN_PYDUB_IMPORT"}
            )
        # Resolve audio path from artifact
        audio_path = _extract_audio_path(artifact)

        if not audio_path or not audio_path.exists():
            return self._create_result(
                QualityStatus.FAIL,
                f"Audio file not found: {audio_path or artifact}",
                {"path": str(audio_path or artifact), "code": "Q_ERR_AUDIO_NOT_FOUND"}
            )

        try:
            # Load audio via cache
            audio = audio_cache.get_segment(audio_path)
            if audio is None:
                return self._create_result(
                    QualityStatus.WARN,
                    "Unable to decode audio segment, skipping silence detection",
                    {"path": str(audio_path), "code": "Q_WARN_SEGMENT_MISSING"}
                )

            # Detect leading silence
            leading_silence = detect_leading_silence(
                audio,
                silence_threshold=self.silence_threshold_db
            )

            # Detect trailing silence (reverse audio)
            trailing_silence = detect_leading_silence(
                audio.reverse(),
                silence_threshold=self.silence_threshold_db
            )

            # Calculate silence proportion
            total_duration = len(audio)
            total_silence = leading_silence + trailing_silence
            silence_proportion = total_silence / total_duration if total_duration > 0 else 0

            # Check leading silence
            if leading_silence > self.max_leading_silence_ms:
                return self._create_result(
                    QualityStatus.WARN,
                    f"Excessive leading silence: {leading_silence}ms (max: {self.max_leading_silence_ms}ms)",
                    {
                        "leading_silence_ms": leading_silence,
                        "trailing_silence_ms": trailing_silence,
                        "silence_proportion": round(silence_proportion, 3),
                        "max_leading_ms": self.max_leading_silence_ms,
                        "max_trailing_ms": self.max_trailing_silence_ms,
                        "max_proportion": self.max_silence_proportion
                    }
                )

            # Check trailing silence
            if trailing_silence > self.max_trailing_silence_ms:
                return self._create_result(
                    QualityStatus.WARN,
                    f"Excessive trailing silence: {trailing_silence}ms (max: {self.max_trailing_silence_ms}ms)",
                    {
                        "leading_silence_ms": leading_silence,
                        "trailing_silence_ms": trailing_silence,
                        "silence_proportion": round(silence_proportion, 3),
                        "max_leading_ms": self.max_leading_silence_ms,
                        "max_trailing_ms": self.max_trailing_silence_ms,
                        "max_proportion": self.max_silence_proportion
                    }
                )

            # Check overall silence proportion
            if silence_proportion > self.max_silence_proportion:
                return self._create_result(
                    QualityStatus.WARN,
                    f"Excessive silence proportion: {silence_proportion:.1%} (max: {self.max_silence_proportion:.1%})",
                    {
                        "leading_silence_ms": leading_silence,
                        "trailing_silence_ms": trailing_silence,
                        "silence_proportion": round(silence_proportion, 3),
                        "max_proportion": self.max_silence_proportion
                    }
                )

            return self._create_result(
                QualityStatus.PASS,
                f"Silence within limits: {leading_silence}ms leading, {trailing_silence}ms trailing",
                {
                    "leading_silence_ms": leading_silence,
                    "trailing_silence_ms": trailing_silence,
                    "silence_proportion": round(silence_proportion, 3),
                    "duration_ms": total_duration
                }
            )

        except Exception as e:
            logger.error(f"Error detecting silence in {audio_path}: {e}")
            return self._create_result(
                QualityStatus.WARN,
                f"Failed to detect silence: {str(e)}",
                {"path": str(audio_path), "error": str(e), "code": "Q_WARN_SILENCE_CHECK"}
            )


class LoudnessCheckGate(QualityGate):
    """
    Checks if audio loudness is within acceptable range.

    Uses RMS (root mean square) to measure perceived loudness.
    """
    GATE_NAME = "loudness_check"

    def __init__(
        self,
        target_loudness_dbfs_min: float = -30.0,
        target_loudness_dbfs_max: float = -10.0,
        severity: Severity = Severity.WARN
    ):
        super().__init__(LoudnessCheckGate.GATE_NAME, severity)
        # pydub é usado no método check; aqui apenas guardamos thresholds
        self.target_loudness_dbfs_min = target_loudness_dbfs_min
        self.target_loudness_dbfs_max = target_loudness_dbfs_max

    def check(self, artifact: Any) -> GateResult:
        """
        Check if audio loudness is within acceptable range.

        Args:
            artifact: Path/dict/str referencing the audio file.
        """
        try:
            from pydub import AudioSegment
        except ImportError:
            logger.warning("pydub library not installed. Install with: pip install pydub")
            return self._create_result(
                QualityStatus.WARN,
                "pydub library not available, skipping loudness check",
                {"error": "ImportError: pydub", "code": "Q_WARN_PYDUB_IMPORT"}
            )
        # Resolve audio path from artifact
        audio_path = _extract_audio_path(artifact)

        if not audio_path or not audio_path.exists():
            return self._create_result(
                QualityStatus.FAIL,
                f"Audio file not found: {audio_path or artifact}",
                {"path": str(audio_path or artifact), "code": "Q_ERR_AUDIO_NOT_FOUND"}
            )

        try:
            audio = audio_cache.get_segment(audio_path)
            if audio is None:
                return self._create_result(
                    QualityStatus.WARN,
                    "Unable to decode audio segment, skipping loudness check",
                    {"path": str(audio_path), "code": "Q_WARN_SEGMENT_MISSING"}
                )

            # Get loudness in dBFS (decibels relative to full scale)
            loudness_dbfs = audio.dBFS

            # Check if too quiet
            if loudness_dbfs < self.target_loudness_dbfs_min:
                return self._create_result(
                    QualityStatus.WARN,
                    f"Audio too quiet: {loudness_dbfs:.1f} dBFS (min: {self.target_loudness_dbfs_min} dBFS)",
                    {
                        "loudness_dbfs": round(loudness_dbfs, 2),
                        "target_min_dbfs": self.target_loudness_dbfs_min,
                        "target_max_dbfs": self.target_loudness_dbfs_max
                    }
                )

            # Check if too loud
            if loudness_dbfs > self.target_loudness_dbfs_max:
                return self._create_result(
                    QualityStatus.WARN,
                    f"Audio too loud: {loudness_dbfs:.1f} dBFS (max: {self.target_loudness_dbfs_max} dBFS)",
                    {
                        "loudness_dbfs": round(loudness_dbfs, 2),
                        "target_min_dbfs": self.target_loudness_dbfs_min,
                        "target_max_dbfs": self.target_loudness_dbfs_max
                    }
                )

            return self._create_result(
                QualityStatus.PASS,
                f"Loudness within range: {loudness_dbfs:.1f} dBFS",
                {
                    "loudness_dbfs": round(loudness_dbfs, 2),
                    "target_min_dbfs": self.target_loudness_dbfs_min,
                    "target_max_dbfs": self.target_loudness_dbfs_max,
                    "code": "Q_PASS_LOUDNESS"
                }
            )

        except Exception as e:
            logger.error(f"Error checking loudness in {audio_path}: {e}")
            return self._create_result(
                QualityStatus.WARN,
                f"Failed to check loudness: {str(e)}",
                {"path": str(audio_path), "error": str(e), "code": "Q_WARN_LOUDNESS_CHECK"}
            )
