"""Gate factory - centralized gate creation based on configuration."""

from pathlib import Path
from typing import List

from .base import QualityGate, Severity
from .config import QualityConfig
from .gates.script_gates import (
    SchemaValidationGate,
    WordBoundsGate,
    ForbiddenTermsGate,
    LanguageGate,
    ScriptCompletenessGate,
    DuplicateScriptGate
)
from .gates.audio_gates import (
    AudioFormatGate,
    DurationConsistencyGate,
    SilenceDetectionGate,
    LoudnessCheckGate
)
from .gates.loader import discover_gates


class GateFactory:
    """Factory for creating quality gates based on configuration."""

    def __init__(self, quality_config: QualityConfig, base_dir: Path):
        """
        Initialize the factory.

        Args:
            quality_config: Quality configuration
            base_dir: Base directory for resolving relative paths
        """
        self.config = quality_config
        self.base_dir = base_dir

    def create_script_gates(self, schema_path: Path) -> List[QualityGate]:
        """
        Create script quality gates based on configuration.

        Args:
            schema_path: Path to JSON schema file

        Returns:
            List of configured quality gates
        """
        if not self.config.enabled:
            return []

        gates = []
        script_config = self.config.script_config

        discovered = discover_gates()  # Built-in + future plugins
        for gate_name in self.config.script_gate_order:
            severity_str = self.config.get_severity(gate_name)
            severity = Severity.ERROR if severity_str == "error" else Severity.WARN

            if gate_name == "schema_validation":
                gates.append(SchemaValidationGate(schema_path, severity))

            elif gate_name == "word_bounds":
                gates.append(WordBoundsGate(
                    script_config.get("min_words", 10),
                    script_config.get("max_words", 2000),
                    severity
                ))

            elif gate_name == "forbidden_terms":
                forbidden_file = script_config.get("forbidden_terms_file")
                if forbidden_file:
                    forbidden_path = self.base_dir / forbidden_file
                    gates.append(ForbiddenTermsGate(
                        forbidden_terms_file=forbidden_path,
                        severity=severity
                    ))
                else:
                    gates.append(ForbiddenTermsGate(
                        forbidden_terms=script_config.get("forbidden_terms", []),
                        severity=severity
                    ))

            elif gate_name == "language":
                gates.append(LanguageGate(
                    script_config.get("language", "pt-BR"),
                    severity
                ))

            elif gate_name == "script_completeness":
                gates.append(ScriptCompletenessGate(
                    llm_assisted=self.config.llm_assisted,
                    severity=severity
                ))
            elif gate_name == "duplicates":
                # Index path under output/quality_gates
                index_path = self.base_dir / 'data' / 'output' / 'quality_gates' / 'indexes' / 'scripts_hash_index.json'
                index_path.parent.mkdir(parents=True, exist_ok=True)
                allow_dup = script_config.get('allow_duplicates', False)
                gates.append(DuplicateScriptGate(index_path=index_path, allow_duplicates=allow_dup, severity=severity))
            else:
                # Attempt dynamic discovery (plugin/custom gate)
                cls = discovered.get(gate_name)
                if cls:
                    try:
                        # Try common constructor patterns (severity first)
                        gate_obj = None
                        for pattern in (
                            lambda: cls(severity=severity),
                            lambda: cls(severity),
                            lambda: cls()
                        ):
                            try:
                                gate_obj = pattern()
                                break
                            except Exception:
                                continue
                        if gate_obj:
                            gates.append(gate_obj)
                        else:
                            raise RuntimeError(f"Could not instantiate gate '{gate_name}' via known patterns")
                    except Exception:
                        # Silently skip unknown gate for now (could log warning)
                        import logging
                        logging.getLogger(__name__).warning(f"Failed to dynamically load gate '{gate_name}'")

        return gates

    def create_audio_gates(self) -> List[QualityGate]:
        """
        Create audio quality gates based on configuration.

        Returns:
            List of configured quality gates
        """
        if not self.config.enabled:
            return []

        gates = []
        audio_config = self.config.audio_config

        discovered = discover_gates()
        for gate_name in self.config.audio_gate_order:
            severity_str = self.config.get_severity(gate_name)
            severity = Severity.ERROR if severity_str == "error" else Severity.WARN

            if gate_name == "audio_format":
                gates.append(AudioFormatGate(
                    audio_config.get("min_sample_rate", 16000),
                    severity
                ))

            elif gate_name == "duration_consistency":
                gates.append(DurationConsistencyGate(severity))

            elif gate_name == "silence":
                gates.append(SilenceDetectionGate(
                    max_leading_silence_ms=audio_config.get("max_leading_silence_ms", 1000),
                    max_trailing_silence_ms=audio_config.get("max_trailing_silence_ms", 1000),
                    max_silence_proportion=audio_config.get("max_silence_proportion", 0.3),
                    severity=severity
                ))

            elif gate_name == "loudness":
                gates.append(LoudnessCheckGate(
                    target_loudness_dbfs_min=audio_config.get("target_loudness_dbfs_min", -30.0),
                    target_loudness_dbfs_max=audio_config.get("target_loudness_dbfs_max", -10.0),
                    severity=severity
                ))
            else:
                cls = discovered.get(gate_name)
                if cls:
                    try:
                        gate_obj = None
                        for pattern in (
                            lambda: cls(severity=severity),
                            lambda: cls(severity),
                            lambda: cls()
                        ):
                            try:
                                gate_obj = pattern()
                                break
                            except Exception:
                                continue
                        if gate_obj:
                            gates.append(gate_obj)
                    except Exception:
                        import logging
                        logging.getLogger(__name__).warning(f"Failed to dynamically load audio gate '{gate_name}'")

        return gates
