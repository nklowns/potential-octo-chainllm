from pathlib import Path
from src.utils.metrics_exporter import update_http_metrics

def test_update_http_metrics(tmp_path):
    metrics_dir = tmp_path / 'metrics'
    path = update_http_metrics(metrics_dir, service='tts', method='GET', status=200, duration_ms=123)
    assert path.exists()
    text = path.read_text(encoding='utf-8')
    assert 'pipeline_http_requests_total' in text
    assert 'service="tts"' in text
    assert 'method="GET"' in text
    assert 'status="200"' in text
    # Duration sum and count style lines should exist
    assert 'pipeline_http_request_duration_ms_sum' in text
    assert 'pipeline_http_request_duration_ms_count' in text
