# Quality Gates V2 — Decisões Consolidadas

Este documento consolida as decisões tomadas para a V2 focada em Quality Gates (scripts e áudios), execução via Makefile/Docker, paralelismo, lazy gating e configuração simples. Ele serve de referência para continuidade do trabalho (inclusive por agente na nuvem).

## Objetivo

Garantir dois artefatos confiáveis por tópico:
- Texto do narrador (script) — validado estruturalmente e de conteúdo.
- Áudio do narrador (TTS) — validado tecnicamente e com checagens de qualidade sonora.

Manter gates simples, previsíveis e extensíveis, com opção de gates assistidos por LLM (Ollama) para análises subjetivas (engajamento, tom, tags).

## Fluxo do Pipeline

Ordem prevista (com e sem gates):
1. Tópicos → Geração de Script (LLM)
2. Quality do Script (gates técnicos → conteúdo → LLM opcional)
3. TTS → Geração de Áudio
4. Quality do Áudio (gates técnicos → qualidade sonora)

Execução padrão: via `make pipeline`. Variantes: `make pipeline-without-gates`, execução manual de gates via `make quality-gates`.

## Makefile — Alvos (nomes referenciais)

- `make pipeline`: executa scripts-pipeline e audio-pipeline em ordem, aguardando workers.
- `make pipeline-without-gates`: fluxo completo com gates desativados.
- `make scripts-pipeline`: apenas etapa de scripts (geração + quality + manifesto).
- `make audio-pipeline`: apenas etapa de áudio (a partir do manifesto).
- `make quality-scripts`: roda apenas os gates de scripts existentes.
- `make quality-audio`: roda apenas os gates de áudios existentes.
- `make quality-gates`: executa quality-scripts + quality-audio.
- `make list-failures`: lista artefatos reprovados (com base nos relatórios/manifesto).
- `make reprocess-scripts-failed` / `make reprocess-audio-failed`: reprocesso seletivo.

Variáveis suportadas (exemplos):
- `DISABLE_GATES=1` (desativa todos os gates).
- `LLM_GATES_ENABLED=1` (ativa gates assistidos por LLM no script).
- `STRICT=1` (pipeline retorna exit code ≠ 0 se houver falhas críticas).
- `SCRIPT_WORKERS` e `AUDIO_WORKERS` (paralelismo por etapa).

Execução preferencial via Docker (container `manager`) e docker-compose já existente.

## Quality Gates — Definição

Script
- Técnicos (críticos e rápidos):
  - JSON Schema (Draft-07) para estrutura mínima e formatos (timestamp), baseado em `config/schemas/script_v1.json`.
  - Limites de palavras (mínimo/máximo).
  - Presença de metadados essenciais (modelo, timestamp).
- Conteúdo (foco funcional):
  - Termos proibidos (lista simples).
  - Linguagem/charset esperado (pt-BR) — verificação básica.
  - (Opcional) Duplicidade (hash) — inicialmente desativado.
- LLM assistido (opcional, não bloqueante inicialmente):
  - Score de engajamento (0–100), tom adequado, tags, melhorias; apenas após passar nos técnicos.

Áudio
- Técnicos:
  - Formato válido (extensão, samplerate ≥ 16 kHz, canais 1–2, duração > 0).
  - Duração consistente com word_count do script (tolerância simples).
- Qualidade sonora:
  - Silêncio inicial e final dentro de limites (ms) e proporção de silêncio total.
  - Faixa de loudness (dBFS) recomendada.
  - (Opcional futuro) Clipping percentual baixo.

Severidades e política (configuráveis):
- `error` bloqueia a etapa/artefato; `warn` registra e continua.
- Short-circuit (lazy gating): se gate crítico falha, não roda os seguintes para aquele artefato.

## Lazy Gating e Paralelismo

- Ordenação por categoria (ex.: script: [schema, word_bounds, forbidden_terms, language, llm_engagement]).
- Lazy: após falha crítica, interromper gates subsequentes para o artefato.
- Paralelismo por tópico com pools distintos:
  - `SCRIPT_WORKERS` (geração/validação de scripts)
  - `AUDIO_WORKERS` (TTS/validação de áudio)
- LLM gates executam somente após gates técnicos, e podem rodar em “segunda onda” para não bloquear TTS.

## Configuração Simples

Arquivo: `config/quality.json` (JSON simples, legível, sem parâmetros excessivamente técnicos).

Campos previstos (exemplo):
- `enabled` (gates on/off), `llm_assisted` (on/off)
- `script`: `min_words`, `max_words`, `forbidden_terms[]`, `language`, `allow_duplicates`
- `audio`: `min_duration_sec`, `max_duration_sec`, `max_leading_silence_ms`, `max_trailing_silence_ms`, `target_loudness_dbfs_min`, `target_loudness_dbfs_max`
- `severity`: mapa gate→severity
- `ordering`: ordem de execução por categoria

Obs.: parâmetros “técnicos” (como `top_db`) só entram quando realmente necessários.

## Manifesto de Execução

Arquivo: `data/output/run_manifest.json`

Uso:
- Produzido na etapa de scripts, contendo lista de scripts, seus status e flag `ready_for_audio`.
- Etapa de áudio consome o manifesto e anexa seus próprios resultados.

Estrutura (alto nível):
- `run_id`, `config_hash`
- `scripts`: [{topic, script_id, path, quality_status, ready_for_audio}]
- `audio`:   [{script_id, audio_id, path, quality_status}]

Escrita atômica (tmp + rename) e lock simples para evitar condições de corrida.

## Relatórios e Quarentena

- Por artefato:
  - Scripts: `data/output/reports/scripts/<id>.json`
  - Áudio:   `data/output/reports/audio/<id>.json`
- Agregado: `data/output/reports/summary.json`
- Quarentena para reprovações críticas:
  - `data/output/quarantine/scripts/`
  - `data/output/quarantine/audio/`

Artefatos conterão metadata sobre se gates foram executados:
`"quality": {"processed": true|false, "status": "pass|fail|warn|skipped", ...}`

## Política de Exit Code

- Padrão: desenvolvimento amigável (exit 0) mesmo com falhas.
- `STRICT=1`: se houver falhas críticas em qualquer etapa, retornar exit code ≠ 0 (para CI/CD).

## Integração com Docker

- Reutilizar compose atual: serviços `ollama`, `piper-tts`, `manager` (pipeline).
- Rodar alvos do Make dentro do container `manager` (montando `data/` e `config/`).

## Segurança e Privacidade

- Validar JSON Schema localmente (sem `$ref` remotos) e sanitizar nomes de arquivos.
- Evitar logar conteúdo integral do script; logs com amostras curtas e códigos de violação.
- Rate-limit já presente no gerador; timeouts por item para evitar travamentos.

## Dependências (mínimo inicial)

- JSON Schema (Python jsonschema) — já referenciado.
- (Áudio básico) soundfile/libsndfile para metadados/duração.
- (Opcional) pydub + ffmpeg para silêncio/loudness práticos.
- (Opcional) librosa para análises mais ricas; ativar depois se preciso.
- Para `format date-time` estrito no schema: `rfc3339-validator` (opcional recomendado).

## Observabilidade (placeholders)

- Endpoints internos reservados (futuro):
  - `GET /quality/status` (resumo)
  - `GET /quality/artifacts/<id>` (relatório)
  - `GET /quality/metrics` (JSON simples)
- Métricas Prometheus podem ser plugadas futuramente (contadores por gate/status e latência).

## Reprocessamento Seletivo

- Scripts: reprocessar apenas falhas reprocessáveis (ex.: timeout LLM; não reprocessar “termos proibidos” automaticamente).
- Áudio: reprocessar falhas técnicas (ex.: duração zero/formato inválido) sem regerar script.

## Versionamento e Rastreabilidade

- `script_v1.json` continua como base estrutural; futura `ScriptV2` poderá incluir `version`, `prompt` completo, `params` e `model_digest`.
- Salvar scripts em `.json` (fonte da verdade) e `.txt` (conveniência), com hash SHA256 no metadata.
- Registrar `config_hash` em relatórios/manifesto para reprodutibilidade.

## Roadmap de Implementação (Fases)

Fase 1 (imediato):
- Alvos do Make (scripts-pipeline, audio-pipeline, pipeline/pipeline-without-gates, quality-scripts/audio, list-failures).
- Gates mínimos: script (schema, word_bounds, forbidden_terms), áudio (format, duration_consistency).
- Manifesto, relatórios básicos, quarentena e política de exit (`STRICT`).

Fase 2:
- Silêncio e loudness no áudio (warn por padrão), linguagem básica no script, lazy gating, paralelismo.

Fase 3:
- Gate LLM assistido (script) opcional, cache por hash, reprocessamento seletivo.

Fase 4:
- Duplicidade de script, endpoints de observabilidade (implementação real), métricas.

Fase 5:
- Calibração fina de thresholds e, se necessário, análises mais ricas (librosa/ASR futuramente).

## Decisões-chave

- Separação de pipelines de Scripts e Áudio (alvos Make dedicados) com um alvo geral `pipeline` que orquestra ambos.
- Configuração simples em `config/quality.json` (sem tecnicalidades desnecessárias).
- Lazy gating + paralelismo por tópico; LLM assistido é opcional e não bloqueia inicialmente.
- Manifesto de execução para compor dependências e estado; relatórios por artefato + agregado; quarentena para críticos.
- Docker como meio de execução padrão; possibilidade de rodar sem gates.

---

Este documento é o guia de implementação da V2 focada em Quality Gates. Ajustes pontuais podem ser feitos conforme aprendizados práticos (especialmente thresholds e severidades), mantendo a simplicidade como princípio.
