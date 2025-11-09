# Changelog

Todas as mudanças notáveis neste projeto serão documentadas neste arquivo.

O formato é baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/),
e este projeto adere ao [Semantic Versioning](https://semver.org/lang/pt-BR/).

## [Não Lançado]

### Em Desenvolvimento
- Geração de imagens com Stable Diffusion
- Interface web para gerenciamento
- API REST para integração externa

## [1.0.0] - 2025-11-09

### 🎉 Lançamento Inicial

#### Adicionado
- Pipeline completo de geração de scripts e áudio
- Integração com Ollama para geração de texto (gemma3:4b)
- Integração com Piper TTS v1.3.1 (GPL) para síntese de áudio
- Arquitetura baseada em microserviços com Docker
- Proxy reverso via Traefik com HTTPS
- Makefile consolidado para automação
- Health checks robustos em todos os serviços
- Retry automático com exponential backoff
- Tratamento de erros robusto
- Logging estruturado
- Documentação completa

#### Melhorias de Código
- Migração de `requests` para `ollama-python` (biblioteca oficial)
- Remoção de `verify=False` com configuração correta de SSL
- Implementação de exceções customizadas
- Type hints e docstrings
- Estrutura modular e extensível

#### Documentação
- README.md principal com quickstart
- Guias detalhados em docs/
- .env.example atualizado
- CHANGELOG.md criado

#### Infraestrutura
- Docker Compose multi-serviço
- Volumes nomeados para cache
- Bind mounts para input/output
- Rede proxy_net externa (Traefik)
- Healthchecks configurados

### Segurança
- Containers rodando como non-root (appuser)
- SSL/TLS via Traefik
- Sem credenciais hardcoded
- Variáveis de ambiente para configuração sensível

## [0.9.0] - 2025-11-08

### Migração Piper TTS

#### Alterado
- **BREAKING**: Migração de rhasspy/piper (MIT, arquivado) para OHF-Voice/piper1-gpl v1.3.1 (GPL)
- Nova API HTTP do Piper TTS
- Dockerfile multi-stage para Piper

#### Removido
- Dependência do rhasspy/piper (descontinuado)

#### Documentação
- MIGRATION_PIPER.md criado
- README_PIPER.md adicionado

## [0.8.0] - 2025-11-07

### Consolidação de Estrutura

#### Adicionado
- Makefile unificado (merge de Makefile + Makefile.piper)
- docker-compose.ollama.yml para Ollama local
- Suporte a GPU NVIDIA

#### Organizado
- Documentação movida para docs/
- Scripts Python em scripts/
- Configurações em config/

## [0.7.0] - 2025-11-06

### Pipeline Funcional

#### Adicionado
- Pipeline de geração de scripts funcional
- Pipeline de conversão text-to-speech funcional
- Integração com Traefik

#### Corrigido
- Caminhos de arquivo (de /app para /home/appuser/app)
- Portas do Piper TTS (8090 → 5000)
- Variáveis de ambiente no .env

## Versões Anteriores

### [0.6.0] - [0.1.0]
Desenvolvimento inicial e protótipos.

---

## Tipos de Mudanças

- `Adicionado` para novas funcionalidades
- `Alterado` para mudanças em funcionalidades existentes
- `Descontinuado` para funcionalidades que serão removidas
- `Removido` para funcionalidades removidas
- `Corrigido` para correções de bugs
- `Segurança` para vulnerabilidades corrigidas

## Links

- [Unreleased]: Comparação com última versão
- [1.0.0]: Tag da v1.0.0
