# 🚀 Guia de Execução - Pipeline de Geração de Conteúdo IA

**Data**: 09 Novembro 2025
**Status**: Projeto com Piper TTS v1.3.1 (GPL) migrado ✅

---

## 📋 Pré-requisitos

### 1. Verificar Ambiente

```bash
# Verificar se está no diretório correto
pwd
# Esperado: /home/cloud/dev/homelab/supertest

# Verificar se .env existe
ls -la .env
# Se não existir: cp .env.example .env

# Verificar rede Traefik
docker network ls | grep proxy_net
# Se não existir: docker network create proxy_net
```

### 2. Configurar Variáveis de Ambiente

Edite o arquivo `.env`:

```bash
nano .env
```

**Variáveis críticas**:
```bash
# Rede
TRAEFIK_NETWORK=proxy_net

# Domínios (ajustar conforme seu ambiente)
DOMAIN_DUCKDNS=drake-ayu.duckdns.org
DOMAIN_LOCAL=drake-ayu.local

# Ollama (OBRIGATÓRIO - deve estar rodando)
OLLAMA_BASE_URL=https://ollama.drake-ayu.duckdns.org
# OU para local: OLLAMA_BASE_URL=http://ollama:11434

# TTS
TTS_SERVICE_NAME=piper-tts
TTS_PORT=5000  # IMPORTANTE: Mudei de 8090 para 5000 (padrão Piper v1.3.1)

# Stable Diffusion (opcional para começar)
SD_API_URL=http://stable-diffusion-api:7860/sdapi/v1/txt2img
```

**⚠️ ATENÇÃO**: A porta do TTS deve ser `5000` (padrão da nova versão Piper v1.3.1)

### 3. Atualizar .env se necessário

Se você ainda tem `TTS_PORT=8090` no `.env`, precisa mudar para `5000`:

```bash
# Verificar porta atual
grep TTS_PORT .env

# Se for 8090, mudar para 5000:
sed -i 's/TTS_PORT=8090/TTS_PORT=5000/' .env

# Confirmar mudança
grep TTS_PORT .env
# Deve mostrar: TTS_PORT=5000
```

---

## 🎯 Ordem de Execução Recomendada

### **OPÇÃO 1: Migração e Teste do Piper TTS (Primeiro)**

Comece testando apenas a migração do TTS antes do pipeline completo:

```bash
# Passo 1: Migração automática do Piper TTS
make -f Makefile.piper migrate

# O que isso faz:
# 1. Para versão antiga (se existir)
# 2. Build da imagem piper-tts:1.3.1-gpl
# 3. Inicia container
# 4. Aguarda 60s para download da voz pt_BR-faber-medium
# 5. Testa API HTTP

# Passo 2: Verificar logs
make -f Makefile.piper logs
# Procurar por:
# ✅ "📥 Baixando voz pt_BR-faber-medium..."
# ✅ "🚀 Iniciando Piper TTS HTTP Server v1.3.1 (GPL)"
# ✅ Sem erros de "Voice not found"

# Passo 3: Testar API manualmente
make -f Makefile.piper test

# Ou com curl direto:
curl -X POST http://localhost:5000 \
  -H 'Content-Type: application/json' \
  -d '{"text": "Teste de migração bem-sucedido!"}' \
  -o /tmp/teste_piper.wav

# Ouvir áudio (se tiver ffplay):
ffplay /tmp/teste_piper.wav

# Passo 4: Verificar health
make -f Makefile.piper status
# Container deve estar "healthy"
```

**✅ Se tudo acima funcionar, prosseguir para OPÇÃO 2**

---

### **OPÇÃO 2: Pipeline Básico (Scripts + Áudio)**

Após validar o Piper TTS:

```bash
# Passo 1: Build da imagem do pipeline
make build
# Cria: audio-pipeline-app:latest

# Passo 2: Verificar se Ollama está acessível
curl -s https://ollama.drake-ayu.duckdns.org/api/tags | jq .
# Deve retornar lista de modelos

# Passo 3: Preparar arquivo de entrada
cat input/topics.txt
# Deve ter pelo menos um tópico, ex: "Inteligência Artificial"

# Passo 4: Executar pipeline básico
make pipeline

# O que isso faz:
# 1. Build da imagem (se necessário)
# 2. Inicia piper-tts (se não estiver rodando)
# 3. Executa manager:
#    - generate_scripts.py (Ollama gera roteiros)
#    - text_to_speech.py (Piper converte para áudio)

# Passo 5: Monitorar execução
# Em outro terminal:
docker logs -f pipeline-manager

# Passo 6: Verificar resultados
make monitor

# Ou manualmente:
ls -lh output/scripts/
ls -lh output/audio/
```

**Possíveis saídas**:

✅ **Sucesso**:
```
=== SCRIPTS GERADOS ===
-rw-r--r-- 1 user user 1.5K Nov  9 14:30 script_001.txt
-rw-r--r-- 1 user user 1.8K Nov  9 14:31 script_002.txt

=== ÁUDIOS GERADOS ===
-rw-r--r-- 1 user user 450K Nov  9 14:32 script_001.wav
-rw-r--r-- 1 user user 520K Nov  9 14:33 script_002.wav
```

❌ **Erro comum**: "TTS não acessível"
```bash
# Verificar se piper-tts está rodando
docker ps | grep piper-tts

# Se não estiver, iniciar manualmente:
make tts

# Aguardar 60s para download da voz
sleep 60

# Verificar logs:
docker logs piper-tts

# Tentar novamente:
make manager
```

---

### **OPÇÃO 3: Pipeline Completo (Scripts + Áudio + Imagens)**

Requer Stable Diffusion rodando:

```bash
# Passo 1: Iniciar Stable Diffusion
make images

# Passo 2: Aguardar SD estar pronto (pode demorar 2-5min)
docker logs -f stable-diffusion-api
# Procurar por: "Startup time:"

# Passo 3: Testar SD API
curl -X POST http://localhost:7860/sdapi/v1/txt2img \
  -H 'Content-Type: application/json' \
  -d '{
    "prompt": "test",
    "steps": 1,
    "width": 512,
    "height": 512
  }'

# Passo 4: Executar pipeline completo
make full-pipeline

# Ou passo a passo:
make pipeline              # Scripts + Áudio
make image-manager         # Imagens

# Passo 5: Verificar imagens geradas
ls -lh output/images/
```

---

## 🧪 Testes Individuais

### Teste 1: Geração de Scripts (Ollama)

```bash
# Apenas gerar scripts (sem áudio)
docker-compose -f docker-compose.manager.yml run --rm manager \
  python generate_scripts.py

# Verificar scripts gerados
ls -lh output/scripts/
cat output/scripts/script_001.txt
```

### Teste 2: Conversão TTS (Piper)

```bash
# Assumindo que já tem scripts em output/scripts/

# Apenas converter para áudio
docker-compose -f docker-compose.manager.yml run --rm manager \
  python text_to_speech.py

# Verificar áudios gerados
ls -lh output/audio/
```

### Teste 3: Geração de Imagens (SD)

```bash
# Assumindo que já tem scripts em output/scripts/

# Apenas gerar imagens
docker-compose -f docker-compose.manager.yml run --rm image-generator

# Verificar imagens geradas
ls -lh output/images/
```

---

## 🐛 Troubleshooting

### Problema 1: "TTS_PORT mismatch"

**Sintoma**: Container piper-tts não inicia ou health check falha

**Causa**: `.env` tem porta antiga (8090) mas Piper v1.3.1 usa 5000

**Solução**:
```bash
# Verificar porta em .env
grep TTS_PORT .env

# Se for 8090, corrigir:
sed -i 's/TTS_PORT=8090/TTS_PORT=5000/' .env

# Recriar container
docker-compose -f docker-compose.tts.yml down
docker-compose -f docker-compose.tts.yml up -d

# Verificar saúde
docker ps | grep piper-tts
# Status deve ser "healthy" após ~60s
```

### Problema 2: "Voice not found: pt_BR-faber-medium"

**Sintoma**: Logs do piper-tts mostram erro de voz não encontrada

**Causa**: Download da voz falhou ou volume não foi criado

**Solução**:
```bash
# Download manual da voz
docker exec -it piper-tts \
  python3 -m piper.download_voices pt_BR-faber-medium --data-dir /data

# Verificar se foi baixado
docker exec -it piper-tts ls -lh /data/
# Deve ter: pt_BR-faber-medium.onnx e pt_BR-faber-medium.onnx.json

# Restart container
docker restart piper-tts
```

### Problema 3: "Ollama não acessível"

**Sintoma**: `generate_scripts.py` falha com erro de conexão

**Causa**: Ollama não está rodando ou URL incorreta

**Solução**:
```bash
# Verificar URL no .env
grep OLLAMA_BASE_URL .env

# Testar conectividade
curl -s $OLLAMA_BASE_URL/api/tags

# Se local, iniciar Ollama:
make local-ollama

# Se externo, verificar se está rodando:
# curl -s https://ollama.drake-ayu.duckdns.org/api/tags
```

### Problema 4: "Rede proxy_net não encontrada"

**Sintoma**: Containers falham ao iniciar com erro de rede

**Causa**: Rede Traefik não existe

**Solução**:
```bash
# Criar rede manualmente
docker network create proxy_net

# Ou usar Makefile:
make test-network

# Verificar
docker network ls | grep proxy_net
```

### Problema 5: "Permission denied" em output/

**Sintoma**: Scripts falham ao salvar arquivos

**Causa**: Permissões incorretas nos diretórios

**Solução**:
```bash
# Ajustar permissões (UID 1000 = appuser no container)
sudo chown -R 1000:1000 output/
sudo chmod -R 755 output/

# Ou se preferir seu usuário:
sudo chown -R $USER:$USER output/
```

---

## 📊 Checklist de Validação

### ✅ Pré-Execução

- [ ] Arquivo `.env` existe e está configurado
- [ ] `TTS_PORT=5000` (não 8090)
- [ ] Rede `proxy_net` criada
- [ ] Ollama acessível (testar com curl)
- [ ] Diretórios `input/`, `output/scripts/`, `output/audio/`, `output/images/` existem
- [ ] Arquivo `input/topics.txt` tem pelo menos 1 tópico

### ✅ Pós-Migração Piper TTS

- [ ] Container `piper-tts` está rodando
- [ ] Status é "healthy" (após ~60s)
- [ ] Voz `pt_BR-faber-medium` foi baixada
- [ ] Endpoint `/voices` responde
- [ ] Síntese de áudio funciona (curl test)

### ✅ Pós-Pipeline Básico

- [ ] Imagem `audio-pipeline-app:latest` foi criada
- [ ] Scripts foram gerados em `output/scripts/`
- [ ] Áudios foram gerados em `output/audio/`
- [ ] Arquivos `.wav` são válidos (podem ser reproduzidos)

### ✅ Pós-Pipeline Completo

- [ ] Container `stable-diffusion-api` está rodando
- [ ] Imagens foram geradas em `output/images/`
- [ ] Arquivos `.png` são válidos (podem ser visualizados)

---

## 🎯 Fluxo Recomendado para Primeira Execução

```bash
# 1. Preparação
cd /home/cloud/dev/homelab/supertest
cp .env.example .env
nano .env  # Ajustar variáveis

# 2. Verificar pré-requisitos
make test-network
curl -s $OLLAMA_BASE_URL/api/tags | jq .

# 3. Migrar Piper TTS (CRÍTICO)
make -f Makefile.piper migrate
# Aguardar conclusão (~2-3 minutos)

# 4. Validar TTS
make -f Makefile.piper test

# 5. Build do pipeline
make build

# 6. Executar pipeline básico
make pipeline

# 7. Monitorar resultados
make monitor

# 8. (Opcional) Pipeline completo com imagens
make images  # Iniciar SD (demorado)
# Aguardar 5 minutos
make image-manager
```

---

## 📚 Arquivos de Referência

- **Migração TTS**: `MIGRATION_PIPER.md` - Detalhes da atualização Piper v1.3.1
- **Guia Rápido TTS**: `README_PIPER.md` - Comandos específicos do TTS
- **Análise Técnica**: `TECH_ANALYSIS.md` - Comparação de tecnologias
- **README Principal**: `README.md` - Visão geral do projeto

---

## 🆘 Suporte

**Logs importantes**:
```bash
# Piper TTS
docker logs piper-tts

# Pipeline manager
docker logs pipeline-manager

# Image generator
docker logs image-generator

# Stable Diffusion
docker logs stable-diffusion-api
```

**Limpeza completa** (se precisar recomeçar):
```bash
make clean
docker system prune -f
make -f Makefile.piper clean
```

---

**Última Atualização**: 09 Novembro 2025
**Versão do Projeto**: Pipeline v1.0 + Piper TTS v1.3.1 (GPL)
