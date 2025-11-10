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


def update_http_metrics(metrics_dir: Path, service: str, method: str, status: str | int, duration_ms: int, run_id: Optional[str] = None):
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
