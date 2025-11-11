"""Metrics sink abstraction (initial pass-through)."""

from __future__ import annotations

from typing import Dict, Any, Optional
from pathlib import Path

from src.utils.metrics_exporter import update_http_metrics


class MetricsSink:
    def __init__(self, base_dir: Path):
        self._dir = base_dir / 'quality_gates' / 'metrics'

    def http_request(self, service: str, method: str, status_code: int, duration_ms: int, run_id: Optional[str] = None):
        update_http_metrics(self._dir, service=service, method=method, status=status_code, duration_ms=duration_ms, run_id=run_id)

    # Placeholder methods for future histogram/counter usage
    def gate_duration(self, gate: str, duration_ms: int, status: str, artifact_type: str, run_id: Optional[str] = None):
        # Could merge into existing exporter lazily later
        pass

    def increment(self, name: str, labels: Dict[str, Any]):
        pass
