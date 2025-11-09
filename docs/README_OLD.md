# 🎬 Pipeline de Geração de Conteúdo com IA

Pipeline modular para geração automatizada de conteúdo em vídeo usando IA 100% local (ou com serviços externos configuráveis).

## 🏗️ Arquitetura

O projeto é dividido em contextos independentes, cada um com seu próprio `docker-compose`:

```
supertest/
├── docker-compose.tts.yml       # Serviço de Text-to-Speech (Piper)
├── docker-compose.images.yml    # Serviço de Geração de Imagens (Stable Diffusion)
├── docker-compose.manager.yml   # Orquestradores do pipeline
├── docker-compose.ollama.yml    # Ollama local (opcional)
├── Dockerfile                   # Imagem base para scripts Python
├── Makefile                     # Comandos de orquestração
└── scripts/                     # Lógica de negócio
    ├── generate_scripts.py      # Geração de roteiros via LLM
    ├── text_to_speech.py        # Conversão de texto para áudio
    └── image_generator.py       # Geração de imagens
```

## 🚀 Início Rápido

### 1. Configuração Inicial

Copie o arquivo de exemplo e configure suas variáveis de ambiente:

```bash
cp .env.example .env
# Edite .env com suas configurações
```

### 2. Construir a Imagem Base

```bash
make build
```

### 3. Executar o Pipeline Completo

```bash
# Pipeline básico (scripts + áudio)
make pipeline

# Pipeline completo (incluindo geração de imagens)
make full-pipeline
```

## 📋 Comandos Disponíveis

| Comando | Descrição |
|---------|-----------|
| `make build` | Constrói a imagem `audio-pipeline-app` |
| `make tts` | Inicia serviço TTS com Traefik |
| `make images` | Inicia serviço de Geração de Imagens |
| `make manager` | Executa pipeline de geração de scripts e áudio |
| `make image-manager` | Executa pipeline de geração de imagens |
| `make pipeline` | Pipeline completo (build + tts + manager) |
| `make monitor` | Monitora resultados (scripts, áudios, imagens) |
| `make clean` | Limpa containers e volumes |
| `make test-network` | Testa conectividade na rede |
| `make test-services` | Testa acessibilidade dos serviços |

## 🔧 Configuração de Serviços

### Serviços Locais vs. Externos

O pipeline suporta tanto serviços locais (via Docker) quanto externos (via URLs):

**Ollama (Geração de Scripts)**
```bash
# Externo (padrão)
OLLAMA_BASE_URL=https://ollama.drake-ayu.duckdns.org

# Local
OLLAMA_BASE_URL=http://ollama:11434
```

**Piper TTS (Text-to-Speech)**
```bash
# Local via DNS Docker (padrão)
# Usa o serviço 'piper-tts' diretamente na rede proxy_net

# Externo via Traefik
TTS_BASE_URL=https://piper-tts.drake-ayu.duckdns.org
```

**Stable Diffusion (Geração de Imagens)**
```bash
# Local via DNS Docker (padrão)
SD_API_URL=http://stable-diffusion-api:7860/sdapi/v1/txt2img

# Externo
SD_API_URL=https://sd-api.drake-ayu.duckdns.org/sdapi/v1/txt2img
```

## 📂 Estrutura de Dados

```
supertest/
├── input/
│   └── topics.txt              # Tópicos de entrada (um por linha)
├── output/
│   ├── scripts/                # Scripts gerados (.txt)
│   ├── audio/                  # Áudios gerados (.wav)
│   └── images/                 # Imagens geradas (.png)
└── config/
    └── voices.json             # Configuração de vozes
```

## 🔐 Segurança

- ✅ Containers executam como usuário não-root (`appuser`)
- ✅ Volumes de entrada e configuração montados como somente leitura
- ✅ Imagens Docker construídas com multi-stage builds
- ✅ Dependências Python gerenciadas via `requirements.txt`
- ✅ Health checks implementados em todos os serviços

## 🌐 Integração com Traefik

Todos os serviços são expostos via Traefik com certificados TLS automáticos:

- **Piper TTS**: `https://piper-tts.drake-ayu.duckdns.org`
- **Stable Diffusion**: `https://sd-api.drake-ayu.duckdns.org`

Os serviços usam a rede externa `proxy_net` para comunicação.

## 🛠️ Desenvolvimento

### Adicionar um Novo Serviço

1. Crie um novo `docker-compose.<contexto>.yml`
2. Use a imagem `audio-pipeline-app:latest` ou crie uma nova no `Dockerfile`
3. Configure variáveis de ambiente no `.env`
4. Adicione comandos relevantes ao `Makefile`

### Boas Práticas Implementadas

- **Separação de Contextos**: Cada serviço em seu próprio arquivo `docker-compose`
- **Configuração Centralizada**: Todas as variáveis no `.env`
- **Modularidade**: Serviços podem ser trocados por alternativas externas
- **Versionamento**: Imagens tagueadas e versionadas
- **Observabilidade**: Health checks e comandos de monitoramento

## 📊 Monitoramento

Acompanhe o progresso do pipeline:

```bash
# Visualizar resultados
make monitor

# Ver logs dos serviços
docker-compose -f docker-compose.manager.yml logs -f

# Status dos containers
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
```

## 🐛 Troubleshooting

### Serviço não está acessível

```bash
# Verificar conectividade de rede
make test-network

# Verificar status dos serviços
make test-services

# Verificar logs
docker logs <container-name>
```

### Problemas com GPU (Stable Diffusion)

Certifique-se de que o NVIDIA Container Toolkit está instalado:

```bash
# Instalar nvidia-container-toolkit
sudo apt-get install -y nvidia-container-toolkit
sudo systemctl restart docker
```

### Build falhando

```bash
# Limpar cache e reconstruir
docker system prune -a
make build
```

## 📝 TODO / Roadmap

- [ ] Integração com FFmpeg para montagem de vídeo
- [ ] Sistema de filas para processamento em batch
- [ ] Dashboard web para monitoramento
- [ ] Métricas de performance (Prometheus/Grafana)
- [ ] Cache de modelos de IA
- [ ] Backup automático de resultados
- [ ] CI/CD com GitHub Actions

## 📄 Licença

Este projeto é de código aberto e está disponível sob a licença MIT.

## 🤝 Contribuindo

Contribuições são bem-vindas! Por favor:

1. Fork o projeto
2. Crie uma branch para sua feature (`git checkout -b feature/AmazingFeature`)
3. Commit suas mudanças (`git commit -m 'Add some AmazingFeature'`)
4. Push para a branch (`git push origin feature/AmazingFeature`)
5. Abra um Pull Request

---

**Desenvolvido com ❤️ usando Docker, Python e IA**
