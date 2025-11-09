## 🔧 Correções Aplicadas - 09 Nov 2025

### Problema 1: Tag v1.3.1 não existe ❌

**Erro Original**:
```
fatal: Remote branch v1.3.1 not found in upstream origin
```

**Causa**:
O repositório OHF-Voice/piper1-gpl não tem a tag `v1.3.1` ainda. O projeto está em desenvolvimento ativo mas sem releases taggeadas.

**Solução Aplicada**:
Modificado `Dockerfile.piper` para usar branch `main` (última versão):

```dockerfile
# ANTES (não funcionava)
RUN git clone --depth 1 --branch v1.3.1 https://github.com/OHF-Voice/piper1-gpl.git .

# DEPOIS (funciona)
RUN git clone --depth 1 https://github.com/OHF-Voice/piper1-gpl.git .
```

**Versão Resultante**: ~1.3.0+ (branch main, última versão estável)

---

### Problema 2: Stable Diffusion não está rodando ❌

**Erro**:
```
Failed to resolve 'stable-diffusion-api' ([Errno -2] Name or service not known)
```

**Causa**:
O serviço `stable-diffusion-api` não foi iniciado antes de executar `make image-manager`.

**Solução**:
Você precisa iniciar o Stable Diffusion ANTES de gerar imagens:

```bash
# 1. Iniciar Stable Diffusion
make images

# 2. Aguardar ficar pronto (2-5 minutos na primeira vez)
docker logs -f stable-diffusion-api
# Aguarde até ver: "Startup time: XX.XXs"

# 3. ENTÃO executar geração de imagens
make image-manager
```

**OU use o comando completo**:
```bash
make full-pipeline
# Isso faz: build + local-ollama + images + pipeline + image-manager
```

---

### Problema 3: Warning "version is obsolete"

**Warning**:
```
WARN[0000] the attribute `version` is obsolete
```

**Causa**: Docker Compose v2 não precisa mais de `version: "3.9"` nos arquivos YAML.

**Solução**: Opcional, mas pode remover as linhas `version: "3.9"` dos arquivos:
- `docker-compose.tts.yml`
- `docker-compose.manager.yml`
- `docker-compose.images.yml`
- `docker-compose.ollama.yml`

Não afeta funcionalidade, apenas gera warning.

---

## ✅ Comandos Corrigidos para Executar

### Opção 1: Migração Piper TTS (Corrigida)

```bash
cd /home/cloud/dev/homelab/supertest

# Migrar Piper TTS com versão correta (branch main)
make -f Makefile.piper migrate

# Aguardar conclusão (~3-5 minutos na primeira vez)
# - Build da imagem
# - Download da voz pt_BR-faber-medium (~80MB)

# Verificar logs
make -f Makefile.piper logs

# Testar
make -f Makefile.piper test
```

### Opção 2: Pipeline Básico (Scripts + Áudio) - SEM Imagens

```bash
# Se TTS já está rodando da migração acima, pular make tts

# Build do pipeline
make build

# Executar pipeline (gera scripts + áudio)
make manager

# Ver resultados
make monitor
ls -lh output/scripts/
ls -lh output/audio/
```

### Opção 3: Pipeline Completo (COM Imagens)

```bash
# 1. Iniciar Stable Diffusion (ANTES de gerar imagens)
make images

# 2. Aguardar SD ficar pronto (em outro terminal)
docker logs -f stable-diffusion-api
# Aguarde ver: "Startup time: XX.XXs" ou "Running on local URL"

# 3. Verificar que SD está rodando
docker ps | grep stable-diffusion
curl -s http://localhost:7860/ | grep -i stable

# 4. ENTÃO executar pipeline completo
make full-pipeline

# OU separado:
make pipeline         # Scripts + Áudio
make image-manager    # Imagens
```

---

## 🧪 Teste Rápido do TTS (Após Correção)

```bash
# Testar API do Piper TTS diretamente
curl -X POST http://localhost:5000 \
  -H 'Content-Type: application/json' \
  -d '{"text": "Teste corrigido com sucesso!"}' \
  -o /tmp/teste_corrigido.wav

# Ver informações do arquivo
file /tmp/teste_corrigido.wav
# Deve mostrar: RIFF (little-endian) data, WAVE audio, Microsoft PCM, 16 bit, mono 22050 Hz

# Reproduzir (se tiver ffplay)
ffplay /tmp/teste_corrigido.wav
```

---

## 📊 Ordem de Execução Atualizada

```bash
# PASSO 1: Migrar Piper TTS (corrigido)
make -f Makefile.piper migrate
# Aguardar conclusão + testar

# PASSO 2: Build do pipeline
make build

# PASSO 3A: Pipeline básico (SEM imagens)
make manager
make monitor

# OU

# PASSO 3B: Pipeline completo (COM imagens)
make images              # Iniciar SD primeiro
sleep 180                # Aguardar 3 minutos
make pipeline            # Scripts + Áudio
make image-manager       # Imagens
make monitor             # Ver resultados
```

---

## 🔍 Verificação de Saúde

```bash
# Verificar containers rodando
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# Esperado após migração TTS:
# piper-tts    Up XX minutes (healthy)   0.0.0.0:5000->5000/tcp

# Esperado após make images:
# stable-diffusion-api   Up XX minutes   0.0.0.0:7860->7860/tcp

# Testar endpoints
curl -s http://localhost:5000/voices | jq .        # Piper TTS
curl -s http://localhost:7860/ | grep -i stable   # Stable Diffusion
```

---

## 📝 Notas Importantes

1. **Versão do Piper**: Agora usa branch `main` (última versão estável ~1.3.0+)
2. **Não há tag v1.3.1**: Projeto OHF-Voice ainda não criou releases taggeadas
3. **SD é opcional**: Pipeline básico funciona sem Stable Diffusion
4. **Primeira execução demora**: Build + downloads podem levar 5-10 minutos total

---

**Última Atualização**: 09 Novembro 2025 18:15
**Status**: ✅ Correções aplicadas, pronto para testar
