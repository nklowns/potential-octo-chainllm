# 🚀 Deployment Guide - Audio Pipeline

**Last Updated**: November 10, 2025
**Status**: Ready for execution with new `data/` structure

---

## 📋 Prerequisites

### 1. System Requirements

- Docker 20.10+
- Docker Compose v2.0+
- Make
- Network access to external services OR local Ollama/Stable Diffusion

### 2. Network Setup

```bash
# Create Docker network if it doesn't exist
docker network create proxy_net
```

### 3. Environment Configuration

```bash
# Copy example environment file
cp .env.example .env

# Edit configuration as needed
nano .env
```

**Critical variables (infra)**:
- `TRAEFIK_NETWORK=proxy_net` - Docker network name
- `OLLAMA_BASE_URL` - URL for Ollama service (local or external)
- `PIPER_SERVICE_NAME` / `PIPER_PORT` - Identificação e porta do serviço Piper (Traefik / Compose)
- `DOMAIN_DUCKDNS` - Your domain (if using external services)

---

## ⚡ Quick Start

### First-Time Setup

```bash
# 1. Navigate to project directory
cd /path/to/potential-octo-chainllm

# 2. Complete setup (verify env, network, build images)
make setup

# 3. Start Piper TTS service
make tts-up

# 4. Wait for TTS to be ready (~30 seconds)
make tts-status

# 5. Run the pipeline (generates scripts + audio)
make pipeline

# 6. Monitor the results
make monitor
```

### Subsequent Runs

```bash
# Simply run the pipeline
make pipeline

# Or run the full pipeline with Ollama local
make pipeline-full
```

---

## 🎯 Available Commands

### Setup Commands

```bash
make setup           # Complete project setup
make check-env       # Verify .env file exists
make check-network   # Verify Docker network exists
make build           # Build pipeline images
```

### Pipeline Execution

```bash
make pipeline        # Run pipeline (scripts + audio)
make pipeline-full   # Run pipeline with local Ollama
make manager         # Run script and audio generation only
make image-generator # Run image generation only
```

### Service Management

```bash
# Piper TTS
make tts-up          # Start Piper TTS
make tts-down        # Stop Piper TTS
make tts-status      # Check TTS status
make tts-test        # Test TTS API
make tts-logs        # View TTS logs

# Ollama (if using local)
make ollama-up       # Start local Ollama
make ollama-down     # Stop local Ollama
make ollama-pull     # Pull configured model
make ollama-test     # Test Ollama API
```

### Monitoring

```bash
make monitor         # Monitor generated outputs
make status          # Check service status
make logs            # View pipeline logs
make test-services   # Test all services
```

### Cleanup

```bash
make clean           # Stop all containers
make clean-outputs   # Delete generated outputs
make clean-all       # Stop containers and remove volumes
make backup          # Backup outputs and config
```

---

## 📁 Directory Structure

```
audio-pipeline/
├── data/                        # Data directory (bind mounts)
│   ├── input/
│   │   └── topics.txt          # Input topics (one per line)
│   └── output/
│       ├── scripts/            # Generated scripts (.txt)
│       ├── audio/              # Generated audio (.wav)
│       └── images/             # Generated images (.png)
├── config/                      # Configuration files
│   ├── prompts/
│   │   └── script_template.txt # Script generation template
│   ├── schemas/
│   │   └── script_v1.json     # Script schema
│   └── voices.json             # TTS voice configurations
└── deploy/                      # Docker Compose files
    ├── docker-compose.manager.yml
    ├── docker-compose.tts.yml
    ├── docker-compose.ollama.yml
    └── docker-compose.images.yml
```

---

## 🔧 Configuration

### Input Topics

Edit `data/input/topics.txt` with your topics (one per line):

```
Tecnologia Docker para desenvolvedores
Inteligência Artificial no dia a dia
Python para automação de tarefas
```

### Prompt Template

Customize the script generation template at `config/prompts/script_template.txt`.

### TTS (Piper) Configuration

Voices and backend endpoints are defined centrally in `config/voices.json` (v2):

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
        "piper_pt_br": { "backend": "piper", "model_id": "pt_BR-faber-medium", "params": {} },
        "piper_pt_br_alt": { "backend": "piper", "model_id": "pt_BR-cadu-medium", "params": { "length_scale": 0.95 } }
    }
}
```

Nenhuma variável `TTS_*` é usada para controlar voz ou parâmetros. Ajuste tudo pelo JSON.

---

## 🐛 Troubleshooting

### Container Won't Start

```bash
# Check logs
docker logs pipeline-manager

# Check service status
make status

# Verify network
docker network inspect proxy_net
```

### No Output Generated

```bash
# Check if input file exists
cat data/input/topics.txt

# Verify services are running
make test-services

# Check permissions
ls -la data/output/
```

### TTS Not Working

```bash
# Rebuild TTS
make tts-down
make tts-build
make tts-up

# Test API
make tts-test
```

### Ollama Connection Failed

```bash
# If using local Ollama
make ollama-up
make ollama-pull    # Pull the model

# If using external, verify .env
grep OLLAMA_BASE_URL .env
```

---

## 🔒 Security Notes

- All containers run as non-root user (`appuser`)
- Input data mounted as read-only
- Environment variables in `.env` (git-ignored)
- No secrets in source code

---

## 📊 Performance Tips

1. **First run is slower**: Models and voices need to be downloaded
2. **Adjust rate limits**: Set `OLLAMA_RATE_LIMIT` and `TTS_RATE_LIMIT` in `.env`
3. **Use local services**: For better performance, run Ollama and SD locally
4. **Monitor resources**: Use `docker stats` to check resource usage

---

## 🔗 Related Documentation

- [README.md](../README.md) - Project overview and quick start
- [MIGRATION_PIPER.md](MIGRATION_PIPER.md) - Piper TTS migration details
- [TECH_ANALYSIS.md](TECH_ANALYSIS.md) - Technical analysis
- [BEST_PRACTICES.md](BEST_PRACTICES.md) - Development best practices
- [PROJECT_STATUS.md](PROJECT_STATUS.md) - Current project status

---

## 📝 Next Steps

After successful deployment:

1. ✅ Verify all outputs in `data/output/`
2. ✅ Customize prompts in `config/prompts/`
3. ✅ Adjust generation parameters in `.env`
4. ✅ Set up backups: `make backup`
5. ✅ Monitor resource usage
