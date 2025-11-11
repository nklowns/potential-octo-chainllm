from pathlib import Path
import json
import os
from src.utils.config_loader import load_config_file

def test_yaml_profile_merge(tmp_path, monkeypatch):
    yaml_content = """
base:
  feature: true
  limits:
    max_items: 10
    timeout: 5
profiles:
  prod:
    limits:
      timeout: 15
      extra: 99
    feature: false
"""
    cfg = tmp_path / 'quality.yaml'
    cfg.write_text(yaml_content, encoding='utf-8')
    monkeypatch.setenv('PIPELINE_PROFILE', 'prod')
    data = load_config_file(cfg)
    assert data['feature'] is False
    assert data['limits']['max_items'] == 10  # inherited
    assert data['limits']['timeout'] == 15    # overridden
    assert data['limits']['extra'] == 99      # added

