#!/usr/bin/env python3
"""Script quality checker - validates generated scripts."""

import json
import logging
import sys
import os
from pathlib import Path
from typing import List, Any, Dict

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.quality.base import QualityStatus
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
        # Get max workers from environment or parameter
        if max_workers is None:
            max_workers = int(os.getenv('SCRIPT_WORKERS', '1'))
        
        super().__init__(
            artifact_type='scripts',
            disable_gates=disable_gates,
            max_workers=max_workers
        )
        
        # Script-specific paths
        self.scripts_dir = pipeline_config.SCRIPTS_OUTPUT_DIR
        self.schema_path = pipeline_config.CONFIG_DIR / "schemas" / "script_v1.json"
        self.manifest_path = pipeline_config.OUTPUT_DIR / "quality_gates" / "run_manifest.json"
        
        # Initialize manifest and reporter
        self.manifest = RunManifest(self.manifest_path)
        self.reporter = QualityReporter(self.reports_dir, self.quarantine_dir)
        
    
    def _setup_gates(self):
        """Setup quality gates using factory pattern."""
        if self.disable_gates or not self.quality_config.enabled:
            logger.info("Quality gates disabled")
            return []
        
        # Use factory to create script gates
        gates = self.gate_factory.create_script_gates(self.schema_path)
        logger.info(f"Initialized {len(gates)} quality gates")
        return gates
    
    def _load_artifact(self, artifact_path: Path) -> Any:
        """
        Load a script file and convert to the expected JSON structure.
        
        Prefers .json files if available, otherwise loads .txt and constructs JSON.
        """
        # Check if JSON version exists
        json_path = artifact_path.with_suffix('.json')
        if json_path.exists():
            try:
                with open(json_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load JSON file {json_path}, falling back to .txt: {e}")
        
        # Fallback to .txt file
        with open(artifact_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Extract topic from filename (format: script_XXX_topic.txt)
        parts = artifact_path.stem.split('_', 2)
        topic = parts[2] if len(parts) > 2 else "Unknown"
        
        # Create JSON structure matching schema
        return {
            "topic": topic,
            "content": content,
            "metadata": {
                "word_count": len(content.split())
            }
        }
    
    def _create_manifest_entry(self, artifact_path: Path, results: List, overall_status: QualityStatus, metadata: Dict) -> Dict:
        """Create manifest entry for a script."""
        return ScriptEntry(
            script_id=artifact_path.stem,
            script_path=str(artifact_path),
            status=overall_status,
            gates_passed=[r.gate_name for r in results if r.passed],
            gates_failed=[r.gate_name for r in results if not r.passed],
            metadata=metadata
        ).to_dict()
    
    def _get_artifact_files(self) -> List[Path]:
        """Get list of script files to check."""
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
        failed_count = checker.check_all_artifacts()
        
        # In strict mode, exit with non-zero if there were failures
        if strict_mode and failed_count > 0:
            logger.error(f"STRICT mode: {failed_count} scripts failed critical gates")
            sys.exit(1)
        else:
            sys.exit(0)
            
    except Exception as e:
        logger.error(f"Script quality checker failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
