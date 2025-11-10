#!/usr/bin/env python3
"""Audio quality checker - validates generated audio files."""

import json
import logging
import sys
import os
from pathlib import Path
from typing import List, Any, Dict
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.quality.base import QualityStatus, GateResult
from src.quality.base_checker import BaseQualityChecker
from src.quality.manifest import AudioEntry
from src.pipeline import config as pipeline_config

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class AudioQualityChecker(BaseQualityChecker):
    """Checks quality of generated audio files."""

    def __init__(self, disable_gates: bool = False, max_workers: int = None):
        if max_workers is None:
            max_workers = int(os.getenv('AUDIO_WORKERS', '1'))

        super().__init__(
            artifact_type='audio',
            disable_gates=disable_gates,
            max_workers=max_workers
        )

        self.audio_dir = pipeline_config.AUDIO_OUTPUT_DIR
        self.scripts_dir = pipeline_config.SCRIPTS_OUTPUT_DIR

    def _setup_gates(self):
        if self.disable_gates or not self.quality_config.enabled:
            logger.info("Quality gates disabled")
            return []
        gates = self.gate_factory.create_audio_gates()
        logger.info(f"Initialized {len(gates)} quality gates")
        return gates

    def _load_artifact(self, artifact_path: Path) -> Any:
        script_id = artifact_path.stem
        word_count = 0
        script_entry = self.manifest.get_script(script_id)
        if script_entry:
            word_count = script_entry.get("word_count", 0)
        else:
            script_path = self.scripts_dir / f"{script_id}.txt"
            if script_path.exists():
                try:
                    with open(script_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    word_count = len(content.split())
                except Exception:
                    pass
        return {
            "audio_path": artifact_path,
            "word_count": word_count
        }

    def _get_artifact_metadata(self, artifact_path: Path, artifact_data: Any) -> Dict:
        return {
            "word_count": artifact_data.get("word_count", 0),
            "filename": artifact_path.name
        }

    def _create_manifest_entry(self, artifact_path: Path, results: List[GateResult], overall_status: QualityStatus, metadata: Dict) -> AudioEntry:
        quality_details = {
            "gates": [
                {
                    "gate": r.gate_name,
                    "status": r.status.value,
                    "severity": r.severity.value,
                    "message": r.message
                } for r in results
            ]
        }
        return AudioEntry(
            script_id=artifact_path.stem,
            audio_id=artifact_path.stem,
            path=str(artifact_path),
            quality_status=overall_status.value,
            duration=None,  # placeholder, could be filled by audio_format gate later
            timestamp=datetime.utcnow().isoformat() + "Z",
            quality_details=quality_details
        )

    def _update_manifest(self, entry: AudioEntry):
        self.manifest.add_audio(entry)

    def _create_error_entry(self, artifact_path: Path, error: str) -> Dict:
        entry = AudioEntry(
            script_id=artifact_path.stem,
            audio_id=artifact_path.stem,
            path=str(artifact_path),
            quality_status="error",
            duration=None,
            timestamp=datetime.utcnow().isoformat() + "Z",
            quality_details={"error": error}
        )
        self.manifest.add_audio(entry)
        return {
            "audio_id": artifact_path.stem,
            "error": error
        }

    def _get_artifact_files(self) -> List[Path]:
        return list(self.audio_dir.glob("*.wav"))


def main():
    """Main entry point."""
    # Check for DISABLE_GATES environment variable
    disable_gates = os.getenv("DISABLE_GATES", "0") == "1"
    strict_mode = os.getenv("STRICT", "0") == "1"
    max_workers = int(os.getenv("AUDIO_WORKERS", "1"))

    if disable_gates:
        logger.info("Quality gates are DISABLED (DISABLE_GATES=1)")

    logger.info(f"Using {max_workers} worker(s) for audio quality checks")

    try:
        checker = AudioQualityChecker(
            disable_gates=disable_gates,
            max_workers=max_workers
        )
        summary = checker.check_all()
        failed_count = summary.get("failed", 0)
        if strict_mode and failed_count > 0:
            logger.error(f"STRICT mode: {failed_count} audio files failed critical gates")
            sys.exit(1)
        sys.exit(0)

    except Exception as e:
        logger.error(f"Audio quality checker failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
