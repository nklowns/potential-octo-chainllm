import json
from pathlib import Path

from src.quality.gates.script_gates import WordBoundsGate, ForbiddenTermsGate, SchemaValidationGate
from src.quality.base import Severity, QualityStatus

SCHEMA_PATH = Path('config/schemas/script_v1.json')


def load_minimal_artifact():
    return {
        "topic": "Teste",
        "content": "palavra1 palavra2 palavra3",
        "metadata": {"model": "test-model", "timestamp": "2024-01-01T00:00:00Z"}
    }


def test_word_bounds_pass():
    gate = WordBoundsGate(min_words=1, max_words=10, severity=Severity.ERROR)
    result = gate.check(load_minimal_artifact())
    assert result.status == QualityStatus.PASS


def test_word_bounds_fail_too_short():
    gate = WordBoundsGate(min_words=5, max_words=10, severity=Severity.ERROR)
    artifact = load_minimal_artifact()
    artifact['content'] = 'a b c'
    result = gate.check(artifact)
    assert result.status == QualityStatus.FAIL


def test_forbidden_terms_detects():
    gate = ForbiddenTermsGate(forbidden_terms=['segredo'], severity=Severity.ERROR)
    artifact = load_minimal_artifact()
    artifact['content'] += ' segredo'
    result = gate.check(artifact)
    assert result.status == QualityStatus.FAIL
    assert 'segredo' in result.details['found_terms']


def test_schema_validation_pass():
    gate = SchemaValidationGate(schema_path=SCHEMA_PATH, severity=Severity.ERROR)
    result = gate.check(load_minimal_artifact())
    assert result.status == QualityStatus.PASS


def test_schema_validation_fail_missing_field(tmp_path):
    gate = SchemaValidationGate(schema_path=SCHEMA_PATH, severity=Severity.ERROR)
    artifact = load_minimal_artifact()
    del artifact['topic']
    result = gate.check(artifact)
    assert result.status == QualityStatus.FAIL
