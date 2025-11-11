from src.quality.gates.loader import discover_gates

def test_discover_builtin_gates():
    registry = discover_gates()
    # Expect script and audio gates present by their GATE_NAME or name
    expected = {'schema_validation', 'word_bounds', 'forbidden_terms', 'language', 'script_completeness', 'duplicates',
                'audio_format', 'duration_consistency', 'silence_detection', 'loudness_check'}
    assert expected.intersection(registry.keys()), 'Should find at least one expected gate'
    # Ensure audio_format present explicitly
    assert 'audio_format' in registry
