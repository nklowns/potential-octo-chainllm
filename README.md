# 🎬 Audio Pipeline - Geração Automatizada de Conteúdo

> Pipeline automatizado para geração de scripts, áudio e imagens usando IA

[![Docker](https://img.shields.io/badge/Docker-Ready-blue)](https://www.docker.com/)
[![Traefik](https://img.shields.io/badge/Traefik-Proxy-green)](https://traefik.io/)
[![Python](https://img.shields.io/badge/Python-3.11-yellow)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-red)](LICENSE)

## 📋 Índice

- [Visão Geral](#-visão-geral)
- [Arquitetura](#-arquitetura)
- [Requisitos](#-requisitos)
- [Instalação Rápida](#-instalação-rápida)
- [Uso](#-uso)
- [Configuração](#️-configuração)
- [Documentação Completa](#-documentação-completa)
- [Troubleshooting](#-troubleshooting)

## 🎯 Visão Geral

O **Audio Pipeline** é uma solução completa para geração automatizada de conteúdo multimídia:

1. **📝 Geração de Scripts**: Cria roteiros usando LLMs via Ollama
2. **✅ Quality Gates**: Valida qualidade de scripts e áudios
3. **🔊 Síntese de Áudio**: Converte texto em áudio usando Piper TTS
4. **🖼️ Geração de Imagens**: Cria imagens com Stable Diffusion (em breve)

### Características

✅ **Containerizado**: 100% Docker, fácil de implantar
✅ **Escalável**: Arquitetura modular e extensível
✅ **Quality Gates**: Validação automática de qualidade
✅ **Seguro**: HTTPS via Traefik, certificados automáticos
✅ **Observável**: Logs, health checks e monitoramento
✅ **Resiliente**: Retry automático e tratamento de erros

## 🏗️ Arquitetura

```
┌─────────────────────────────────────────────────────────────┐
│                       TRAEFIK PROXY                         │
│                    (HTTPS / DNS / Load Balancing)           │
└────────┬────────────────────┬────────────────────┬──────────┘
         │                    │                    │
         ▼                    ▼                    ▼
    ┌────────┐          ┌──────────┐        ┌──────────────┐
    │ OLLAMA │          │ PIPER TTS│        │  STABLE-DIFF │
    │ gemma3 │          │  v1.3.1  │        │   (futuro)   │
    └────────┘          └──────────┘        └──────────────┘
         │                    │                    │
         └────────────────────┴────────────────────┘
                              │
                     ┌────────▼────────┐
                     │  PIPELINE MGR   │
                     │  (Orquestrador) │
                     └─────────────────┘
                              │
         ┌────────────────────┼────────────────────┐
         ▼                    ▼                    ▼
    [Scripts]             [Áudios]            [Imagens]
     output/              output/             output/
     scripts/             audio/              images/
```

### Serviços

| Serviço | Porta | Descrição | URL |
|---------|-------|-----------|-----|
| **Ollama** | 11434 | LLM para geração de texto | `https://ollama.drake-ayu.duckdns.org` |
| **Piper TTS** | 5000 | Text-to-Speech (GPL v1.3.1) | `https://piper-tts.drake-ayu.duckdns.org` |
| **Pipeline Manager** | - | Orquestrador (run-once) | - |

## 📦 Requisitos

### Essenciais

- **Docker** >= 24.0
- **Docker Compose** >= 2.0
- **Traefik** rodando na rede `proxy_net`
- **DNS**: `drake-ayu.duckdns.org` configurado

### Opcionais

- **GPU NVIDIA** (para Ollama/Stable Diffusion locais)
- **make** (para automação de comandos)

## 🚀 Instalação Rápida

### 1. Clone o Repositório

```bash
git clone https://github.com/seu-usuario/audio-pipeline.git
cd audio-pipeline/supertest
```

### 2. Configure Variáveis de Ambiente

```bash
cp .env.example .env
nano .env  # Edite conforme necessário
```

**Variáveis principais:**

```bash
# Domínios
DOMAIN_DUCKDNS=drake-ayu.duckdns.org

# Ollama (usar serviço externo ou local)
OLLAMA_BASE_URL=https://ollama.drake-ayu.duckdns.org
OLLAMA_MODEL=gemma3:4b
```

### 3. Crie Arquivo de Tópicos

```bash
cat > data/input/topics.txt <<EOF
Tecnologia Docker para desenvolvedores
Inteligência Artificial no dia a dia
Python para automação de tarefas
EOF
```

### 4. Execute o Pipeline

```bash
make setup    # Setup inicial (uma vez)
make pipeline # Gera scripts + áudio + quality gates
make monitor  # Visualiza resultados
```

## 💡 Uso

### Comandos Principais

```bash
# SETUP
make setup           # Setup completo do projeto
make build           # Build das imagens

# SERVIÇOS
make tts-up          # Inicia Piper TTS
make ollama-up       # Inicia Ollama local (opcional)

# PIPELINE
make pipeline              # Pipeline completo (scripts + áudio + quality gates)
make scripts-pipeline      # Apenas pipeline de scripts + quality
make audio-pipeline        # Apenas pipeline de áudio + quality
make pipeline-without-gates # Pipeline sem quality gates (desenvolvimento)

# QUALITY GATES
make quality-scripts   # Valida scripts gerados
make quality-audio     # Valida áudios gerados
make quality-gates     # Valida scripts + áudios
make list-failures     # Lista artefatos reprovados
make generate-summary  # Gera relatório consolidado

# MONITORAMENTO
make monitor         # Visualiza outputs gerados
make logs            # Logs do pipeline
make status          # Status dos serviços

# LIMPEZA
make clean           # Para containers
make clean-outputs   # Limpa arquivos gerados
make backup          # Backup de outputs

# AJUDA
make help            # Lista todos os comandos
```

### Workflow Típico

```bash
# 1. Primeiro uso
make setup

# 2. Adicionar tópicos em data/input/topics.txt
nano data/input/topics.txt

# 3. Executar pipeline
make pipeline

# 4. Verificar resultados
make monitor
ls -lh data/output/scripts/
ls -lh data/output/audio/

# 5. Backup (opcional)
make backup
```

## ⚙️ Configuração

### Estrutura de Diretórios

```
audio-pipeline/
├── data/               # Dados do pipeline
│   ├── input/          # Entrada (tópicos)
│   │   └── topics.txt
│   └── output/         # Saídas geradas
│       ├── scripts/    # Roteiros .txt
│       ├── audio/      # Áudio .wav
│       └── images/     # Imagens .png (futuro)
├── config/             # Configurações
│   └── voices.json
├── docs/               # Documentação detalhada
├── scripts/            # Scripts Python
└── .env                # Configuração local
```

### Variáveis de Ambiente Avançadas

Consulte [`.env.example`](.env.example) para lista completa.

**Ollama:**
```bash
OLLAMA_BASE_URL=https://ollama.drake-ayu.duckdns.org
OLLAMA_MODEL=gemma3:4b      # ou qwen3-vl:4b, llama3.2, etc
```

**Piper TTS:**
Configuração via `config/voices.json` (v2). Exemplo:

```jsonc
{
     "version": 2,
     "default_voice": "piper_pt_br",
     "available_backends": {
          "piper": {
               "base_url": "http://piper-tts:5000",
               "defaults": { "length_scale": 1.0, "noise_scale": 0.667, "noise_w_scale": 0.8 }
          }
     },
     "available_voices": {
          "piper_pt_br": { "backend": "piper", "model_id": "pt_BR-faber-medium", "params": {} }
     }
}
```

**Caminhos (Container):**
```bash
INPUT_FILE=/home/appuser/app/data/input/topics.txt
OUTPUT_SCRIPTS=/home/appuser/app/data/output/scripts
OUTPUT_AUDIO=/home/appuser/app/data/output/audio
```

**Quality Gates:**
```bash
DISABLE_GATES=0    # 1 = desabilita quality gates
STRICT=0           # 1 = exit code != 0 se houver falhas (CI/CD)
```

## 📚 Documentação Completa

### Guias Essenciais

- **[DEPLOYMENT.md](docs/DEPLOYMENT.md)** - Guia completo de implantação e uso
- **[DEVELOPMENT.md](docs/DEVELOPMENT.md)** - Guia de desenvolvimento e contribuição
- **[ARCHITECTURE.md](docs/ARCHITECTURE.md)** - Arquitetura detalhada e design decisions
- **[QUALITY_GATES_STATUS.md](docs/QUALITY_GATES_STATUS.md)** - ✨ **Status atual da implementação** (READ FIRST)
- **[QUALITY_GATES_USAGE.md](docs/QUALITY_GATES_USAGE.md)** - Guia completo de uso
- **[QUALITY_GATES_V2.md](docs/QUALITY_GATES_V2.md)** - Especificação técnica e roadmap

### Documentação Técnica

- **[MIGRATION_PIPER.md](docs/MIGRATION_PIPER.md)** - Migração Piper TTS para v1.3.1
- **[TECH_ANALYSIS.md](docs/TECH_ANALYSIS.md)** - Análise técnica e stack
- **[BEST_PRACTICES.md](docs/BEST_PRACTICES.md)** - Boas práticas de desenvolvimento

### Status e Planejamento

- **[PROJECT_STATUS.md](docs/PROJECT_STATUS.md)** - Status atual do projeto
- **[GAPS_ANALYSIS.md](docs/GAPS_ANALYSIS.md)** - Análise de gaps e melhorias
- **[RESTRUCTURE_PLAN.md](docs/RESTRUCTURE_PLAN.md)** - Plano de reestruturação

## 🔧 Troubleshooting

### Ollama retorna 404

```bash
# Verificar se Ollama está rodando
curl -k https://ollama.drake-ayu.duckdns.org/api/tags

# Iniciar Ollama local (se necessário)
make ollama-up

# Alterar .env para usar Ollama local
OLLAMA_BASE_URL=http://ollama:11434
```

### Piper TTS não responde

```bash
# Verificar logs
make tts-logs

# Rebuild do TTS
make tts-build
make tts-up

# Testar endpoint
make tts-test
```

### Pipeline falha com permissão negada

```bash
# Verificar permissões dos diretórios
ls -la output/

# Recriar diretórios
rm -rf output/scripts output/audio
mkdir -p output/scripts output/audio output/images
```

### Certificado SSL inválido (desenvolvimento)

```bash
# Normal em ambiente dev com certificados self-signed
# O código já suprime esses warnings

# Para produção, use certificados válidos no Traefik
```

### Health check falha

```bash
# Verificar health status
docker inspect pipeline-manager | grep -A 10 Health
docker inspect piper-tts | grep -A 10 Health

# Restart do serviço
make clean
make pipeline
```

## 🤝 Contribuindo

Contribuições são bem-vindas! Por favor:

1. Fork o projeto
2. Crie uma branch (`git checkout -b feature/nova-feature`)
3. Commit suas mudanças (`git commit -am 'Adiciona nova feature'`)
4. Push para a branch (`git push origin feature/nova-feature`)
5. Abra um Pull Request

## 📝 License

Este projeto está sob a licença MIT. Consulte [LICENSE](LICENSE) para mais detalhes.

**Nota sobre Piper TTS:** A partir da v1.3.0, o Piper TTS é GPL-3.0. Consulte [docs/MIGRATION_PIPER.md](docs/MIGRATION_PIPER.md).

## 🙏 Agradecimentos

- **[Ollama](https://github.com/ollama/ollama)** - LLM runtime
- **[Piper TTS](https://github.com/OHF-Voice/piper1-gpl)** - Text-to-Speech
- **[Traefik](https://traefik.io/)** - Reverse proxy
- Comunidade open-source ❤️

---

**Desenvolvido com ❤️ para automação de conteúdo**

Para mais informações, consulte a [documentação completa](docs/) ou abra uma [issue](https://github.com/seu-usuario/audio-pipeline/issues).
