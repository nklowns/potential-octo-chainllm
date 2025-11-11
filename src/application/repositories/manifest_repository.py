"""Manifest repository abstraction and adapter for RunManifest."""

from __future__ import annotations

from typing import Protocol, List, Dict, Any
from pathlib import Path

from src.domain.entities import Script, AudioArtifact, QualityGateOutcome
from src.quality.manifest import RunManifest, ScriptEntry, AudioEntry


class ManifestRepository(Protocol):
    def snapshot_config(self, config: Dict[str, Any], source_path: str | None = None) -> str: ...
    def add_script(self, script: Script, quality_status: str, ready_for_audio: bool, gate_outcomes: List[QualityGateOutcome]) -> None: ...
    def add_audio(self, audio: AudioArtifact, quality_status: str, gate_outcomes: List[QualityGateOutcome]) -> None: ...
    def get_scripts_ready_for_audio(self) -> List[Dict[str, Any]]: ...
    def get_failed_scripts(self) -> List[Dict[str, Any]]: ...
    def get_failed_audio(self) -> List[Dict[str, Any]]: ...
    def to_dict(self) -> Dict[str, Any]: ...


class RunManifestRepository:
    """Adapter turning RunManifest into ManifestRepository interface."""

    def __init__(self, manifest_or_path: Path | RunManifest):
        # Allow passing an existing RunManifest to share state with callers
        if isinstance(manifest_or_path, RunManifest):
            self._manifest = manifest_or_path
        else:
            self._manifest = RunManifest(manifest_or_path)

    def snapshot_config(self, config: Dict[str, Any], source_path: str | None = None) -> str:
        return self._manifest.save_config_snapshot(config, source_path)

    def add_script(self, script: Script, quality_status: str, ready_for_audio: bool, gate_outcomes: List[QualityGateOutcome]) -> None:
        entry = ScriptEntry(
            topic=script.topic,
            script_id=script.script_id,
            path=f"{script.script_id}.txt",
            quality_status=quality_status,
            ready_for_audio=ready_for_audio,
            word_count=script.word_count,
            timestamp=script.created_at,
            quality_details={
                "gates": [
                    {
                        "gate": o.gate_name,
                        "status": o.status,
                        "severity": o.severity,
                        "message": o.message,
                        "duration_ms": o.duration_ms,
                    } for o in gate_outcomes
                ]
            }
        )
        self._manifest.add_script(entry)

    def add_audio(self, audio: AudioArtifact, quality_status: str, gate_outcomes: List[QualityGateOutcome]) -> None:
        entry = AudioEntry(
            script_id=audio.script_id,
            audio_id=audio.audio_id,
            path=audio.path,
            quality_status=quality_status,
            duration=audio.duration,
            timestamp=audio.created_at,
            quality_details={
                "gates": [
                    {
                        "gate": o.gate_name,
                        "status": o.status,
                        "severity": o.severity,
                        "message": o.message,
                        "duration_ms": o.duration_ms,
                    } for o in gate_outcomes
                ]
            }
        )
        self._manifest.add_audio(entry)

    def get_scripts_ready_for_audio(self) -> List[Dict[str, Any]]:
        return self._manifest.get_scripts_ready_for_audio()

    def get_failed_scripts(self) -> List[Dict[str, Any]]:
        return self._manifest.get_failed_scripts()

    def get_failed_audio(self) -> List[Dict[str, Any]]:
        return self._manifest.get_failed_audio()

    def to_dict(self) -> Dict[str, Any]:
        return self._manifest.to_dict()
