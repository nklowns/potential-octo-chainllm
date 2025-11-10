"""Configuration loader for quality gates."""

import json
import logging
from pathlib import Path
from typing import Dict, Any

# Optional import with clear error if missing during validation
try:
    import jsonschema
    from jsonschema import Draft7Validator
except Exception:  # jsonschema is in requirements, but keep lazy import safety
    jsonschema = None
    Draft7Validator = None

logger = logging.getLogger(__name__)


class QualityConfig:
    """Loads and provides access to quality gate configuration."""

    def __init__(self, config_path: Path):
        """Load quality configuration from JSON file."""
        self.config_path = config_path
        self._config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file."""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            logger.info(f"Loaded quality config from {self.config_path}")
            # Validate against schema if available
            try:
                schema_path = self.config_path.parent / 'schemas' / 'quality_config_v1.json'
                if schema_path.exists():
                    if jsonschema is None or Draft7Validator is None:
                        logger.error("jsonschema library not installed. Install with: pip install jsonschema")
                        raise RuntimeError("jsonschema not available for config validation")
                    with open(schema_path, 'r', encoding='utf-8') as sf:
                        schema = json.load(sf)
                    validator = Draft7Validator(schema)
                    errors = sorted(validator.iter_errors(config), key=lambda e: e.path)
                    if errors:
                        msgs = [f"{list(e.path)}: {e.message}" for e in errors]
                        pretty = "\n  - ".join(msgs)
                        raise ValueError(
                            f"Quality config invalid per schema {schema_path}:\n  - {pretty}"
                        )
                    # Additional logical checks
                    script = config.get('script', {})
                    if script.get('max_words') is not None and script.get('min_words') is not None:
                        if script['max_words'] < script['min_words']:
                            raise ValueError("script.max_words must be >= script.min_words")
                else:
                    logger.warning(f"Quality config schema not found at {schema_path}; skipping validation")
            except Exception as ve:
                logger.error(f"Quality config validation failed: {ve}")
                raise
            return config
        except FileNotFoundError:
            logger.error(f"Quality config not found at {self.config_path}")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in quality config: {e}")
            raise

    @property
    def enabled(self) -> bool:
        """Check if quality gates are enabled."""
        return self._config.get('enabled', True)

    @property
    def llm_assisted(self) -> bool:
        """Check if LLM-assisted gates are enabled."""
        return self._config.get('llm_assisted', False)

    @property
    def script_config(self) -> Dict[str, Any]:
        """Get script quality gate configuration."""
        return self._config.get('script', {})

    @property
    def audio_config(self) -> Dict[str, Any]:
        """Get audio quality gate configuration."""
        return self._config.get('audio', {})

    @property
    def severity_map(self) -> Dict[str, str]:
        """Get severity mapping for gates."""
        return self._config.get('severity', {})

    @property
    def script_gate_order(self) -> list:
        """Get ordered list of script gates to run."""
        return self._config.get('ordering', {}).get('script', [])

    @property
    def audio_gate_order(self) -> list:
        """Get ordered list of audio gates to run."""
        return self._config.get('ordering', {}).get('audio', [])

    def get_severity(self, gate_name: str, default: str = 'error') -> str:
        """Get severity level for a specific gate."""
        return self.severity_map.get(gate_name, default)
