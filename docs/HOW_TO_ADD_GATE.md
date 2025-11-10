## Como Adicionar um Novo Quality Gate

Este guia mostra o fluxo completo para adicionar um novo gate (ex: `engagement_score`).

### 1. Definir a Regra
Descreva claramente:
- Objetivo (ex: medir taxa de frases imperativas para engajamento)
- Input esperado (script dict / Path para áudio)
- Critérios de PASS/WARN/FAIL

### 2. Atualizar `config/quality.json`
Adicionar na seção `severity` e `ordering.script` ou `ordering.audio`.
```jsonc
"severity": { "engagement_score": "warn" }
"ordering": { "script": ["schema_validation", "engagement_score", ...] }
```

### 3. Implementar Classe
Criar em `src/quality/gates/script_gates.py` ou `audio_gates.py`:
```python
class EngagementScoreGate(QualityGate):
    def __init__(self, min_score: float = 0.3, severity: Severity = Severity.WARN):
        super().__init__("engagement_score", severity)
        self.min_score = min_score

    def check(self, artifact: Dict[str, Any]) -> GateResult:
        content = artifact.get('content', '')
        score = compute_score(content)  # Função auxiliar
        status = QualityStatus.PASS if score >= self.min_score else QualityStatus.WARN
        return self._create_result(status, f"Engagement score: {score:.2f}", {"score": score, "min_score": self.min_score})
```

### 4. Atualizar Factory
Registrar em `GateFactory.create_script_gates`:
```python
elif gate_name == "engagement_score":
    gates.append(EngagementScoreGate(severity=severity))
```

### 5. Testes
Criar teste em `tests/test_engagement_gate.py` com casos PASS/WARN.

### 6. Rodar `make test`
Verifique saída e latência (cada gate agora loga `duration_ms`).

### 7. Documentar
Atualizar este arquivo se necessário e adicionar descrição em `QUALITY_GATES_STATUS.md`.

### 8. Observabilidade (Opcional)
Se o gate for pesado, considerar:
- Cache local
- Amostragem (ex: rodar só em scripts > 150 palavras)

### Checklist Rápido
- [ ] Config atualizado
- [ ] Classe implementada
- [ ] Factory ajustada
- [ ] Testes criados
- [ ] Documentação atualizada
- [ ] Pipeline executa sem erros

Pronto! Novo gate disponível e configurável sem mudar código extra além da factory.
