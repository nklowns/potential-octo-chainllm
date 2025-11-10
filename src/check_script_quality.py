#!/usr/bin/env python3
"""Script quality checker - validates generated scripts."""

import json
import logging
import sys
import os
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.quality.base import Severity, QualityStatus
from src.quality.config import QualityConfig
from src.quality.runner import QualityGateRunner
from src.quality.gates.script_gates import (
    SchemaValidationGate,
    WordBoundsGate,
    ForbiddenTermsGate,
    LanguageGate
)
from src.quality.manifest import RunManifest, ScriptEntry
from src.quality.reporters import QualityReporter
from src.pipeline import config as pipeline_config

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ScriptQualityChecker:
    """Checks quality of generated scripts."""
    
    def __init__(self, disable_gates: bool = False):
        """Initialize the checker."""
        self.disable_gates = disable_gates
        
        # Load quality configuration
        quality_config_path = pipeline_config.CONFIG_DIR / "quality.json"
        self.quality_config = QualityConfig(quality_config_path)
        
        # Setup paths with improved structure
        self.scripts_dir = pipeline_config.SCRIPTS_OUTPUT_DIR
        self.schema_path = pipeline_config.CONFIG_DIR / "schemas" / "script_v1.json"
        self.reports_dir = pipeline_config.OUTPUT_DIR / "quality_gates" / "reports" / "scripts"
        self.quarantine_dir = pipeline_config.OUTPUT_DIR / "quality_gates" / "quarantine" / "scripts"
        self.manifest_path = pipeline_config.OUTPUT_DIR / "quality_gates" / "run_manifest.json"
        
        # Initialize manifest and reporter
        self.manifest = RunManifest(self.manifest_path)
        self.reporter = QualityReporter(self.reports_dir, self.quarantine_dir)
        
        # Setup gates
        self.gates = self._setup_gates()
    
    def _setup_gates(self):
        """Setup quality gates based on configuration."""
        if self.disable_gates or not self.quality_config.enabled:
            logger.info("Quality gates disabled")
            return []
        
        gates = []
        script_config = self.quality_config.script_config
        
        # Create gates based on configuration order
        for gate_name in self.quality_config.script_gate_order:
            severity_str = self.quality_config.get_severity(gate_name)
            severity = Severity.ERROR if severity_str == "error" else Severity.WARN
            
            if gate_name == "schema_validation":
                gates.append(SchemaValidationGate(self.schema_path, severity))
            elif gate_name == "word_bounds":
                gates.append(WordBoundsGate(
                    script_config.get("min_words", 10),
                    script_config.get("max_words", 2000),
                    severity
                ))
            elif gate_name == "forbidden_terms":
                # Check if forbidden_terms_file is specified
                forbidden_file = script_config.get("forbidden_terms_file")
                if forbidden_file:
                    forbidden_path = pipeline_config.BASE_DIR / forbidden_file
                    gates.append(ForbiddenTermsGate(
                        forbidden_terms_file=forbidden_path,
                        severity=severity
                    ))
                else:
                    # Fallback to list
                    gates.append(ForbiddenTermsGate(
                        forbidden_terms=script_config.get("forbidden_terms", []),
                        severity=severity
                    ))
            elif gate_name == "language":
                gates.append(LanguageGate(
                    script_config.get("language", "pt-BR"),
                    severity
                ))
        
        logger.info(f"Initialized {len(gates)} quality gates")
        return gates
    
    def _load_script_as_json(self, script_path: Path) -> dict:
        """
        Load a script file and convert to the expected JSON structure.
        
        Prefers .json files if available, otherwise loads .txt and constructs JSON.
        """
        # Check if JSON version exists
        json_path = script_path.with_suffix('.json')
        if json_path.exists():
            try:
                with open(json_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load JSON file {json_path}, falling back to .txt: {e}")
        
        # Fallback to .txt file
        try:
            with open(script_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Extract topic from filename (format: script_XXX_topic.txt)
            parts = script_path.stem.split('_', 2)
            topic = parts[2] if len(parts) > 2 else "Unknown"
            
            # Count words
            word_count = len(content.split())
            
            # Create JSON structure matching schema
            script_json = {
                "topic": topic,
                "content": content,
                "metadata": {
                    "model": "unknown",  # Not stored in .txt file
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "word_count": word_count,
                    "duration_seconds": 0  # Not applicable for quality check
                }
            }
            
            return script_json
            
        except Exception as e:
            logger.error(f"Error loading script {script_path}: {e}")
            raise
    
    def check_script(self, script_path: Path) -> bool:
        """
        Check a single script file.
        
        Returns:
            True if script passed all critical gates, False otherwise.
        """
        script_id = script_path.stem
        logger.info(f"Checking script: {script_id}")
        
        try:
            # Load script
            script_json = self._load_script_as_json(script_path)
            
            # Run quality gates
            if self.gates:
                runner = QualityGateRunner(self.gates, lazy=True)
                results = runner.run(script_json)
                overall_status = runner.get_overall_status(results)
                has_critical_failures = runner.has_critical_failures(results)
            else:
                # No gates, pass through
                results = []
                overall_status = QualityStatus.PASS
                has_critical_failures = False
            
            # Generate report
            self.reporter.generate_report(
                artifact_id=script_id,
                artifact_type="script",
                artifact_path=script_path,
                results=results,
                overall_status=overall_status,
                metadata={
                    "topic": script_json.get("topic"),
                    "word_count": script_json.get("metadata", {}).get("word_count")
                }
            )
            
            # Quarantine if critical failure
            if has_critical_failures:
                self.reporter.quarantine_artifact(
                    script_path,
                    script_id,
                    reason="Critical quality gate failure"
                )
            
            # Update manifest
            ready_for_audio = not has_critical_failures
            self.manifest.add_script(ScriptEntry(
                topic=script_json.get("topic", "Unknown"),
                script_id=script_id,
                path=str(script_path),
                quality_status=overall_status.value,
                ready_for_audio=ready_for_audio,
                word_count=script_json.get("metadata", {}).get("word_count"),
                timestamp=datetime.utcnow().isoformat() + "Z",
                quality_details={
                    "gates_run": len(results),
                    "has_critical_failures": has_critical_failures
                }
            ))
            
            return not has_critical_failures
            
        except Exception as e:
            logger.error(f"Error checking script {script_path}: {e}", exc_info=True)
            # Mark as failed in manifest
            self.manifest.add_script(ScriptEntry(
                topic="Error",
                script_id=script_id,
                path=str(script_path),
                quality_status="fail",
                ready_for_audio=False,
                timestamp=datetime.utcnow().isoformat() + "Z",
                quality_details={"error": str(e)}
            ))
            return False
    
    def check_all(self) -> int:
        """
        Check all scripts in the output directory.
        
        Returns:
            Number of scripts that failed critical gates.
        """
        script_files = list(self.scripts_dir.glob("*.txt"))
        
        if not script_files:
            logger.warning(f"No script files found in {self.scripts_dir}")
            return 0
        
        logger.info(f"Found {len(script_files)} scripts to check")
        
        failed_count = 0
        for script_file in script_files:
            passed = self.check_script(script_file)
            if not passed:
                failed_count += 1
        
        logger.info(f"Script quality check complete: {len(script_files) - failed_count}/{len(script_files)} passed")
        
        return failed_count


def main():
    """Main entry point."""
    # Check for DISABLE_GATES environment variable
    disable_gates = os.getenv("DISABLE_GATES", "0") == "1"
    strict_mode = os.getenv("STRICT", "0") == "1"
    
    if disable_gates:
        logger.info("Quality gates are DISABLED (DISABLE_GATES=1)")
    
    try:
        checker = ScriptQualityChecker(disable_gates=disable_gates)
        failed_count = checker.check_all()
        
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
