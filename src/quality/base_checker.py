"""Base quality checker - shared functionality for script and audio checkers."""

import logging
import os
from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

from .base import QualityStatus
from .config import QualityConfig
from .manifest import RunManifest
from .reporters import QualityReporter
from .factory import GateFactory
from src.pipeline import config as pipeline_config

logger = logging.getLogger(__name__)


class BaseQualityChecker(ABC):
    """Base class for quality checkers with common functionality."""

    def __init__(
        self,
        artifact_type: str,
        disable_gates: bool = False,
        max_workers: Optional[int] = None
    ):
        """
        Initialize the base checker.

        Args:
            artifact_type: Type of artifact ('script' or 'audio')
            disable_gates: Whether to disable quality gates
            max_workers: Maximum number of worker threads (None = sequential)
        """
        self.artifact_type = artifact_type
        self.disable_gates = disable_gates
        self.max_workers = max_workers or 1

        # Load quality configuration
        quality_config_path = pipeline_config.CONFIG_DIR / "quality.json"
        self.quality_config = QualityConfig(quality_config_path)
        # Defer manifest init until after we know config (manifest wants snapshot)

        # Setup gate factory
        self.gate_factory = GateFactory(self.quality_config, pipeline_config.BASE_DIR)

        # Setup paths with improved structure
        self.reports_dir = pipeline_config.OUTPUT_DIR / "quality_gates" / "reports" / artifact_type
        self.quarantine_dir = pipeline_config.OUTPUT_DIR / "quality_gates" / "quarantine" / artifact_type
        self.manifest_path = pipeline_config.OUTPUT_DIR / "quality_gates" / "run_manifest.json"

        # Initialize manifest and reporter
        self.manifest = RunManifest(self.manifest_path)
        # Persist a config snapshot for reproducibility (idempotent per run)
        try:
            self.manifest.save_config_snapshot(
                self.quality_config.to_dict(),
                source_path=str(self.quality_config.source_path)
            )
        except Exception as e:
            logger.warning(f"Failed to write config snapshot: {e}")
        self.reporter = QualityReporter(self.reports_dir, self.quarantine_dir)

        # Setup gates
        self.gates = self._setup_gates()

    @abstractmethod
    def _setup_gates(self):
        """Setup quality gates for this checker type."""
        pass

    @abstractmethod
    def _load_artifact(self, artifact_path: Path) -> Any:
        """Load and prepare artifact for quality checking."""
        pass

    @abstractmethod
    def _create_manifest_entry(self, artifact_path: Path, results: List, overall_status: QualityStatus, metadata: Dict) -> Dict:
        """Create manifest entry for this artifact type."""
        pass

    @abstractmethod
    def _get_artifact_files(self) -> List[Path]:
        """Get list of artifact files to check."""
        pass

    def check_artifact(self, artifact_path: Path) -> Dict[str, Any]:
        """
        Check a single artifact.

        Returns:
            Dict with check results including timing information
        """
        artifact_id = artifact_path.stem
        start_time = datetime.utcnow()

        logger.info(f"Checking {self.artifact_type}: {artifact_id}", extra={
            "artifact_type": self.artifact_type,
            "artifact_id": artifact_id
        })

        try:
            # Load artifact
            artifact_data = self._load_artifact(artifact_path)

            # Run quality gates if enabled
            if self.gates and not self.disable_gates:
                from .runner import QualityGateRunner
                runner = QualityGateRunner(
                    self.gates,
                    lazy=True,
                    context={
                        "run_id": self.manifest.to_dict().get("run_id"),
                        "artifact_id": artifact_id,
                        "artifact_type": self.artifact_type
                    }
                )
                results = runner.run(artifact_data)
                overall_status = runner.get_overall_status(results)
                has_critical_failures = runner.has_critical_failures(results)
            else:
                results = []
                overall_status = QualityStatus.PASS
                has_critical_failures = False

            # Get metadata for report
            metadata = self._get_artifact_metadata(artifact_path, artifact_data)

            # Generate report
            self.reporter.generate_report(
                artifact_id=artifact_id,
                artifact_type=self.artifact_type,
                artifact_path=artifact_path,
                results=results,
                overall_status=overall_status,
                metadata=metadata
            )

            # Quarantine if critical failure
            if has_critical_failures:
                self.reporter.quarantine_artifact(
                    artifact_path,
                    artifact_id,
                    reason="Critical quality gate failure"
                )

            # Create manifest entry
            manifest_entry = self._create_manifest_entry(
                artifact_path, results, overall_status, metadata
            )

            # Update manifest
            self._update_manifest(manifest_entry)

            # Calculate timing
            end_time = datetime.utcnow()
            duration_ms = int((end_time - start_time).total_seconds() * 1000)

            return {
                "artifact_id": artifact_id,
                "passed": not has_critical_failures,
                "status": overall_status.value,
                "duration_ms": duration_ms,
                "gates_run": len(results)
            }

        except Exception as e:
            logger.error(f"Error checking {self.artifact_type} {artifact_path}: {e}", exc_info=True)

            # Create error entry
            error_entry = self._create_error_entry(artifact_path, str(e))
            self._update_manifest(error_entry)

            return {
                "artifact_id": artifact_id,
                "passed": False,
                "status": "error",
                "duration_ms": 0,
                "error": str(e)
            }

    def check_all(self, parallel: bool = None) -> Dict[str, Any]:
        """
        Check all artifacts.

        Args:
            parallel: Whether to use parallel processing (None = use max_workers)

        Returns:
            Summary statistics
        """
        artifact_files = self._get_artifact_files()

        if not artifact_files:
            logger.warning(f"No {self.artifact_type} files found")
            return {
                "total": 0,
                "passed": 0,
                "failed": 0,
                "total_duration_ms": 0
            }

        logger.info(f"Found {len(artifact_files)} {self.artifact_type}s to check")

        # Determine if we should use parallel processing
        use_parallel = (parallel is not None and parallel) or (parallel is None and self.max_workers > 1)

        if use_parallel:
            results = self._check_parallel(artifact_files)
        else:
            results = self._check_sequential(artifact_files)

        # Calculate statistics
        total = len(results)
        passed = sum(1 for r in results if r["passed"])
        failed = total - passed
        total_duration_ms = sum(r["duration_ms"] for r in results)

        logger.info(
            f"{self.artifact_type.capitalize()} quality check complete: "
            f"{passed}/{total} passed ({total_duration_ms}ms total)"
        )

        return {
            "total": total,
            "passed": passed,
            "failed": failed,
            "total_duration_ms": total_duration_ms,
            "results": results
        }

    def _check_sequential(self, artifact_files: List[Path]) -> List[Dict]:
        """Check artifacts sequentially."""
        results = []
        for artifact_file in artifact_files:
            result = self.check_artifact(artifact_file)
            results.append(result)
        return results

    def _check_parallel(self, artifact_files: List[Path]) -> List[Dict]:
        """Check artifacts in parallel using thread pool."""
        logger.info(f"Using {self.max_workers} workers for parallel processing")
        results = []

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {
                executor.submit(self.check_artifact, artifact_file): artifact_file
                for artifact_file in artifact_files
            }

            for future in as_completed(futures):
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    artifact_file = futures[future]
                    logger.error(f"Worker failed for {artifact_file}: {e}", extra={
                        "artifact_type": self.artifact_type,
                        "artifact_id": artifact_file.stem
                    })
                    results.append({
                        "artifact_id": artifact_file.stem,
                        "passed": False,
                        "status": "error",
                        "duration_ms": 0,
                        "error": str(e)
                    })

        return results

    @abstractmethod
    def _get_artifact_metadata(self, artifact_path: Path, artifact_data: Any) -> Dict:
        """Extract metadata from artifact for reporting."""
        pass

    @abstractmethod
    def _update_manifest(self, entry: Dict):
        """Update manifest with entry."""
        pass

    @abstractmethod
    def _create_error_entry(self, artifact_path: Path, error: str) -> Dict:
        """Create manifest entry for error case."""
        pass
