import json
from pathlib import Path

from src.check_script_quality import ScriptQualityChecker
from src.pipeline import config as pipeline_config


def test_config_snapshot_created(tmp_path, monkeypatch):
    # Redirect output and config directories to temporary location
    monkeypatch.setattr(pipeline_config, 'OUTPUT_DIR', tmp_path / 'output')
    monkeypatch.setattr(pipeline_config, 'CONFIG_DIR', Path('config'))  # keep real config for loading
    (pipeline_config.OUTPUT_DIR / 'quality_gates').mkdir(parents=True)

    checker = ScriptQualityChecker(disable_gates=True)
    manifest = checker.manifest.to_dict()

    assert manifest.get('config_hash'), 'config_hash should be set in manifest'
    snapshot_path = manifest.get('config_snapshot_path')
    assert snapshot_path, 'config_snapshot_path should be recorded'
    snapshot_file = Path(snapshot_path)
    assert snapshot_file.exists(), 'Snapshot file should exist on disk'
    data = json.loads(snapshot_file.read_text(encoding='utf-8'))
    assert isinstance(data, dict), 'Snapshot content should be a dict'
    # Hash should match content
    from src.quality.manifest import compute_config_hash
    assert compute_config_hash(data) == manifest['config_hash']
