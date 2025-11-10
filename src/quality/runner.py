"""Quality gate runner."""

import logging
from typing import Any, List, Optional
from datetime import datetime
from .base import GateResult, QualityGate, QualityStatus

logger = logging.getLogger(__name__)


class QualityGateRunner:
    """Runs quality gates against artifacts with lazy evaluation support."""

    def __init__(self, gates: List[QualityGate], lazy: bool = True):
        """
        Initialize the runner.

        Args:
            gates: List of quality gates to run in order.
            lazy: If True, stop running gates after first critical failure.
        """
        self.gates = gates
        self.lazy = lazy

    def run(self, artifact: Any) -> List[GateResult]:
        """
        Run all gates against an artifact.

        Args:
            artifact: The artifact to check.

        Returns:
            List of GateResults from all executed gates.
        """
        results = []

        for gate in self.gates:
            try:
                gate_start = datetime.utcnow()
                logger.info(f"Running gate: {gate.name}")
                result = gate.check(artifact)
                gate_end = datetime.utcnow()
                duration_ms = int((gate_end - gate_start).total_seconds() * 1000)
                # Inject timing into details
                result.details.setdefault('metrics', {})
                result.details['metrics']['duration_ms'] = duration_ms
                logger.info(
                    f"Gate completed: {gate.name} status={result.status.value} severity={result.severity.value} duration_ms={duration_ms}"
                )
                results.append(result)

                # Lazy evaluation: stop on first critical failure
                if self.lazy and result.is_critical_failure():
                    logger.warning(
                        f"Critical failure in gate '{gate.name}'. "
                        f"Skipping remaining gates due to lazy evaluation."
                    )
                    # Mark remaining gates as skipped
                    for remaining_gate in self.gates[self.gates.index(gate) + 1:]:
                        results.append(GateResult(
                            gate_name=remaining_gate.name,
                            status=QualityStatus.SKIPPED,
                            severity=remaining_gate.severity,
                            message="Skipped due to previous critical failure",
                            details={}
                        ))
                    break

            except Exception as e:
                gate_end = datetime.utcnow()
                duration_ms = int((gate_end - gate_start).total_seconds() * 1000)
                logger.error(f"Error running gate '{gate.name}': {e}", exc_info=True)
                results.append(GateResult(
                    gate_name=gate.name,
                    status=QualityStatus.FAIL,
                    severity=gate.severity,
                    message=f"Gate execution error: {str(e)}",
                    details={"exception": str(e), "metrics": {"duration_ms": duration_ms}}
                ))
                # Treat execution errors as critical failures for lazy evaluation
                if self.lazy:
                    break

        return results

    def has_critical_failures(self, results: List[GateResult]) -> bool:
        """Check if any results are critical failures."""
        return any(r.is_critical_failure() for r in results)

    def get_overall_status(self, results: List[GateResult]) -> QualityStatus:
        """
        Determine overall status from gate results.

        Returns:
            FAIL if any critical failures, WARN if any warnings, PASS otherwise.
        """
        if any(r.is_critical_failure() for r in results):
            return QualityStatus.FAIL
        if any(r.status == QualityStatus.WARN for r in results):
            return QualityStatus.WARN
        if all(r.status in (QualityStatus.PASS, QualityStatus.SKIPPED) for r in results):
            return QualityStatus.PASS
        return QualityStatus.FAIL
