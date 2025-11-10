"""Quality gate reporters for generating reports and handling quarantine."""

import json
import logging
import shutil
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime

from ..base import GateResult, QualityStatus
from src.utils.metrics_exporter import write_metrics

logger = logging.getLogger(__name__)


class QualityReporter:
    """Generates quality reports for scripts and audio."""

    def __init__(
        self,
        reports_dir: Path,
        quarantine_dir: Path
    ):
        """
        Initialize reporter.

        Args:
            reports_dir: Directory for quality reports.
            quarantine_dir: Directory for quarantined artifacts.
        """
        self.reports_dir = reports_dir
        self.quarantine_dir = quarantine_dir

        # Ensure directories exist
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        self.quarantine_dir.mkdir(parents=True, exist_ok=True)

    def generate_report(
        self,
        artifact_id: str,
        artifact_type: str,  # "script" or "audio"
        artifact_path: Path,
        results: List[GateResult],
        overall_status: QualityStatus,
        metadata: Dict[str, Any] = None
    ) -> Path:
        """
        Generate a quality report for an artifact.

        Args:
            artifact_id: Unique identifier for the artifact.
            artifact_type: Type of artifact (script/audio).
            artifact_path: Path to the artifact file.
            results: List of gate results.
            overall_status: Overall quality status.
            metadata: Additional metadata to include.

        Returns:
            Path to the generated report file.
        """
        # Optional: include run_id if present in metadata argument to propagate to metrics
        run_id = None
        if metadata and isinstance(metadata, dict):
            run_id = metadata.get('run_id')

        report_data = {
            "artifact_id": artifact_id,
            "artifact_type": artifact_type,
            "artifact_path": str(artifact_path),
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "quality": {
                "processed": True,
                "status": overall_status.value,
                "gates_run": len(results),
                "gates_passed": sum(1 for r in results if r.status == QualityStatus.PASS),
                "gates_failed": sum(1 for r in results if r.status == QualityStatus.FAIL),
                "gates_warned": sum(1 for r in results if r.status == QualityStatus.WARN),
                "gates_skipped": sum(1 for r in results if r.status == QualityStatus.SKIPPED),
            },
            "gate_results": [
                {
                    "gate_name": r.gate_name,
                    "status": r.status.value,
                    "severity": r.severity.value,
                    "message": r.message,
                    "details": r.details
                }
                for r in results
            ],
            "metadata": {**(metadata or {}), **({"run_id": run_id} if run_id else {})}
        }

        # Save report
        report_path = self.reports_dir / f"{artifact_id}.json"
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False)

        logger.info(f"Quality report saved: {report_path}")
        return report_path

    def quarantine_artifact(
        self,
        artifact_path: Path,
        artifact_id: str,
        reason: str = "Critical quality gate failure"
    ):
        """
        Move an artifact to quarantine.

        Args:
            artifact_path: Path to the artifact file.
            artifact_id: Unique identifier.
            reason: Reason for quarantine.
        """
        if not artifact_path.exists():
            logger.warning(f"Cannot quarantine non-existent file: {artifact_path}")
            return

        # Create quarantine path
        quarantine_path = self.quarantine_dir / artifact_path.name

        # Copy to quarantine (don't move, keep original)
        try:
            shutil.copy2(artifact_path, quarantine_path)

            # Also save a metadata file explaining why
            meta_path = self.quarantine_dir / f"{artifact_id}_reason.txt"
            with open(meta_path, 'w', encoding='utf-8') as f:
                f.write(f"Quarantined at: {datetime.utcnow().isoformat()}Z\n")
                f.write(f"Reason: {reason}\n")
                f.write(f"Original path: {artifact_path}\n")

            logger.warning(f"Artifact quarantined: {artifact_path} -> {quarantine_path}")

        except Exception as e:
            logger.error(f"Failed to quarantine artifact {artifact_path}: {e}")


class SummaryReporter:
    """Generates aggregate summary reports."""

    def __init__(self, summary_path: Path):
        """
        Initialize summary reporter.

        Args:
            summary_path: Path to the summary report file.
        """
        self.summary_path = summary_path
        self.summary_path.parent.mkdir(parents=True, exist_ok=True)

    def generate_summary(
        self,
        script_reports: List[Path],
        audio_reports: List[Path]
    ):
        """
        Generate aggregate summary from individual reports.

        Args:
            script_reports: List of paths to script report files.
            audio_reports: List of paths to audio report files.
        """
        summary = {
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "scripts": self._summarize_reports(script_reports),
            "audio": self._summarize_reports(audio_reports),
        }

        # Overall statistics
        summary["overall"] = {
            "total_artifacts": summary["scripts"]["total"] + summary["audio"]["total"],
            "total_passed": summary["scripts"]["passed"] + summary["audio"]["passed"],
            "total_failed": summary["scripts"]["failed"] + summary["audio"]["failed"],
            "total_warned": summary["scripts"]["warned"] + summary["audio"]["warned"],
        }

        # Save summary
        with open(self.summary_path, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)

        logger.info(f"Summary report saved: {self.summary_path}")

        # Export Prometheus metrics next to summary (per artifact type for label richness)
        metrics_dir = self.summary_path.parent / 'metrics'
        metrics_dir.mkdir(parents=True, exist_ok=True)

        # Attempt to extract run_id from any report's metadata (first script report if available)
        run_id = None
        probe_list = script_reports + audio_reports
        for rp in probe_list:
            try:
                with open(rp, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                run_id = data.get('metadata', {}).get('run_id')
                if run_id:
                    break
            except Exception:
                continue

        # Write metrics for scripts and audio separately to include artifact_type label
        domains = [
            ('script', summary.get('scripts', {})),
            ('audio', summary.get('audio', {}))
        ]
        for art_type, domain in domains:
            gate_stats = domain.get('gate_statistics', {})
            avg_timings = domain.get('avg_gate_duration_ms', {})
            metrics_path = metrics_dir / f'metrics_{art_type}.prom'
            try:
                write_metrics(metrics_path, gate_stats, avg_timings, run_id=run_id, artifact_type=art_type)
                logger.info(f"Prometheus metrics exported: {metrics_path}")
            except Exception as e:
                logger.warning(f"Failed to export Prometheus metrics for {art_type}: {e}")

        # Backward-compatible: also write a merged metrics.prom without artifact_type label
        merged_gate_stats = {}
        for _, domain in domains:
            for gate, stats in domain.get('gate_statistics', {}).items():
                m = merged_gate_stats.setdefault(gate, {"total": 0, "pass": 0, "fail": 0, "warn": 0, "skipped": 0})
                for k in ("total", "pass", "fail", "warn", "skipped"):
                    m[k] += stats.get(k, 0)
        merged_avg_timings = {}
        for _, domain in domains:
            for gate, val in domain.get('avg_gate_duration_ms', {}).items():
                merged_avg_timings.setdefault(gate, val)

        try:
            combined_path = metrics_dir / 'metrics.prom'
            write_metrics(combined_path, merged_gate_stats, merged_avg_timings, run_id=run_id, artifact_type=None)
            logger.info(f"Prometheus metrics exported (combined): {combined_path}")
        except Exception as e:
            logger.warning(f"Failed to export combined Prometheus metrics: {e}")

    def _summarize_reports(self, report_paths: List[Path]) -> Dict[str, Any]:
        """Summarize a list of individual reports."""
        total = len(report_paths)
        passed = 0
        failed = 0
        warned = 0

        gate_stats = {}
        gate_timings_ms = {}

        for report_path in report_paths:
            try:
                with open(report_path, 'r', encoding='utf-8') as f:
                    report = json.load(f)

                status = report.get("quality", {}).get("status", "unknown")
                if status == "pass":
                    passed += 1
                elif status == "fail":
                    failed += 1
                elif status == "warn":
                    warned += 1

                # Collect gate statistics
                for gate_result in report.get("gate_results", []):
                    gate_name = gate_result["gate_name"]
                    gate_status = gate_result["status"]

                    if gate_name not in gate_stats:
                        gate_stats[gate_name] = {
                            "total": 0,
                            "pass": 0,
                            "fail": 0,
                            "warn": 0,
                            "skipped": 0
                        }

                    gate_stats[gate_name]["total"] += 1
                    # Use the status as key (pass, fail, warn, skipped)
                    if gate_status in gate_stats[gate_name]:
                        gate_stats[gate_name][gate_status] += 1

                    # Collect timing if available
                    duration = (
                        gate_result.get("details", {})
                        .get("metrics", {})
                        .get("duration_ms")
                    )
                    if isinstance(duration, (int, float)):
                        agg = gate_timings_ms.setdefault(gate_name, {"count": 0, "total_ms": 0})
                        agg["count"] += 1
                        agg["total_ms"] += int(duration)

            except Exception as e:
                logger.error(f"Error reading report {report_path}: {e}")

        # Compute averages
        avg_timings = {
            name: round(v["total_ms"] / v["count"]) if v["count"] else 0
            for name, v in gate_timings_ms.items()
        }

        return {
            "total": total,
            "passed": passed,
            "failed": failed,
            "warned": warned,
            "gate_statistics": gate_stats,
            "avg_gate_duration_ms": avg_timings
        }
