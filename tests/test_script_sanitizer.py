import textwrap

from src.utils.script_sanitizer import extract_narration, list_visual_cues, parse_control_tags


def test_extract_narration_basic():
    sample = textwrap.dedent(
        """
    [TONE: energico]
    [PACE: rapido]
    **1. ATENÇÃO**
    [VISUAL] Desenvolvedor olhando tela confusa
    "Você já perdeu horas configurando ambiente que não funciona?"

    **2. CONEXÃO**
    "Isso atrasa projeto e gera frustração."
    [VISUAL] Relógio acelerando

    **3. ESTRUTURA**
    "Docker empacota tudo: dependências, código e ambiente igual."
    "Roda igual no seu PC, no servidor ou na máquina do colega."

    **4. AÇÃO**
    "Salva esse vídeo e segue para mais dicas."
        """
    ).strip()

    narration = extract_narration(sample)
    cues = list_visual_cues(sample)

    # Verifica se linhas VISUAL foram excluídas da narração
    assert all('[VISUAL]' not in line for line in narration.splitlines())

    # A extração remove aspas nos resultados
    assert '"' not in narration

    # Checa que pelo menos duas frases principais estão presentes
    assert 'Docker empacota tudo' in narration
    assert 'Salva esse vídeo' in narration

    # Visual cues capturadas
    assert len(cues) == 2
    assert cues[0].startswith('[VISUAL]')

    tags = parse_control_tags(sample)
    assert tags.get('tone') == 'energico'
    assert tags.get('pace') == 'rapido'
