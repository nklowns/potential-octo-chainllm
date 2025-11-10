from src.quality.runner import QualityGateRunner
from src.quality.base import QualityGate, Severity, QualityStatus, GateResult

class DummyGate(QualityGate):
    def __init__(self, name: str, status: QualityStatus, severity: Severity):
        super().__init__(name, severity)
        self._status = status
    def check(self, artifact):
        return GateResult(gate_name=self.name, status=self._status, severity=self.severity, message='ok', details={})


def test_lazy_stops_on_critical_failure():
    gates = [
        DummyGate('g1', QualityStatus.PASS, Severity.ERROR),
        DummyGate('g2', QualityStatus.FAIL, Severity.ERROR),
        DummyGate('g3', QualityStatus.PASS, Severity.ERROR),
    ]
    runner = QualityGateRunner(gates, lazy=True)
    results = runner.run({})
    names = [r.gate_name for r in results]
    # g3 should be skipped
    assert 'g2' in names
    assert 'g3' in names  # appears as skipped
    # Find skipped entry for g3
    skipped = [r for r in results if r.gate_name == 'g3'][0]
    assert skipped.status == QualityStatus.SKIPPED


def test_non_lazy_runs_all():
    gates = [
        DummyGate('g1', QualityStatus.PASS, Severity.ERROR),
        DummyGate('g2', QualityStatus.FAIL, Severity.ERROR),
        DummyGate('g3', QualityStatus.PASS, Severity.ERROR),
    ]
    runner = QualityGateRunner(gates, lazy=False)
    results = runner.run({})
    assert len(results) == 3
