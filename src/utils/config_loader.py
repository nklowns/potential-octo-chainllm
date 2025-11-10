"""Config loader with optional YAML support and profiles.

Supports two layouts for YAML files:
- Flat dict (no profiles): loaded as-is.
- With base/profiles: { base: {...}, profiles: { dev: {...}, prod: {...} } }

Merging strategy: base deep-merged with selected profile (shallow for simple dicts).
Profile is selected via env PIPELINE_PROFILE or argument.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict

try:
    import yaml  # type: ignore
except Exception:
    yaml = None  # Optional dependency


def _deep_merge(a: Dict[str, Any], b: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(a)
    for k, v in b.items():
        if k in out and isinstance(out[k], dict) and isinstance(v, dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def load_config_file(path: Path, profile: str | None = None) -> Dict[str, Any]:
    """Load YAML/JSON config. If YAML and has profiles, merge base+selected profile.

    Args:
        path: Path to YAML or JSON file.
        profile: Optional profile name. Defaults to env PIPELINE_PROFILE or 'dev'.
    """
    profile = profile or os.getenv("PIPELINE_PROFILE", "dev")
    suffix = path.suffix.lower()

    # JSON path: load via json from caller to avoid dependency; here we only handle YAML
    if suffix not in (".yml", ".yaml"):
        raise ValueError("load_config_file only supports YAML files. For JSON, load with json library.")

    if yaml is None:
        raise RuntimeError("pyyaml not installed; cannot load YAML config.")

    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    if not isinstance(data, dict):
        return {}

    if "base" in data or "profiles" in data:
        base = data.get("base", {})
        profiles = data.get("profiles", {})
        selected = profiles.get(profile, {}) if isinstance(profiles, dict) else {}
        if not selected and profiles:
            # fallback to any single profile if provided but not found
            try:
                first_key = next(iter(profiles))
                selected = profiles.get(first_key, {})
            except Exception:
                selected = {}
        return _deep_merge(base if isinstance(base, dict) else {}, selected if isinstance(selected, dict) else {})

    return data
