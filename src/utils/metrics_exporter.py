"""Simple Prometheus textfile metrics exporter with label support.

Adds labels: gate, status, artifact_type, run_id when provided.
Backward-compatible: if artifact_type/run_id ausentes, omite labels.
"""

from pathlib import Path
from typing import Dict, Optional
import time
import threading
import tempfile

_lock = threading.Lock()

def _fmt_labels(base: Dict[str, str]) -> str:
    items = [f'{k}="{v}"' for k, v in base.items() if v is not None]
    if not items:
        return ""
    return "{" + ",".join(items) + "}"

def write_metrics(
    metrics_path: Path,
    gate_stats: Dict[str, Dict],
    avg_timings: Dict[str, int],
    run_id: Optional[str] = None,
    artifact_type: Optional[str] = None
):
    metrics_path.parent.mkdir(parents=True, exist_ok=True)
    lines = []
    lines.append('# TYPE quality_gate_runs_total counter')
    lines.append('# TYPE quality_gate_duration_ms gauge')
    for gate, stats in gate_stats.items():
        for status_key in ("pass", "fail", "warn", "skipped"):
            if status_key in stats:
                value = stats.get(status_key, 0)
                label_str = _fmt_labels({
                    "gate": gate,
                    "status": status_key,
                    "artifact_type": artifact_type,
                    "run_id": run_id
                })
                lines.append(f'quality_gate_runs_total{label_str} {value}')
        if gate in avg_timings:
            label_str = _fmt_labels({
                "gate": gate,
                "artifact_type": artifact_type,
                "run_id": run_id
            })
            lines.append(f'quality_gate_duration_ms{label_str} {avg_timings[gate]}')

    content = "\n".join(lines) + "\n"
    with _lock:
        try:
            with tempfile.NamedTemporaryFile('w', encoding='utf-8', delete=False, dir=metrics_path.parent, suffix='.tmp') as tf:
                tf.write(content)
                tmp = tf.name
            Path(tmp).replace(metrics_path)
        except Exception:
            pass

# ------------------------- HTTP metrics -------------------------

_http_lock = threading.Lock()
_http_requests: Dict[str, int] = {}
_http_duration_sum: Dict[str, float] = {}
_http_duration_count: Dict[str, int] = {}


def update_http_metrics(metrics_dir: Path, service: str, method: str, status: str | int, duration_ms: int, run_id: Optional[str] = None) -> Path:
    """Update HTTP metrics counters and write textfile atomically.

    Metrics:
      - pipeline_http_requests_total{service,method,status,run_id}
      - pipeline_http_request_duration_ms_sum{service,method}
      - pipeline_http_request_duration_ms_count{service,method}
    """
    metrics_dir.mkdir(parents=True, exist_ok=True)
    status_str = str(status)
    key_req = f"{service}|{method}|{status_str}|{run_id or ''}"
    key_lat = f"{service}|{method}"
    with _http_lock:
        _http_requests[key_req] = _http_requests.get(key_req, 0) + 1
        _http_duration_sum[key_lat] = _http_duration_sum.get(key_lat, 0.0) + float(duration_ms)
        _http_duration_count[key_lat] = _http_duration_count.get(key_lat, 0) + 1

        # Render
        lines = []
        lines.append('# TYPE pipeline_http_requests_total counter')
        lines.append('# TYPE pipeline_http_request_duration_ms_sum counter')
        lines.append('# TYPE pipeline_http_request_duration_ms_count counter')
        for k, v in _http_requests.items():
            s, m, st, rid = k.split('|', 3)
            label_str = _fmt_labels({"service": s, "method": m, "status": st, "run_id": rid or None})
            lines.append(f'pipeline_http_requests_total{label_str} {v}')
        for k, v in _http_duration_sum.items():
            s, m = k.split('|', 1)
            label_str = _fmt_labels({"service": s, "method": m})
            lines.append(f'pipeline_http_request_duration_ms_sum{label_str} {int(v)}')
        for k, v in _http_duration_count.items():
            s, m = k.split('|', 1)
            label_str = _fmt_labels({"service": s, "method": m})
            lines.append(f'pipeline_http_request_duration_ms_count{label_str} {v}')

        content = "\n".join(lines) + "\n"
        metrics_path = metrics_dir / 'http_metrics.prom'
        try:
            with tempfile.NamedTemporaryFile('w', encoding='utf-8', delete=False, dir=metrics_dir, suffix='.tmp') as tf:
                tf.write(content)
                tmp = tf.name
            Path(tmp).replace(metrics_path)
        except Exception:
            pass
        return metrics_path


# ------------------------- Gate runtime metrics -------------------------
_gate_lock = threading.Lock()
_gate_runs: Dict[str, int] = {}
_gate_duration_sum: Dict[str, float] = {}
_gate_duration_count: Dict[str, int] = {}


def update_gate_runtime(metrics_dir: Path, gate: str, status: str, duration_ms: int,
                        artifact_type: Optional[str] = None, run_id: Optional[str] = None) -> Path:
    """Update gate runtime metrics and write textfile atomically.

    Metrics:
      - quality_gate_runs_total{gate,status,artifact_type,run_id}
      - quality_gate_run_duration_ms_sum{gate,artifact_type}
      - quality_gate_run_duration_ms_count{gate,artifact_type}
    """
    metrics_dir.mkdir(parents=True, exist_ok=True)
    key_req = f"{gate}|{status}|{artifact_type or ''}|{run_id or ''}"
    key_lat = f"{gate}|{artifact_type or ''}"
    with _gate_lock:
        _gate_runs[key_req] = _gate_runs.get(key_req, 0) + 1
        _gate_duration_sum[key_lat] = _gate_duration_sum.get(key_lat, 0.0) + float(duration_ms)
        _gate_duration_count[key_lat] = _gate_duration_count.get(key_lat, 0) + 1

        lines = []
        lines.append('# TYPE quality_gate_runs_total counter')
        lines.append('# TYPE quality_gate_run_duration_ms_sum counter')
        lines.append('# TYPE quality_gate_run_duration_ms_count counter')
        for k, v in _gate_runs.items():
            g, st, art, rid = k.split('|', 3)
            label_str = _fmt_labels({"gate": g, "status": st, "artifact_type": art or None, "run_id": rid or None})
            lines.append(f'quality_gate_runs_total{label_str} {v}')
        for k, v in _gate_duration_sum.items():
            g, art = k.split('|', 1)
            label_str = _fmt_labels({"gate": g, "artifact_type": art or None})
            lines.append(f'quality_gate_run_duration_ms_sum{label_str} {int(v)}')
        for k, v in _gate_duration_count.items():
            g, art = k.split('|', 1)
            label_str = _fmt_labels({"gate": g, "artifact_type": art or None})
            lines.append(f'quality_gate_run_duration_ms_count{label_str} {v}')

        content = "\n".join(lines) + "\n"
        metrics_path = metrics_dir / 'gate_runtime_metrics.prom'
        try:
            with tempfile.NamedTemporaryFile('w', encoding='utf-8', delete=False, dir=metrics_dir, suffix='.tmp') as tf:
                tf.write(content)
                tmp = tf.name
            Path(tmp).replace(metrics_path)
        except Exception:
            pass
        return metrics_path


# ------------------------- Audio cache metrics -------------------------
_cache_lock = threading.Lock()
_cache_hits: Dict[str, int] = {"meta": 0, "segment": 0}
_cache_misses: Dict[str, int] = {"meta": 0, "segment": 0}
_cache_sizes: Dict[str, int] = {"meta": 0, "segment": 0}


def update_cache_metric(metrics_dir: Path, kind: str, hit: bool):
    metrics_dir.mkdir(parents=True, exist_ok=True)
    with _cache_lock:
        if hit:
            _cache_hits[kind] = _cache_hits.get(kind, 0) + 1
        else:
            _cache_misses[kind] = _cache_misses.get(kind, 0) + 1
        _write_cache_metrics(metrics_dir)


def update_cache_sizes(metrics_dir: Path, meta_count: int, segment_count: int):
    with _cache_lock:
        _cache_sizes['meta'] = meta_count
        _cache_sizes['segment'] = segment_count
        _write_cache_metrics(metrics_dir)


def _write_cache_metrics(metrics_dir: Path):
    lines = []
    lines.append('# TYPE audio_cache_hits_total counter')
    lines.append('# TYPE audio_cache_misses_total counter')
    lines.append('# TYPE audio_cache_entries gauge')
    for kind in ("meta", "segment"):
        label = _fmt_labels({"kind": kind})
        lines.append(f'audio_cache_hits_total{label} {_cache_hits.get(kind, 0)}')
        lines.append(f'audio_cache_misses_total{label} {_cache_misses.get(kind, 0)}')
        lines.append(f'audio_cache_entries{label} {_cache_sizes.get(kind, 0)}')
    content = "\n".join(lines) + "\n"
    metrics_path = metrics_dir / 'cache_metrics.prom'
    try:
        with tempfile.NamedTemporaryFile('w', encoding='utf-8', delete=False, dir=metrics_dir, suffix='.tmp') as tf:
            tf.write(content)
            tmp = tf.name
        Path(tmp).replace(metrics_path)
    except Exception:
        pass

# ------------------------- TTS synthesis metrics -------------------------
_tts_lock = threading.Lock()
_tts_counts: Dict[str, int] = {}  # key: backend|voice|status
_tts_chars_sum: Dict[str, int] = {}  # key: backend|voice
_tts_duration_sum: Dict[str, int] = {}  # key: backend|voice
_tts_duration_count: Dict[str, int] = {}  # key: backend|voice

def update_tts_metrics(metrics_dir: Path, backend: str, voice: str, status: str, chars: int, duration_ms: int):
    metrics_dir.mkdir(parents=True, exist_ok=True)
    key_status = f"{backend}|{voice}|{status}"
    key_voice = f"{backend}|{voice}"
    with _tts_lock:
        _tts_counts[key_status] = _tts_counts.get(key_status, 0) + 1
        if status == 'ok':
            _tts_chars_sum[key_voice] = _tts_chars_sum.get(key_voice, 0) + int(chars)
            _tts_duration_sum[key_voice] = _tts_duration_sum.get(key_voice, 0) + int(duration_ms)
            _tts_duration_count[key_voice] = _tts_duration_count.get(key_voice, 0) + 1

        lines = []
        lines.append('# TYPE tts_synth_total counter')
        lines.append('# TYPE tts_synth_chars_sum counter')
        lines.append('# TYPE tts_synth_duration_ms_sum counter')
        lines.append('# TYPE tts_synth_duration_ms_count counter')
        for k, v in _tts_counts.items():
            b, vname, st = k.split('|', 3)
            label = _fmt_labels({"backend": b, "voice": vname, "status": st})
            lines.append(f'tts_synth_total{label} {v}')
        for k, v in _tts_chars_sum.items():
            b, vname = k.split('|', 1)
            label = _fmt_labels({"backend": b, "voice": vname})
            lines.append(f'tts_synth_chars_sum{label} {v}')
        for k, v in _tts_duration_sum.items():
            b, vname = k.split('|', 1)
            label = _fmt_labels({"backend": b, "voice": vname})
            lines.append(f'tts_synth_duration_ms_sum{label} {v}')
        for k, v in _tts_duration_count.items():
            b, vname = k.split('|', 1)
            label = _fmt_labels({"backend": b, "voice": vname})
            lines.append(f'tts_synth_duration_ms_count{label} {v}')
        content = '\n'.join(lines) + '\n'
        metrics_path = metrics_dir / 'tts_metrics.prom'
        try:
            with tempfile.NamedTemporaryFile('w', encoding='utf-8', delete=False, dir=metrics_dir, suffix='.tmp') as tf:
                tf.write(content)
                tmp = tf.name
            Path(tmp).replace(metrics_path)
        except Exception:
            pass


# ------------------------- Test helpers -------------------------
def reset_all_metrics():
    """Reset all in-memory metric counters. Intended for unit tests only."""
    global _http_requests, _http_duration_sum, _http_duration_count
    global _gate_runs, _gate_duration_sum, _gate_duration_count
    global _cache_hits, _cache_misses, _cache_sizes
    global _tts_counts, _tts_chars_sum, _tts_duration_sum, _tts_duration_count

    with _http_lock:
        _http_requests = {}
        _http_duration_sum = {}
        _http_duration_count = {}
    with _gate_lock:
        _gate_runs = {}
        _gate_duration_sum = {}
        _gate_duration_count = {}
    with _cache_lock:
        _cache_hits = {"meta": 0, "segment": 0}
        _cache_misses = {"meta": 0, "segment": 0}
        _cache_sizes = {"meta": 0, "segment": 0}
    with _tts_lock:
        _tts_counts = {}
        _tts_chars_sum = {}
        _tts_duration_sum = {}
        _tts_duration_count = {}
