from pathlib import Path
import json

from src.quality.gates.script_gates import WordBoundsGate
from src.quality.base import Severity, QualityStatus


def test_gate_result_has_code():
    gate = WordBoundsGate(min_words=1, max_words=5, severity=Severity.ERROR)
    artifact = {
        "topic": "t",
        "content": "a b c",
        "metadata": {"model": "m", "timestamp": "2024-01-01T00:00:00Z"}
    }
    result = gate.check(artifact)
    assert 'code' in result.details


def test_metrics_file_written(tmp_path, monkeypatch):
    # Simular summary reporter escrevendo metrics
    from src.quality.reporters.quality_reporter import SummaryReporter

    # Cria dummy reports
    reports_dir = tmp_path / 'reports'
    reports_dir.mkdir(parents=True)
    script_report = reports_dir / 'scripts'
    audio_report = reports_dir / 'audio'
    script_report.mkdir()
    audio_report.mkdir()

    # Example minimal gate result file
    sample = {
        "artifact_id": "x",
        "artifact_type": "scripts",
        "artifact_path": "x.txt",
        "timestamp": "2024-01-01T00:00:00Z",
        "quality": {"processed": True, "status": "pass", "gates_run": 1, "gates_passed": 1, "gates_failed": 0, "gates_warned": 0, "gates_skipped": 0},
        "gate_results": [
            {"gate_name": "word_bounds", "status": "pass", "severity": "error", "message": "ok", "details": {"metrics": {"duration_ms": 5}}}
        ],
        "metadata": {}
    }
    with open(script_report / 'x.json', 'w', encoding='utf-8') as f:
        json.dump(sample, f)

    summary_path = reports_dir / 'summary.json'
    reporter = SummaryReporter(summary_path)
    reporter.generate_summary([script_report / 'x.json'], [])

    metrics_dir = summary_path.parent / 'metrics'
    metrics_file = metrics_dir / 'metrics.prom'
    assert metrics_file.exists(), 'metrics.prom should exist'
    text = metrics_file.read_text()
    assert 'quality_gate_runs_total' in text
    assert 'quality_gate_duration_ms' in text
