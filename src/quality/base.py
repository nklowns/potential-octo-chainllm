"""Base classes for quality gates."""

from abc import ABC, abstractmethod
from enum import Enum
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


class QualityStatus(str, Enum):
    """Status of quality gate evaluation."""
    PASS = "pass"
    FAIL = "fail"
    WARN = "warn"
    SKIPPED = "skipped"


class Severity(str, Enum):
    """Severity level of a quality gate."""
    ERROR = "error"
    WARN = "warn"


@dataclass
class GateResult:
    """Result of a quality gate check."""
    gate_name: str
    status: QualityStatus
    severity: Severity
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    
    def is_critical_failure(self) -> bool:
        """Check if this is a critical failure that should block processing."""
        return self.status == QualityStatus.FAIL and self.severity == Severity.ERROR


class QualityGate(ABC):
    """Base class for quality gates."""
    
    def __init__(self, name: str, severity: Severity):
        self.name = name
        self.severity = severity
    
    @abstractmethod
    def check(self, artifact: Any) -> GateResult:
        """
        Check the quality gate against an artifact.
        
        Args:
            artifact: The artifact to check (dict for scripts, path for audio).
            
        Returns:
            GateResult with the check outcome.
        """
        pass
    
    def _create_result(
        self, 
        status: QualityStatus, 
        message: str, 
        details: Optional[Dict[str, Any]] = None
    ) -> GateResult:
        """Helper to create a gate result."""
        return GateResult(
            gate_name=self.name,
            status=status,
            severity=self.severity,
            message=message,
            details=details or {}
        )
