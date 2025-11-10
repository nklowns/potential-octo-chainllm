#!/usr/bin/env python3
"""Audio quality checker - validates generated audio files."""

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
from src.quality.gates.audio_gates import (
    AudioFormatGate,
    DurationConsistencyGate
)
from src.quality.manifest import RunManifest, AudioEntry
from src.quality.reporters import QualityReporter
from src.pipeline import config as pipeline_config

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class AudioQualityChecker:
    """Checks quality of generated audio files."""
    
    def __init__(self, disable_gates: bool = False):
        """Initialize the checker."""
        self.disable_gates = disable_gates
        
        # Load quality configuration
        quality_config_path = pipeline_config.CONFIG_DIR / "quality.json"
        self.quality_config = QualityConfig(quality_config_path)
        
        # Setup paths
        self.audio_dir = pipeline_config.AUDIO_OUTPUT_DIR
        self.reports_dir = pipeline_config.OUTPUT_DIR / "reports" / "audio"
        self.quarantine_dir = pipeline_config.OUTPUT_DIR / "quarantine" / "audio"
        self.manifest_path = pipeline_config.OUTPUT_DIR / "run_manifest.json"
        
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
        audio_config = self.quality_config.audio_config
        
        # Create gates based on configuration order
        for gate_name in self.quality_config.audio_gate_order:
            severity_str = self.quality_config.get_severity(gate_name)
            severity = Severity.ERROR if severity_str == "error" else Severity.WARN
            
            if gate_name == "audio_format":
                gates.append(AudioFormatGate(
                    audio_config.get("min_sample_rate", 16000),
                    severity
                ))
            elif gate_name == "duration_consistency":
                gates.append(DurationConsistencyGate(severity))
        
        logger.info(f"Initialized {len(gates)} quality gates")
        return gates
    
    def _get_script_word_count(self, audio_path: Path) -> int:
        """Get word count from corresponding script in manifest."""
        # Audio filename matches script filename (script_XXX_topic.wav)
        script_id = audio_path.stem
        
        script_entry = self.manifest.get_script(script_id)
        if script_entry:
            return script_entry.get("word_count", 0)
        
        # Fallback: try to load from script file directly
        script_path = pipeline_config.SCRIPTS_OUTPUT_DIR / f"{script_id}.txt"
        if script_path.exists():
            try:
                with open(script_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                return len(content.split())
            except:
                pass
        
        return 0
    
    def check_audio(self, audio_path: Path) -> bool:
        """
        Check a single audio file.
        
        Returns:
            True if audio passed all critical gates, False otherwise.
        """
        audio_id = audio_path.stem
        script_id = audio_id  # Same as script
        logger.info(f"Checking audio: {audio_id}")
        
        try:
            # Get word count for duration consistency check
            word_count = self._get_script_word_count(audio_path)
            
            # Run format gate first
            format_results = []
            if self.gates:
                # Run format gate
                format_gates = [g for g in self.gates if isinstance(g, AudioFormatGate)]
                if format_gates:
                    runner = QualityGateRunner(format_gates, lazy=False)
                    format_results = runner.run(audio_path)
                    
                    # If format check failed, skip duration check
                    if runner.has_critical_failures(format_results):
                        results = format_results
                        overall_status = QualityStatus.FAIL
                        has_critical_failures = True
                    else:
                        # Run duration consistency gate
                        duration_gates = [g for g in self.gates if isinstance(g, DurationConsistencyGate)]
                        if duration_gates:
                            artifact_for_duration = {
                                "audio_path": audio_path,
                                "word_count": word_count
                            }
                            duration_runner = QualityGateRunner(duration_gates, lazy=False)
                            duration_results = duration_runner.run(artifact_for_duration)
                            results = format_results + duration_results
                        else:
                            results = format_results
                        
                        # Calculate overall status
                        combined_runner = QualityGateRunner([], lazy=False)
                        overall_status = combined_runner.get_overall_status(results)
                        has_critical_failures = combined_runner.has_critical_failures(results)
                else:
                    results = []
                    overall_status = QualityStatus.PASS
                    has_critical_failures = False
            else:
                # No gates, pass through
                results = []
                overall_status = QualityStatus.PASS
                has_critical_failures = False
            
            # Get audio duration for metadata
            duration = None
            try:
                import soundfile as sf
                info = sf.info(audio_path)
                duration = info.duration
            except:
                pass
            
            # Generate report
            self.reporter.generate_report(
                artifact_id=audio_id,
                artifact_type="audio",
                artifact_path=audio_path,
                results=results,
                overall_status=overall_status,
                metadata={
                    "script_id": script_id,
                    "duration": duration,
                    "word_count": word_count
                }
            )
            
            # Quarantine if critical failure
            if has_critical_failures:
                self.reporter.quarantine_artifact(
                    audio_path,
                    audio_id,
                    reason="Critical quality gate failure"
                )
            
            # Update manifest
            self.manifest.add_audio(AudioEntry(
                script_id=script_id,
                audio_id=audio_id,
                path=str(audio_path),
                quality_status=overall_status.value,
                duration=duration,
                timestamp=datetime.utcnow().isoformat() + "Z",
                quality_details={
                    "gates_run": len(results),
                    "has_critical_failures": has_critical_failures
                }
            ))
            
            return not has_critical_failures
            
        except Exception as e:
            logger.error(f"Error checking audio {audio_path}: {e}", exc_info=True)
            # Mark as failed in manifest
            self.manifest.add_audio(AudioEntry(
                script_id=script_id,
                audio_id=audio_id,
                path=str(audio_path),
                quality_status="fail",
                timestamp=datetime.utcnow().isoformat() + "Z",
                quality_details={"error": str(e)}
            ))
            return False
    
    def check_all(self) -> int:
        """
        Check all audio files in the output directory.
        
        Returns:
            Number of audio files that failed critical gates.
        """
        audio_files = list(self.audio_dir.glob("*.wav"))
        
        if not audio_files:
            logger.warning(f"No audio files found in {self.audio_dir}")
            return 0
        
        logger.info(f"Found {len(audio_files)} audio files to check")
        
        failed_count = 0
        for audio_file in audio_files:
            passed = self.check_audio(audio_file)
            if not passed:
                failed_count += 1
        
        logger.info(f"Audio quality check complete: {len(audio_files) - failed_count}/{len(audio_files)} passed")
        
        return failed_count


def main():
    """Main entry point."""
    # Check for DISABLE_GATES environment variable
    disable_gates = os.getenv("DISABLE_GATES", "0") == "1"
    strict_mode = os.getenv("STRICT", "0") == "1"
    
    if disable_gates:
        logger.info("Quality gates are DISABLED (DISABLE_GATES=1)")
    
    try:
        checker = AudioQualityChecker(disable_gates=disable_gates)
        failed_count = checker.check_all()
        
        # In strict mode, exit with non-zero if there were failures
        if strict_mode and failed_count > 0:
            logger.error(f"STRICT mode: {failed_count} audio files failed critical gates")
            sys.exit(1)
        else:
            sys.exit(0)
            
    except Exception as e:
        logger.error(f"Audio quality checker failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
