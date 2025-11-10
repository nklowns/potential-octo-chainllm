"""Dynamic gate discovery loader.

Scans built-in gates package and optional plugins directory for subclasses of QualityGate
with attribute GATE_NAME to enable configuration-driven or automatic registration.
"""

import importlib
import pkgutil
from pathlib import Path
from typing import Dict, Type, List

from ..base import QualityGate


def discover_gates(additional_paths: List[Path] | None = None) -> Dict[str, Type[QualityGate]]:
    registry: Dict[str, Type[QualityGate]] = {}

    # Built-in gates package
    pkg = importlib.import_module(__package__)
    for mod in pkgutil.iter_modules(pkg.__path__):  # type: ignore[attr-defined]
        if mod.name.endswith('_gates'):
            module_name = f"{__package__}.{mod.name}"
            module = importlib.import_module(module_name)
            for attr in dir(module):
                obj = getattr(module, attr)
                if isinstance(obj, type) and issubclass(obj, QualityGate) and obj is not QualityGate:
                    gate_name = getattr(obj, 'GATE_NAME', getattr(obj, 'name', None))
                    if gate_name:
                        registry[gate_name] = obj

    # Plugins
    for p in additional_paths or []:
        if not p.exists():
            continue
        for file in p.glob('**/*.py'):
            rel = file.stem
            if rel.startswith('_'):
                continue
            spec_name = f"plugins.{rel}"  # Expect PYTHONPATH adjusted if using plugins/
            try:
                module = importlib.import_module(spec_name)
            except Exception:
                continue
            for attr in dir(module):
                obj = getattr(module, attr)
                if isinstance(obj, type) and issubclass(obj, QualityGate) and obj is not QualityGate:
                    gate_name = getattr(obj, 'GATE_NAME', getattr(obj, 'name', None))
                    if gate_name and gate_name not in registry:
                        registry[gate_name] = obj

    return registry
