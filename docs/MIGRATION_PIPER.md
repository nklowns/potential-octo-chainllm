# 🔄 Migração Piper TTS: rhasspy/piper → OHF-Voice/piper1-gpl

**Data**: 09 Novembro 2025
**Motivo**: Projeto original `rhasspy/piper` foi **arquivado** e migrado para `OHF-Voice/piper1-gpl`
**Versão Nova**: v1.3.1 (GPL-3.0)

---

## 📋 Resumo da Migração

| Aspecto | Antes (rhasspy/piper) | Depois (OHF-Voice/piper1-gpl) |
|---------|----------------------|-------------------------------|
| **Repositório** | `rhasspy/piper` (ARQUIVADO) | `OHF-Voice/piper1-gpl` ✅ |
| **Licença** | MIT | **GPL-3.0** ⚠️ |
| **Versão** | v1.2.0 (última) | v1.3.1 (atual) |
| **Docker Image** | `rhasspy/piper:latest` | Custom build `piper-tts:1.3.1-gpl` |
| **API Endpoint** | `POST /` (text/plain) | `POST /` (application/json) |
| **Status** | ❌ Arquivado | ✅ Mantido ativamente |

---

## 🔧 Mudanças Implementadas

### 1. **Docker Image Atualizada**

#### Antes:
```yaml
services:
  piper-tts:
    image: rhasspy/piper:latest  # Arquivado
    command: ['--model', 'pt_BR/faber/medium', '--host', '0.0.0.0', '--port', '5000']
```

#### Depois:
```yaml
services:
  piper-tts:
    build:
      context: .
      dockerfile: Dockerfile.piper
    image: piper-tts:1.3.1-gpl  # Nova versão GPL
    command: ["server", "-m", "pt_BR-faber-medium", "--host", "0.0.0.0", "--port", "5000"]
    volumes:
      - piper-voices:/data  # Volume persistente para vozes
```

### 2. **Nova API HTTP (Breaking Change)**

#### Antes (text/plain):
```python
response = requests.post(
    "http://piper-tts:5000",
    data=text.encode('utf-8'),
    headers={'Content-Type': 'text/plain'}
)
```

#### Depois (application/json):
```python
response = requests.post(
    "http://piper-tts:5000",
    json={
        "text": text,
        "voice": "pt_BR-faber-medium",
        "length_scale": 1.0,  # Velocidade
        "noise_scale": 0.667,  # Variabilidade
    },
    headers={'Content-Type': 'application/json'}
)
```

### 3. **Download Automático de Vozes**

O novo Dockerfile baixa automaticamente a voz `pt_BR-faber-medium` se não existir:

```bash
# Dentro do container ao iniciar
python3 -m piper.download_voices pt_BR-faber-medium --data-dir /data
```

### 4. **Health Check Melhorado**

```yaml
healthcheck:
  test: ["CMD-SHELL", "curl -f http://localhost:5000/voices || exit 1"]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 60s  # Mais tempo para download inicial da voz
```

---

## 🚀 Como Aplicar a Migração

### Passo 1: Build da Nova Imagem

```bash
cd /home/cloud/dev/homelab/supertest
docker-compose -f docker-compose.tts.yml build piper-tts
```

### Passo 2: Parar Versão Antiga

```bash
docker-compose -f docker-compose.tts.yml down
```

### Passo 3: Iniciar Nova Versão

```bash
docker-compose -f docker-compose.tts.yml up -d piper-tts
```

### Passo 4: Verificar Logs

```bash
docker logs -f piper-tts
```

**Esperado no primeiro boot**:
```
📥 Baixando voz pt_BR-faber-medium...
Downloading https://huggingface.co/rhasspy/piper-voices/.../pt_BR-faber-medium.onnx
🚀 Iniciando Piper TTS HTTP Server v1.3.1 (GPL)
```

### Passo 5: Testar API

```bash
# Testar endpoint /voices
curl http://localhost:5000/voices

# Testar síntese
curl -X POST http://localhost:5000 \
  -H 'Content-Type: application/json' \
  -d '{"text": "Olá, este é um teste de migração."}' \
  -o teste_migracao.wav
```

---

## ⚠️ Mudanças de Licença

### Antes: MIT (Permissivo)
- ✅ Uso comercial livre
- ✅ Modificações livres
- ✅ Sem obrigação de código aberto

### Depois: GPL-3.0 (Copyleft)
- ✅ Uso comercial permitido
- ✅ Modificações permitidas
- ⚠️ **Modificações devem ser compartilhadas com mesma licença**
- ⚠️ **Código que usa Piper deve ser GPL-compatível**

**Implicação para este projeto**:
- ✅ **OK para uso pessoal/homelab** (não distribui software)
- ✅ **OK como serviço interno** (não expõe código fonte)
- ⚠️ **Se distribuir binários**: deve incluir código fonte

---

## 📊 Comparação de Features

| Feature | v1.2.0 (MIT) | v1.3.1 (GPL) | Status |
|---------|--------------|--------------|--------|
| **API HTTP** | ✅ text/plain | ✅ JSON (melhor) | ✅ Migrado |
| **Download Voices** | Manual | ✅ Automático | ✅ Melhor |
| **Streaming** | ✅ Sim | ✅ Sim | ✅ Mantido |
| **Multi-Speaker** | ✅ Sim | ✅ Sim | ✅ Mantido |
| **Python API** | ✅ Sim | ✅ Sim | ✅ Mantido |
| **C/C++ API** | ✅ Sim | 🔄 Em dev | ⏳ Futuro |
| **Alignments** | ❌ Não | ✅ Sim | 🆕 Novo |
| **Raw Phonemes** | ❌ Não | ✅ Sim `[[ ... ]]` | 🆕 Novo |
| **Stable ABI** | ❌ Não | ✅ Sim (Python 3.9+) | 🆕 Novo |

---

## 🐛 Troubleshooting

### Problema: "Voice not found: pt_BR-faber-medium"

**Causa**: Voz não foi baixada
**Solução**:
```bash
docker exec -it piper-tts bash
python3 -m piper.download_voices pt_BR-faber-medium --data-dir /data
```

### Problema: "HTTP 500 Internal Server Error"

**Causa**: JSON payload inválido
**Solução**: Verificar formato do request:
```python
# ✅ CORRETO
payload = {"text": "Olá", "voice": "pt_BR-faber-medium"}

# ❌ ERRADO (antigo)
payload = "Olá".encode('utf-8')
```

### Problema: Build falha com "git clone error"

**Causa**: Sem acesso à internet no builder
**Solução**: Verificar proxy/firewall ou usar cache:
```dockerfile
RUN git config --global http.proxy http://proxy:port
```

---

## 📚 Referências

- **Novo Repositório**: https://github.com/OHF-Voice/piper1-gpl
- **Documentação API HTTP**: https://github.com/OHF-Voice/piper1-gpl/blob/main/docs/API_HTTP.md
- **Changelog v1.3.0**: https://github.com/OHF-Voice/piper1-gpl/blob/main/CHANGELOG.md
- **Vozes Disponíveis**: https://huggingface.co/rhasspy/piper-voices

---

## ✅ Checklist de Migração

- [x] Criar `Dockerfile.piper` com build da v1.3.1
- [x] Atualizar `docker-compose.tts.yml` com novo comando
- [x] Atualizar `text_to_speech.py` com nova API JSON
- [x] Adicionar volume `piper-voices` para cache
- [x] Atualizar health check com endpoint `/voices`
- [x] Documentar mudanças de licença (MIT → GPL-3.0)
- [ ] Testar pipeline completo end-to-end
- [ ] Atualizar `TECH_ANALYSIS.md` com status atualizado
- [ ] Commit e push das mudanças

---

**Última Atualização**: 09 Novembro 2025
**Próxima Revisão**: Após teste em produção
