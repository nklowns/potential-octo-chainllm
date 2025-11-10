# Quality Gates - Guia de Uso

Este documento descreve como usar o sistema de Quality Gates implementado no pipeline.

## Visão Geral

O sistema de Quality Gates V2 valida automaticamente scripts e áudios gerados, garantindo que apenas artefatos de qualidade sejam produzidos. O sistema:

- ✅ Valida estrutura e conteúdo dos scripts
- ✅ Valida formato e qualidade dos áudios
- ✅ Gera relatórios detalhados por artefato
- ✅ Isola artefatos reprovados em quarentena
- ✅ Suporta modo estrito para CI/CD
- ✅ Permite desabilitar gates para desenvolvimento

## Comandos Principais

### Pipeline Completo com Quality Gates

```bash
# Executa pipeline completo (scripts + áudio + quality gates)
make pipeline

# Ou executar em etapas separadas
make scripts-pipeline    # Gera scripts + valida
make audio-pipeline      # Gera áudio + valida
```

### Pipeline sem Quality Gates

```bash
# Para desenvolvimento rápido, desabilita quality gates
make pipeline-without-gates

# Ou via variável de ambiente
DISABLE_GATES=1 make pipeline
```

### Executar apenas Quality Gates

```bash
# Validar apenas scripts já gerados
make quality-scripts

# Validar apenas áudios já gerados
make quality-audio

# Validar ambos
make quality-gates
```

### Listar Falhas

```bash
# Lista todos os artefatos que falharam nos quality gates
make list-failures
```

### Gerar Relatório Consolidado

```bash
# Gera relatório agregado de todos os quality checks
make generate-summary
```

## Quality Gates - Scripts

### Gates Implementados

1. **Schema Validation** (error)
   - Valida estrutura do JSON contra `config/schemas/script_v1.json`
   - Verifica campos obrigatórios: topic, content, metadata
   - Valida formato de timestamp (ISO 8601)

2. **Word Bounds** (error)
   - Mínimo: 50 palavras
   - Máximo: 500 palavras
   - Configurável em `config/quality.json`

3. **Forbidden Terms** (error)
   - Detecta termos proibidos: hack, pirata, ilegal, crackeado
   - Lista configurável em `config/quality.json`

4. **Language Check** (warn)
   - Verifica se o script está em pt-BR
   - Usa heurística de palavras comuns e caracteres acentuados
   - Não bloqueia por padrão (severity: warn)

### Exemplo de Script Válido

```json
{
  "topic": "Tecnologia Docker",
  "content": "Docker é uma plataforma de containerização...",
  "metadata": {
    "model": "gemma3:4b",
    "timestamp": "2024-11-10T14:00:00Z",
    "word_count": 120,
    "duration_seconds": 5.2
  }
}
```

## Quality Gates - Áudio

### Gates Implementados

1. **Audio Format** (error)
   - Sample rate mínimo: 16kHz
   - Canais: 1-2
   - Duração: > 0 segundos
   - Formato válido (WAV)

2. **Duration Consistency** (error)
   - Verifica consistência entre duração do áudio e word_count
   - Taxa esperada: 1-5 palavras/segundo
   - Evita áudios muito rápidos ou muito lentos

## Configuração

### Arquivo: `config/quality.json`

```json
{
  "enabled": true,              // Ativa/desativa quality gates
  "llm_assisted": false,        // Gates assistidos por LLM (futuro)
  "script": {
    "min_words": 50,            // Mínimo de palavras
    "max_words": 500,           // Máximo de palavras
    "forbidden_terms": [...],   // Lista de termos proibidos
    "language": "pt-BR"         // Idioma esperado
  },
  "audio": {
    "min_duration_sec": 5,      // Duração mínima em segundos
    "max_duration_sec": 300,    // Duração máxima em segundos
    "min_sample_rate": 16000    // Sample rate mínimo
  },
  "severity": {
    "schema_validation": "error",  // error = bloqueia, warn = avisa
    "word_bounds": "error",
    "forbidden_terms": "error",
    "language": "warn",
    ...
  }
}
```

## Variáveis de Ambiente

### DISABLE_GATES

Desabilita todos os quality gates:

```bash
DISABLE_GATES=1 make pipeline
```

### STRICT

Modo estrito - retorna exit code != 0 se houver falhas:

```bash
# Para CI/CD
STRICT=1 make quality-gates
if [ $? -ne 0 ]; then
  echo "Quality gates falharam!"
  exit 1
fi
```

## Estrutura de Diretórios

```
data/output/
├── scripts/                    # Scripts gerados
│   ├── script_001_topic.txt   # Formato texto
│   └── script_001_topic.json  # Formato JSON (para gates)
├── audio/                      # Áudios gerados
│   └── script_001_topic.wav
├── reports/                    # Relatórios de qualidade
│   ├── scripts/
│   │   └── script_001_topic.json
│   ├── audio/
│   │   └── script_001_topic.json
│   └── summary.json           # Relatório consolidado
├── quarantine/                 # Artefatos reprovados
│   ├── scripts/
│   │   ├── script_002_bad.txt
│   │   └── script_002_bad_reason.txt
│   └── audio/
└── run_manifest.json          # Manifesto de execução
```

## Relatórios

### Relatório Individual (por artefato)

```json
{
  "artifact_id": "script_001_topic",
  "artifact_type": "script",
  "timestamp": "2024-11-10T14:00:00Z",
  "quality": {
    "processed": true,
    "status": "pass",
    "gates_run": 4,
    "gates_passed": 4,
    "gates_failed": 0
  },
  "gate_results": [
    {
      "gate_name": "schema_validation",
      "status": "pass",
      "severity": "error",
      "message": "Script structure is valid"
    }
  ]
}
```

### Relatório Consolidado (summary.json)

```json
{
  "generated_at": "2024-11-10T14:30:00Z",
  "scripts": {
    "total": 10,
    "passed": 8,
    "failed": 2,
    "warned": 0
  },
  "audio": {
    "total": 8,
    "passed": 8,
    "failed": 0
  },
  "overall": {
    "total_artifacts": 18,
    "total_passed": 16,
    "total_failed": 2
  }
}
```

## Manifesto de Execução

O arquivo `data/output/run_manifest.json` rastreia o estado de cada artefato:

```json
{
  "run_id": "run_20241110_140000",
  "config_hash": "abc123",
  "scripts": [
    {
      "topic": "Docker",
      "script_id": "script_001_docker",
      "path": "/path/to/script_001_docker.txt",
      "quality_status": "pass",
      "ready_for_audio": true,
      "word_count": 120
    }
  ],
  "audio": [
    {
      "script_id": "script_001_docker",
      "audio_id": "script_001_docker",
      "path": "/path/to/script_001_docker.wav",
      "quality_status": "pass",
      "duration": 45.2
    }
  ]
}
```

## Lazy Gating

O sistema implementa **lazy evaluation** (short-circuit):

- ✅ Gates são executados em ordem definida
- ✅ Ao encontrar falha crítica (severity: error), para a execução
- ✅ Gates restantes são marcados como "skipped"
- ✅ Economiza tempo e recursos

Exemplo:
```
Gate 1 (schema) → PASS
Gate 2 (word_bounds) → PASS
Gate 3 (forbidden_terms) → FAIL (critical)
Gate 4 (language) → SKIPPED (devido à falha anterior)
```

## Workflow Típico

### 1. Desenvolvimento (sem gates)

```bash
# Desenvolvimento rápido sem validação
DISABLE_GATES=1 make pipeline
```

### 2. Teste Local (com gates)

```bash
# Executa com quality gates
make pipeline

# Verifica falhas
make list-failures
```

### 3. Corrigir Falhas

Edite `config/quality.json` se necessário ajustar thresholds ou:

- Corrija scripts com termos proibidos
- Ajuste word count se necessário
- Regenere áudios com problemas

### 4. CI/CD (modo estrito)

```bash
# No CI/CD, use modo estrito
STRICT=1 make pipeline

# Exit code != 0 se houver falhas críticas
echo $?  # 0 = sucesso, 1 = falha
```

## Personalização

### Adicionar Termos Proibidos

Edite `config/quality.json`:

```json
{
  "script": {
    "forbidden_terms": [
      "hack",
      "pirata",
      "ilegal",
      "crackeado",
      "seu_termo_aqui"
    ]
  }
}
```

### Ajustar Limites de Palavras

```json
{
  "script": {
    "min_words": 30,    // Reduz mínimo
    "max_words": 1000   // Aumenta máximo
  }
}
```

### Mudar Severidade

```json
{
  "severity": {
    "forbidden_terms": "warn",  // Agora só avisa, não bloqueia
    "language": "error"         // Agora bloqueia se não for pt-BR
  }
}
```

## Troubleshooting

### "Quality gates disabled"

- Verifique `config/quality.json` → `"enabled": true`
- Não use `DISABLE_GATES=1`

### "No quality reports found"

- Execute `make quality-scripts` ou `make quality-audio` primeiro
- Verifique se há arquivos em `data/output/scripts/` ou `data/output/audio/`

### "soundfile library not available"

```bash
# Instale a dependência
pip install soundfile
# Ou reconstrua a imagem Docker
make build
```

### Relatórios não sendo gerados

```bash
# Verifique permissões
ls -la data/output/reports/

# Recrie diretórios
mkdir -p data/output/reports/{scripts,audio}
mkdir -p data/output/quarantine/{scripts,audio}
```

## Próximos Passos

Conforme roadmap em `docs/QUALITY_GATES_V2.md`:

- [ ] **Fase 2**: Gates de silêncio e loudness para áudio
- [ ] **Fase 3**: Gates assistidos por LLM (análise de engajamento)
- [ ] **Fase 4**: Detecção de duplicidade, observabilidade
- [ ] **Fase 5**: Análises avançadas com librosa

## Referências

- **Especificação Completa**: `docs/QUALITY_GATES_V2.md`
- **Schema de Scripts**: `config/schemas/script_v1.json`
- **Configuração**: `config/quality.json`
- **Código-fonte**: `src/quality/`
