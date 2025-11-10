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

2. **Word Bounds** (warn) - ⚠️ **Atualizado**
   - Mínimo: 10 palavras (validação apenas para textos muito curtos/vazios)
   - Máximo: 2000 palavras (permite conteúdo completo do Ollama)
   - **Não bloqueia** - apenas avisa se fora dos limites
   - Configurável em `config/quality.json`

3. **Forbidden Terms** (error) - ⚠️ **Atualizado**
   - Carregado de arquivo externo: `config/forbidden_terms.txt`
   - Um termo por linha, suporta comentários com `#`
   - Termos atuais: hack, pirata, ilegal, crackeado
   - Fácil manutenção sem editar código

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
  "enabled": true,                        // Ativa/desativa quality gates
  "llm_assisted": false,                  // Gates assistidos por LLM (futuro)
  "script": {
    "min_words": 10,                      // Mínimo de palavras (relaxado)
    "max_words": 2000,                    // Máximo de palavras (relaxado)
    "forbidden_terms_file": "config/forbidden_terms.txt",  // Arquivo externo
    "language": "pt-BR"                   // Idioma esperado
  },
  "audio": {
    "min_duration_sec": 5,                // Duração mínima em segundos
    "max_duration_sec": 300,              // Duração máxima em segundos
    "min_sample_rate": 16000    // Sample rate mínimo
  },
  "severity": {
    "schema_validation": "error",  // error = bloqueia, warn = avisa
    "word_bounds": "warn",         // Mudado para warn (não bloqueia)
    "forbidden_terms": "error",
    "language": "warn",
    ...
  }
}
```

### Arquivo: `config/forbidden_terms.txt` ⚠️ **Novo**

Arquivo de texto simples, um termo por linha:

```
# Forbidden Terms Configuration
# Lines starting with # are comments

hack
pirata
ilegal
crackeado
```

**Vantagens:**
- Fácil manutenção - adicionar/remover termos sem editar código
- Suporta comentários para documentação
- Pode ser versionado separadamente
- Compartilhável entre ambientes

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

## Estrutura de Diretórios ⚠️ **Atualizado**

```
data/output/
├── scripts/                          # Scripts gerados
│   ├── script_001_topic.txt         # Formato texto
│   └── script_001_topic.json        # Formato JSON (para gates)
├── audio/                            # Áudios gerados
│   └── script_001_topic.wav
└── quality_gates/                    # ⭐ Nova estrutura organizada
    ├── reports/                      # Relatórios de qualidade
    │   ├── scripts/
    │   │   └── script_001_topic.json
    │   ├── audio/
    │   │   └── script_001_topic.json
    │   └── summary.json              # Relatório consolidado
    ├── quarantine/                   # Artefatos reprovados
    │   ├── scripts/
    │   │   ├── script_002_bad.txt
    │   │   └── script_002_bad_reason.txt
    │   └── audio/
    └── run_manifest.json             # Manifesto de execução
```

**Melhorias na estrutura:**
- Tudo relacionado a quality gates agora em `quality_gates/` subdirectory
- Separação clara entre conteúdo gerado e validação
- Mais fácil de entender e navegar
- Melhor para backup seletivo

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
- ✅ Gates com severity: warn NÃO param a execução
- ✅ Gates restantes são marcados como "skipped" após falha crítica
- ✅ Economiza tempo e recursos

Exemplo com word_bounds como WARN:
```
Gate 1 (schema) → PASS
Gate 2 (word_bounds) → FAIL (warn) ⚠️ continua executando
Gate 3 (forbidden_terms) → FAIL (error) ❌ para aqui
Gate 4 (language) → SKIPPED (devido à falha crítica anterior)
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

### Adicionar Termos Proibidos ⚠️ **Atualizado**

Edite `config/forbidden_terms.txt`:

```
# Forbidden Terms Configuration
# Add one term per line

hack
pirata
ilegal
crackeado
seu_termo_aqui
outro_termo
```

**Muito mais simples!** Não precisa editar JSON ou código.

### Ajustar Limites de Palavras

Edite `config/quality.json`:

```json
{
  "script": {
    "min_words": 5,      // Reduz ainda mais (apenas para detectar vazios)
    "max_words": 5000    // Aumenta para permitir scripts longos
  }
}
```

**Nota:** Com severity "warn", mesmo scripts fora dos limites não são bloqueados.

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
