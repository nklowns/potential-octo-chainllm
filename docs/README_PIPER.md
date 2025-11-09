# 🎙️ Piper TTS v1.3.1 - Guia Rápido de Migração

> **Migração aplicada**: rhasspy/piper (MIT, arquivado) → OHF-Voice/piper1-gpl v1.3.1 (GPL-3.0)

## 🚀 Início Rápido

### Opção 1: Migração Automática (Recomendado)

```bash
cd /home/cloud/dev/homelab/supertest
make -f Makefile.piper migrate
```

Isso irá:
1. ✅ Parar versão antiga
2. ✅ Build da v1.3.1 (GPL)
3. ✅ Iniciar novo container
4. ✅ Testar API HTTP

### Opção 2: Passo a Passo Manual

```bash
# 1. Build da imagem
docker-compose -f docker-compose.tts.yml build piper-tts

# 2. Iniciar serviço
docker-compose -f docker-compose.tts.yml up -d piper-tts

# 3. Verificar logs (primeira vez baixa a voz ~80MB)
docker logs -f piper-tts

# 4. Testar API
curl -X POST http://localhost:5000 \
  -H 'Content-Type: application/json' \
  -d '{"text": "Teste de migração bem-sucedido!"}' \
  -o teste.wav
```

## 📋 Comandos Úteis

```bash
# Ver comandos disponíveis
make -f Makefile.piper help

# Logs em tempo real
make -f Makefile.piper logs

# Status do serviço
make -f Makefile.piper status

# Testar API
make -f Makefile.piper test

# Listar vozes disponíveis
make -f Makefile.piper voices

# Shell no container
make -f Makefile.piper shell
```

## 🔧 Configuração

### Variáveis de Ambiente (.env)

```bash
# TTS
TTS_SERVICE_NAME=piper-tts
TTS_PORT=5000

# Traefik
TRAEFIK_NETWORK=proxy_net
TRAEFIK_ENTRYPOINT=websecure
DOMAIN_DUCKDNS=seu-dominio.duckdns.org
DOMAIN_LOCAL=seu-dominio.local
```

### Voz Padrão

- **Atual**: `pt_BR-faber-medium` (português brasileiro, qualidade média)
- **Download**: Automático na primeira execução (~80MB)
- **Mudança**: Editar `command` em `docker-compose.tts.yml`

### Vozes Adicionais

```bash
# Listar todas disponíveis
make -f Makefile.piper voices

# Baixar nova voz
make -f Makefile.piper download-voice VOICE=en_US-lessac-medium
```

## 🧪 Testando a API

### Endpoint: POST /

```bash
# Síntese básica
curl -X POST http://localhost:5000 \
  -H 'Content-Type: application/json' \
  -d '{"text": "Olá, mundo!"}' \
  -o output.wav

# Com parâmetros customizados
curl -X POST http://localhost:5000 \
  -H 'Content-Type: application/json' \
  -d '{
    "text": "Texto mais lento.",
    "length_scale": 1.5,
    "noise_scale": 0.667,
    "noise_w_scale": 0.8
  }' \
  -o custom.wav
```

### Endpoint: GET /voices

```bash
# Listar vozes carregadas
curl http://localhost:5000/voices | jq
```

**Resposta esperada**:
```json
{
  "pt_BR-faber-medium": {
    "sample_rate": 22050,
    "num_speakers": 1,
    "espeak_voice": "pt-br",
    "phoneme_type": "espeak"
  }
}
```

## 🐍 Usando Python API

```python
import requests

# Gerar áudio (nova API v1.3.1)
response = requests.post(
    "http://localhost:5000",
    json={
        "text": "Olá do Python!",
        "voice": "pt_BR-faber-medium",
        "length_scale": 1.0,  # Velocidade normal
    }
)

with open("python_output.wav", "wb") as f:
    f.write(response.content)
```

## 📊 Health Check

```bash
# Via Docker
docker inspect piper-tts --format='{{.State.Health.Status}}'

# Via Make
make -f Makefile.piper status

# Via curl
curl http://localhost:5000/voices
```

## 🔄 Rollback (Se Necessário)

```bash
# 1. Parar nova versão
docker-compose -f docker-compose.tts.yml down

# 2. Editar docker-compose.tts.yml
# Restaurar: image: rhasspy/piper:latest

# 3. Reverter text_to_speech.py
git checkout HEAD -- scripts/text_to_speech.py

# 4. Iniciar versão antiga
docker-compose -f docker-compose.tts.yml up -d
```

## ⚠️ Mudanças Importantes

### API HTTP (Breaking Change)

| Aspecto | Antes (v1.2) | Agora (v1.3.1) |
|---------|-------------|----------------|
| **Content-Type** | `text/plain` | `application/json` |
| **Payload** | String raw | Objeto JSON `{"text": "..."}` |
| **Endpoint** | POST / | POST / (mesmo) |

### Licença (MIT → GPL-3.0)

- ✅ Uso pessoal/homelab: **OK**
- ✅ Uso interno: **OK**
- ⚠️ Distribuição: **Deve incluir código fonte**
- ⚠️ Modificações: **Devem ser compartilhadas**

## 📚 Documentação Completa

- **Migração Detalhada**: `MIGRATION_PIPER.md`
- **Análise Técnica**: `TECH_ANALYSIS.md`
- **Repositório**: https://github.com/OHF-Voice/piper1-gpl
- **API Docs**: https://github.com/OHF-Voice/piper1-gpl/blob/main/docs/API_HTTP.md

## 🐛 Troubleshooting

### Problema: Container não inicia

```bash
# Verificar logs
docker logs piper-tts

# Rebuild sem cache
make -f Makefile.piper rebuild
```

### Problema: Voz não encontrada

```bash
# Download manual
docker exec -it piper-tts \
  python3 -m piper.download_voices pt_BR-faber-medium --data-dir /data
```

### Problema: HTTP 500 na API

```bash
# Verificar payload JSON
echo '{"text": "teste"}' | jq .

# Testar com curl verboso
curl -v -X POST http://localhost:5000 \
  -H 'Content-Type: application/json' \
  -d '{"text": "teste"}'
```

## ✅ Checklist Pós-Migração

- [ ] Container `piper-tts` está healthy
- [ ] Endpoint `/voices` responde
- [ ] Síntese de áudio funciona
- [ ] Pipeline `text_to_speech.py` funciona
- [ ] Traefik routeia corretamente
- [ ] Voz pt_BR-faber-medium baixada
- [ ] Logs sem erros

---

**Data da Migração**: 09 Novembro 2025
**Versão**: Piper TTS v1.3.1 (GPL-3.0)
**Autor**: Migração automatizada
