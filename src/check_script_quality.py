#!/usr/bin/env python3
"""Script quality checker - validates generated scripts."""

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
from src.quality.manifest import ScriptEntry
from src.pipeline import config as pipeline_config

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ScriptQualityChecker(BaseQualityChecker):
    """Checks quality of generated scripts."""

    def __init__(self, disable_gates: bool = False, max_workers: int = None):
        """Initialize the script quality checker."""
        if max_workers is None:
            max_workers = int(os.getenv('SCRIPT_WORKERS', '1'))
        # Define schema_path before base init because base calls _setup_gates()
        self.schema_path = pipeline_config.CONFIG_DIR / "schemas" / "script_v1.json"
        super().__init__(
            artifact_type='scripts',
            disable_gates=disable_gates,
            max_workers=max_workers
        )

        # Script-specific paths (safe after base init)
        self.scripts_dir = pipeline_config.SCRIPTS_OUTPUT_DIR

    def _setup_gates(self):
        """Setup quality gates using factory pattern."""
        if self.disable_gates or not self.quality_config.enabled:
            logger.info("Quality gates disabled")
            return []
        gates = self.gate_factory.create_script_gates(self.schema_path)
        logger.info(f"Initialized {len(gates)} quality gates")
        return gates

    def _load_artifact(self, artifact_path: Path) -> Any:
        """Load a script file and convert to expected JSON structure."""
        json_path = artifact_path.with_suffix('.json')
        if json_path.exists():
            try:
                with open(json_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load JSON file {json_path}, falling back to .txt: {e}")
        with open(artifact_path, 'r', encoding='utf-8') as f:
            content = f.read()
        parts = artifact_path.stem.split('_', 2)
        topic = parts[2] if len(parts) > 2 else "Unknown"
        return {
            "topic": topic,
            "content": content,
            "metadata": {
                "word_count": len(content.split()),
                "model": pipeline_config.DEFAULT_SCRIPT_MODEL,
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
        }

    def _get_artifact_metadata(self, artifact_path: Path, artifact_data: Any) -> Dict:
        """Extract metadata for reporting."""
        word_count = artifact_data.get("metadata", {}).get("word_count", 0)
        topic = artifact_data.get("topic", "Unknown")
        return {
            "word_count": word_count,
            "topic": topic,
            "filename": artifact_path.name
        }

    def _create_manifest_entry(self, artifact_path: Path, results: List[GateResult], overall_status: QualityStatus, metadata: Dict) -> ScriptEntry:
        """Create a ScriptEntry dataclass instance for manifest."""
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
        return ScriptEntry(
            topic=metadata.get("topic", "Unknown"),
            script_id=artifact_path.stem,
            path=str(artifact_path),
            quality_status=overall_status.value,
            ready_for_audio=(overall_status != QualityStatus.FAIL),
            word_count=metadata.get("word_count"),
            timestamp=datetime.utcnow().isoformat() + "Z",
            quality_details=quality_details
        )

    def _update_manifest(self, entry: ScriptEntry):
        """Persist script entry into manifest."""
        self.manifest.add_script(entry)

    def _create_error_entry(self, artifact_path: Path, error: str) -> Dict:
        """Create error entry structure for manifest update."""
        entry = ScriptEntry(
            topic="Unknown",
            script_id=artifact_path.stem,
            path=str(artifact_path),
            quality_status="error",
            ready_for_audio=False,
            word_count=None,
            timestamp=datetime.utcnow().isoformat() + "Z",
            quality_details={"error": error}
        )
        self.manifest.add_script(entry)
        return {
            "script_id": artifact_path.stem,
            "error": error
        }

    def _get_artifact_files(self) -> List[Path]:
        return list(self.scripts_dir.glob("*.txt"))


def main():
    """Main entry point."""
    # Check for DISABLE_GATES environment variable
    disable_gates = os.getenv("DISABLE_GATES", "0") == "1"
    strict_mode = os.getenv("STRICT", "0") == "1"
    max_workers = int(os.getenv("SCRIPT_WORKERS", "1"))

    if disable_gates:
        logger.info("Quality gates are DISABLED (DISABLE_GATES=1)")

    logger.info(f"Using {max_workers} worker(s) for script quality checks")

    try:
        checker = ScriptQualityChecker(
            disable_gates=disable_gates,
            max_workers=max_workers
        )
        summary = checker.check_all()
        failed_count = summary.get("failed", 0)

        if strict_mode and failed_count > 0:
            logger.error(f"STRICT mode: {failed_count} scripts failed critical gates")
            sys.exit(1)
        sys.exit(0)

    except Exception as e:
        logger.error(f"Script quality checker failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
