"""Utilitário para sanitizar textos de roteiro antes de enviar ao TTS.

Regras:
 - Apenas trechos entre aspas são considerados NARRAÇÃO. Todo o resto é ignorado.
 - Linhas iniciadas com [TAG: valor] NÃO devem ser narradas.
 - Remove aspas dos trechos narráveis antes de enviar ao TTS.
 - Mantém ordem original dos trechos narrados.
 - Faz leitura de controles de voz globais: [TONE: ...], [PACE: ...].
 - Identifica linhas de indicações visuais: [VISUAL: ...].
"""
from __future__ import annotations

import re
from typing import Iterable, Dict


def _is_visual_line(line: str) -> bool:
    l = line.strip()
    if not l:
        return False
    if l.lower().startswith('[visual:'):
        return True
    return False


_QUOTED_RE = re.compile(r'"([^"]+)"|“([^”]+)”')


def extract_narration(text: str) -> str:
    """Extrai apenas os trechos entre aspas (falas) para narração.

    Parameters
    ----------
    text : str
        Conteúdo completo do roteiro.

    Returns
    -------
    str
        Texto pronto para TTS (apenas narracao).
    """
    narration_chunks: list[str] = []
    # Extração por linha: captura múltiplas falas na mesma linha, se houver
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or _is_visual_line(line):
            continue
        for m in _QUOTED_RE.finditer(line):
            # Dois grupos alternados; pega o que não for None
            chunk = m.group(1) if m.group(1) is not None else m.group(2)
            if chunk:
                narration_chunks.append(chunk.strip())
    return '\n'.join(narration_chunks).strip()


def list_visual_cues(text: str) -> list[str]:
    """Retorna todas as linhas que representam indicações visuais.
    Útil para depuração ou geração de assets.
    """
    cues = []
    for raw_line in text.splitlines():
        if _is_visual_line(raw_line):
            cues.append(raw_line.strip())
    return cues


def parse_control_tags(text: str) -> Dict[str, str]:
    """Lê tags de controle globais como [TONE: ...] e [PACE: ...].

    Retorna um dicionário com chaves minúsculas. Ex:
    {"tone": "energico", "pace": "rapido"}
    """
    tone = None
    pace = None
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line.startswith('[') or ']' not in line:
            continue
        tag = line[1:line.index(']')].strip()
        # Aceita formatos com TONE ou TOM
        if tag.lower().startswith('tone:') or tag.lower().startswith('tom:'):
            tone = tag.split(':', 1)[1].strip().lower()
        elif tag.lower().startswith('pace:') or tag.lower().startswith('ritmo:'):
            pace = tag.split(':', 1)[1].strip().lower()
    result: Dict[str, str] = {}
    if tone:
        result['tone'] = tone
    if pace:
        result['pace'] = pace
    return result


__all__ = ["extract_narration", "list_visual_cues", "parse_control_tags"]
