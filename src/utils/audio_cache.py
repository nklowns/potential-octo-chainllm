"""Simple in-memory cache for audio metadata and decoded segment to reduce repeated IO.

Design:
  - Metadata (samplerate, channels, duration, frames, format, subtype) via soundfile.info()
  - Segment (pydub AudioSegment) loaded lazily only if requested.
  - Thread-safe dictionary with size limit to avoid memory blow-up.
  - No persistence; recreated per process.
"""

import threading
from pathlib import Path
from typing import Optional, Dict, Any
from src.pipeline import config as pipeline_config
from src.utils.metrics_exporter import update_cache_metric, update_cache_sizes

class _AudioCache:
    def __init__(self, max_entries: int = 512):
        self._meta: Dict[str, Dict[str, Any]] = {}
        self._segment: Dict[str, Any] = {}
        self._lock = threading.Lock()
        self.max_entries = max_entries

    def _evict_if_needed(self, store: Dict[str, Any]):
        if len(store) > self.max_entries:
            # FIFO eviction: remove first key
            first_key = next(iter(store.keys()))
            store.pop(first_key, None)

    def get_metadata(self, path: Path) -> Optional[Dict[str, Any]]:
        key = str(path)
        with self._lock:
            if key in self._meta:
                # hit
                try:
                    update_cache_metric(pipeline_config.OUTPUT_DIR / 'quality_gates' / 'metrics', 'meta', True)
                except Exception:
                    pass
                return self._meta[key]
        # Load outside lock to reduce contention
        try:
            import soundfile as sf
            info = sf.info(path)
            data = {
                "sample_rate": info.samplerate,
                "channels": info.channels,
                "duration": info.duration,
                "frames": info.frames,
                "format": info.format,
                "subtype": info.subtype,
            }
        except Exception:
            try:
                update_cache_metric(pipeline_config.OUTPUT_DIR / 'quality_gates' / 'metrics', 'meta', False)
            except Exception:
                pass
            return None
        with self._lock:
            self._meta[key] = data
            self._evict_if_needed(self._meta)
            # update sizes
            try:
                update_cache_sizes(pipeline_config.OUTPUT_DIR / 'quality_gates' / 'metrics', len(self._meta), len(self._segment))
            except Exception:
                pass
        return data

    def get_segment(self, path: Path) -> Optional[Any]:
        key = str(path)
        with self._lock:
            if key in self._segment:
                try:
                    update_cache_metric(pipeline_config.OUTPUT_DIR / 'quality_gates' / 'metrics', 'segment', True)
                except Exception:
                    pass
                return self._segment[key]
        try:
            from pydub import AudioSegment
            segment = AudioSegment.from_file(path)
        except Exception:
            try:
                update_cache_metric(pipeline_config.OUTPUT_DIR / 'quality_gates' / 'metrics', 'segment', False)
            except Exception:
                pass
            return None
        with self._lock:
            self._segment[key] = segment
            self._evict_if_needed(self._segment)
            try:
                update_cache_sizes(pipeline_config.OUTPUT_DIR / 'quality_gates' / 'metrics', len(self._meta), len(self._segment))
            except Exception:
                pass
        return segment

audio_cache = _AudioCache()