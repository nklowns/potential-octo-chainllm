from pathlib import Path
from src.quality.gates.script_gates import DuplicateScriptGate
from src.quality.base import Severity, QualityStatus


def make_artifact(content: str, ident: str):
    return {
        "topic": ident,
        "content": content,
        "metadata": {"model": "m", "timestamp": "2024-01-01T00:00:00Z", "id": ident}
    }


def test_duplicates_detected(tmp_path):
    index_path = tmp_path / 'hash_index.json'
    gate = DuplicateScriptGate(index_path=index_path, allow_duplicates=False, severity=Severity.WARN)
    a1 = make_artifact("um dois tres", "s1")
    r1 = gate.check(a1)
    assert r1.status == QualityStatus.PASS
    a2 = make_artifact("um dois tres", "s2")
    r2 = gate.check(a2)
    assert r2.status in (QualityStatus.WARN, QualityStatus.FAIL)
    assert r2.details["duplicates"]


def test_allow_duplicates_pass(tmp_path):
    index_path = tmp_path / 'hash_index.json'
    gate = DuplicateScriptGate(index_path=index_path, allow_duplicates=True, severity=Severity.WARN)
    a1 = make_artifact("A B C", "x1")
    gate.check(a1)
    a2 = make_artifact("A B C", "x2")
    r2 = gate.check(a2)
    # Even with duplicates, should pass due to allow flag
    assert r2.status == QualityStatus.PASS
