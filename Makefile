# ============================================
# Audio Pipeline - Makefile Consolidado
# ============================================
include .env

.PHONY: help

# Configurações
INPUT_FILE ?= data/input/topics.txt
COMPOSE_TTS := deploy/docker-compose.tts.yml
COMPOSE_MANAGER := deploy/docker-compose.manager.yml
COMPOSE_IMAGES := deploy/docker-compose.images.yml
COMPOSE_OLLAMA := deploy/docker-compose.ollama.yml

# Quality gates configuration
DISABLE_GATES ?= 0
STRICT ?= 0

# ============================================
# HELP
# ============================================
help: ## Mostra esta mensagem de ajuda
	@echo "┌────────────────────────────────────────────────────────────┐"
	@echo "│  🎯 Audio Pipeline - Comandos Disponíveis                 │"
	@echo "└────────────────────────────────────────────────────────────┘"
	@echo ""
	@echo "═══ 🔧 SETUP INICIAL ═══"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; /^[^#]/ && /## SETUP/ {printf "  \033[36m%-20s\033[0m %s\n", $$1, substr($$2, 8)}'
	@echo ""
	@echo "═══ 🎙️  PIPER TTS ═══"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; /^[^#]/ && /## TTS/ {printf "  \033[36m%-20s\033[0m %s\n", $$1, substr($$2, 6)}'
	@echo ""
	@echo "═══ 🤖 OLLAMA ═══"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; /^[^#]/ && /## OLLAMA/ {printf "  \033[36m%-20s\033[0m %s\n", $$1, substr($$2, 9)}'
	@echo ""
	@echo "═══ 🚀 PIPELINE ═══"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; /^[^#]/ && /## PIPELINE/ {printf "  \033[36m%-20s\033[0m %s\n", $$1, substr($$2, 11)}'
	@echo ""
	@echo "═══ ✅ QUALITY GATES ═══"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; /^[^#]/ && /## QUALITY/ {printf "  \033[36m%-20s\033[0m %s\n", $$1, substr($$2, 10)}'
	@echo ""
	@echo "═══ 📊 MONITORAMENTO ═══"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; /^[^#]/ && /## MONITOR/ {printf "  \033[36m%-20s\033[0m %s\n", $$1, substr($$2, 10)}'
	@echo ""
	@echo "═══ 🧹 LIMPEZA ═══"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; /^[^#]/ && /## CLEAN/ {printf "  \033[36m%-20s\033[0m %s\n", $$1, substr($$2, 8)}'
	@echo ""
	@echo "💡 Primeiro uso: make setup && make pipeline"
	@echo "📚 Documentação: docs/DEPLOYMENT.md"

# ============================================
# SETUP
# ============================================
setup: ## SETUP: Setup completo do projeto
	@echo "🔧 Configurando projeto..."
	@$(MAKE) check-env
	@$(MAKE) check-network
	@$(MAKE) build
	@echo "✅ Setup concluído!"

check-env: ## SETUP: Verifica se .env existe
	@test -f .env || (echo "❌ .env não encontrado! Copie .env.example para .env" && exit 1)
	@echo "✅ .env encontrado"

check-network: ## SETUP: Verifica rede Traefik
	@echo "🔗 Verificando rede $(TRAEFIK_NETWORK)..."
	@docker network inspect $(TRAEFIK_NETWORK) >/dev/null 2>&1 && \
		echo "✅ Rede $(TRAEFIK_NETWORK) existe" || \
		(echo "❌ Rede $(TRAEFIK_NETWORK) não encontrada! Inicie o Traefik primeiro." && exit 1)

build: ## SETUP: Build da imagem pipeline
	@echo "🔨 Construindo imagem audio-pipeline-app..."
	@docker compose --env-file .env -f $(COMPOSE_MANAGER) build

# ============================================
# PIPER TTS
# ============================================
tts-build: ## TTS: Build da imagem Piper TTS
	@echo "🔨 Building Piper TTS v1.3.1 (GPL)..."
	@docker compose --env-file .env -f $(COMPOSE_TTS) build piper-tts

tts-up: ## TTS: Inicia Piper TTS
	@echo "🚀 Iniciando Piper TTS..."
	@docker compose --env-file .env -f $(COMPOSE_TTS) up -d piper-tts
	@echo "✅ Piper TTS iniciado!"

tts-down: ## TTS: Para Piper TTS
	@echo "🛑 Parando Piper TTS..."
	@docker compose --env-file .env -f $(COMPOSE_TTS) down

tts-logs: ## TTS: Logs do Piper TTS
	@docker compose --env-file .env -f $(COMPOSE_TTS) logs -f piper-tts

tts-status: ## TTS: Status do Piper TTS
	@echo "📊 Status do Piper TTS:"
	@docker compose --env-file .env -f $(COMPOSE_TTS) ps piper-tts
	@docker inspect --format='Health: {{.State.Health.Status}}' piper-tts 2>/dev/null || echo "Container não encontrado"

tts-test: ## TTS: Testa API do Piper TTS
	@echo "🧪 Testando Piper TTS..."
	@echo "Testando endpoint /voices:"
	@curl -s https://$(TTS_SERVICE_NAME).$(DOMAIN_DUCKDNS)/voices | jq -r 'keys' || echo "❌ Falha ao listar vozes"
	@echo ""
	@echo "Testando síntese de áudio:"
	@mkdir -p data/output/audio
	@curl -X POST https://$(TTS_SERVICE_NAME).$(DOMAIN_DUCKDNS) \
		-H 'Content-Type: application/json' \
		-d '{"text": "Teste de migração bem-sucedido! Piper TTS versão 1.3.0 GPL funcionando via Traefik."}' \
		-o data/output/audio/teste_migracao.wav && echo "✅ Áudio salvo em data/output/audio/teste_migracao.wav" || echo "❌ Falha na síntese"
	@echo "✅ Teste concluído"

tts-migrate: ## TTS: Migração completa do Piper TTS
	@echo "🔄 Migrando Piper TTS para v1.3.1 (GPL)..."
	@$(MAKE) tts-down
	@$(MAKE) tts-build
	@$(MAKE) tts-up
	@sleep 10
	@$(MAKE) tts-test
	@echo "✅ Migração concluída!"

tts-shell: ## TTS: Shell no container Piper
	@docker exec -it piper-tts bash

# ============================================
# OLLAMA
# ============================================
ollama-up: ## OLLAMA: Inicia Ollama local
	@echo "🤖 Iniciando Ollama local..."
	@docker compose --env-file .env -f $(COMPOSE_OLLAMA) up -d
	@echo "✅ Ollama iniciado!"

ollama-down: ## OLLAMA: Para Ollama local
	@docker compose --env-file .env -f $(COMPOSE_OLLAMA) down

ollama-logs: ## OLLAMA: Logs do Ollama
	@docker compose --env-file .env -f $(COMPOSE_OLLAMA) logs -f ollama

ollama-test: ## OLLAMA: Testa Ollama
	@echo "🧪 Testando Ollama..."
	@curl -sk $(OLLAMA_BASE_URL)/api/tags | jq -r '.models[0].name' || echo "❌ Falha"

ollama-pull: ## OLLAMA: Pull do modelo configurado
	@echo "📥 Baixando modelo $(OLLAMA_MODEL)..."
	@docker exec -it ollama ollama pull $(OLLAMA_MODEL)

# ============================================
# PIPELINE
# ============================================
scripts-pipeline: ## PIPELINE: Executa pipeline de scripts (geração + quality)
	@echo "📝 Executando pipeline de scripts..."
	@docker compose --env-file .env -f $(COMPOSE_MANAGER) run --rm -e INPUT_FILE=$(INPUT_FILE) manager python -m src.generators.script_generator
	@$(MAKE) quality-scripts

audio-pipeline: ## PIPELINE: Executa pipeline de áudio (geração + quality)
	@echo "🔊 Executando pipeline de áudio..."
	@docker compose --env-file .env -f $(COMPOSE_MANAGER) run --rm manager python -m src.generators.audio_generator
	@$(MAKE) quality-audio

pipeline: build tts-up scripts-pipeline audio-pipeline ## PIPELINE: Executa pipeline completo (scripts + áudio + quality gates)

pipeline-without-gates: ## PIPELINE: Pipeline completo sem quality gates
	@echo "🎯 Executando pipeline sem quality gates..."
	@DISABLE_GATES=1 $(MAKE) build tts-up
	@DISABLE_GATES=1 INPUT_FILE=$(INPUT_FILE) docker compose --env-file .env -f $(COMPOSE_MANAGER) up manager

pipeline-full: build ollama-up tts-up scripts-pipeline audio-pipeline ## PIPELINE: Pipeline com Ollama local

manager: ## PIPELINE: Executa geração de scripts e áudio (legacy)
	@echo "🎯 Executando pipeline..."
	@INPUT_FILE=$(INPUT_FILE) docker compose --env-file .env -f $(COMPOSE_MANAGER) up manager

image-generator: ## PIPELINE: Executa geração de imagens
	@echo "🎨 Executando geração de imagens..."
	@docker compose --env-file .env -f $(COMPOSE_MANAGER) run --rm image-generator

# ============================================
# QUALITY GATES
# ============================================
quality-scripts: ## QUALITY: Executa quality gates para scripts
	@echo "✅ Executando quality gates para scripts..."
	@DISABLE_GATES=$(DISABLE_GATES) STRICT=$(STRICT) docker compose --env-file .env -f $(COMPOSE_MANAGER) run --rm manager python src/check_script_quality.py

quality-audio: ## QUALITY: Executa quality gates para áudio
	@echo "✅ Executando quality gates para áudio..."
	@DISABLE_GATES=$(DISABLE_GATES) STRICT=$(STRICT) docker compose --env-file .env -f $(COMPOSE_MANAGER) run --rm manager python src/check_audio_quality.py

quality-gates: quality-scripts quality-audio ## QUALITY: Executa todos os quality gates

list-failures: ## QUALITY: Lista artefatos reprovados
	@docker compose --env-file .env -f $(COMPOSE_MANAGER) run --rm manager python src/list_failures.py

generate-summary: ## QUALITY: Gera relatório consolidado
	@docker compose --env-file .env -f $(COMPOSE_MANAGER) run --rm manager python src/generate_summary.py

# ============================================
# MONITORAMENTO
# ============================================
monitor: ## MONITOR: Monitora outputs gerados
	@echo "📊 Monitorando outputs..."
	@echo ""
	@echo "═══ SCRIPTS ═══"
	@ls -lh data/output/scripts/*.txt 2>/dev/null | tail -n +2 | awk '{print $$9, "(" $$5 ")"}' || echo "  Nenhum script"
	@echo ""
	@echo "═══ ÁUDIOS ═══"
	@ls -lh data/output/audio/*.wav 2>/dev/null | tail -n +2 | awk '{print $$9, "(" $$5 ")"}' || echo "  Nenhum áudio"
	@echo ""
	@echo "═══ IMAGENS ═══"
	@ls -lh data/output/images/*.png 2>/dev/null | tail -n +2 | awk '{print $$9, "(" $$5 ")"}' || echo "  Nenhuma imagem"
	@echo ""
	@echo "═══ CONTAINERS ═══"
	@docker ps --format "table {{.Names}}\t{{.Status}}" | grep -E "(piper-tts|ollama|pipeline-manager)" || echo "  Nenhum container ativo"

logs: ## MONITOR: Logs do pipeline manager
	@docker compose --env-file .env -f $(COMPOSE_MANAGER) logs -f manager

status: ## MONITOR: Status de todos os serviços
	@echo "📊 Status dos serviços:"
	@echo ""
	@docker compose --env-file .env -f $(COMPOSE_TTS) ps 2>/dev/null
	@docker compose --env-file .env -f $(COMPOSE_MANAGER) ps 2>/dev/null

status-full: ## MONITOR: Status completo com Ollama
	@$(MAKE) status
	@docker compose --env-file .env -f $(COMPOSE_OLLAMA) ps 2>/dev/null

test-services: ## MONITOR: Testa todos os serviços
	@echo "🧪 Testando serviços..."
	@echo ""
	@$(MAKE) tts-test

test-services-full: ## MONITOR: Testa todos os serviços com Ollama
	@$(MAKE) test-services
	@$(MAKE) ollama-test

# ============================================
# LIMPEZA
# ============================================
clean: ## CLEAN: Para todos os containers
	@echo "🧹 Limpando containers..."
	@docker compose --env-file .env -f $(COMPOSE_TTS) down
	@docker compose --env-file .env -f $(COMPOSE_OLLAMA) down
	@docker compose --env-file .env -f $(COMPOSE_MANAGER) down
	@echo "✅ Containers parados"

clean-all: clean ## CLEAN: Para containers e remove volumes
	@echo "🗑️  Removendo volumes..."
	@docker compose --env-file .env -f $(COMPOSE_TTS) down -v
	@docker volume rm piper-voices 2>/dev/null || true
	@echo "✅ Volumes removidos"

clean-all-full: clean-all ## CLEAN: Limpa tudo incluindo volumes Ollama
	@echo "🗑️  Removendo volumes Ollama..."
	@docker compose --env-file .env -f $(COMPOSE_OLLAMA) down -v
	@docker volume rm ollama_data 2>/dev/null || true
	@echo "✅ Volumes removidos"

clean-outputs: ## CLEAN: Limpa outputs gerados
	@echo "🗑️  Limpando outputs..."
	@rm -f data/output/scripts/*.txt
	@rm -f data/output/audio/*.wav
	@rm -f data/output/images/*.png
	@echo "✅ Outputs limpos"

backup: ## CLEAN: Backup de outputs e config
	@echo "💾 Criando backup..."
	@mkdir -p backups
	@tar -czf backups/outputs_$$(date +%Y%m%d_%H%M%S).tar.gz data/output/
	@tar -czf backups/config_$$(date +%Y%m%d_%H%M%S).tar.gz config/ data/input/
	@echo "✅ Backup criado em backups/"

# ============================================
# ATALHOS
# ============================================
dev: clean setup pipeline monitor ## Desenvolvimento rápido

.DEFAULT_GOAL := help
