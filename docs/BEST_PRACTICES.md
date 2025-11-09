# 📚 Melhores Práticas Aplicadas

Este documento detalha as melhores práticas de Docker e Docker Compose implementadas neste projeto, baseadas na documentação oficial do Docker.

## 🐳 Dockerfile - Melhores Práticas

### 1. **Multi-Stage Builds**
```dockerfile
FROM python:3.11-slim as base
# ... build stage ...
```
- ✅ Reduz o tamanho final da imagem
- ✅ Separa dependências de build do ambiente de runtime
- ✅ Melhora a segurança ao excluir ferramentas de compilação

**Referência**: [Docker Docs - Multi-stage builds](https://docs.docker.com/build/building/multi-stage/)

### 2. **Usuário Não-Root**
```dockerfile
RUN useradd --create-home --shell /bin/bash appuser
USER appuser
```
- ✅ Princípio de menor privilégio
- ✅ Reduz a superfície de ataque
- ✅ Previne modificações acidentais do sistema

**Referência**: [Docker Docs - Create non-root user](https://docs.docker.com/build/building/best-practices/#user)

### 3. **Otimização de Cache de Layers**
```dockerfile
COPY scripts/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY --chown=appuser:appuser scripts/ .
```
- ✅ Copia `requirements.txt` primeiro para aproveitar cache
- ✅ Evita reinstalar dependências em cada mudança de código
- ✅ Builds mais rápidos durante o desenvolvimento

**Referência**: [Docker Docs - Leverage build cache](https://docs.docker.com/build/building/best-practices/#leverage-build-cache)

### 4. **Limpeza de Cache de Pacotes**
```dockerfile
RUN pip install --no-cache-dir -r requirements.txt
```
- ✅ Reduz tamanho da imagem
- ✅ Remove arquivos temporários desnecessários

**Referência**: [Docker Docs - Minimize layer size](https://docs.docker.com/build/building/best-practices/#minimize-the-number-of-layers)

## 🔧 Docker Compose - Melhores Práticas

### 1. **Versionamento Explícito**
```yaml
version: "3.9"
```
- ✅ Garante compatibilidade
- ✅ Evita comportamentos inesperados

### 2. **Redes Externas**
```yaml
networks:
  proxy_net:
    external: true
    name: proxy_net
```
- ✅ Permite comunicação entre stacks diferentes
- ✅ Reutiliza infraestrutura existente (Traefik)
- ✅ Separação de responsabilidades

**Referência**: [Docker Docs - External networks](https://docs.docker.com/compose/compose-file/networks/#external)

### 3. **Variáveis de Ambiente com Valores Padrão**
```yaml
environment:
  - TZ=${TZ:-UTC}
  - SD_API_URL=${SD_API_URL:-http://stable-diffusion-api:7860/sdapi/v1/txt2img}
```
- ✅ Flexibilidade de configuração
- ✅ Valores sensatos como fallback
- ✅ Suporta ambientes local e externo

**Referência**: [Docker Docs - Environment variables](https://docs.docker.com/compose/environment-variables/)

### 4. **Health Checks**
```yaml
healthcheck:
  test: ["CMD-SHELL", "curl -f http://localhost:7860/ || exit 1"]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 60s
```
- ✅ Detecta quando serviços estão realmente prontos
- ✅ Permite restart automático em caso de falha
- ✅ Suporta orquestração com `depends_on`

**Referência**: [Docker Docs - Healthcheck](https://docs.docker.com/compose/compose-file/services/#healthcheck)

### 5. **Volumes Somente Leitura**
```yaml
volumes:
  - ./input:/home/appuser/app/input:ro
  - ./config:/home/appuser/app/config:ro
```
- ✅ Previne modificações acidentais
- ✅ Melhora a segurança
- ✅ Clareza de intenção

**Referência**: [Docker Docs - Volumes](https://docs.docker.com/compose/compose-file/volumes/)

### 6. **Restart Policies**
```yaml
restart: unless-stopped
```
- ✅ Alta disponibilidade
- ✅ Recuperação automática de falhas
- ✅ Comportamento previsível após reinicialização do host

**Referência**: [Docker Docs - Restart policies](https://docs.docker.com/compose/compose-file/services/#restart)

### 7. **Separação de Arquivos por Contexto**
```
docker-compose.tts.yml
docker-compose.images.yml
docker-compose.manager.yml
```
- ✅ Modularidade
- ✅ Facilita manutenção
- ✅ Permite escalar serviços independentemente
- ✅ Melhor visibilidade de cada componente

**Referência**: [Docker Docs - Multiple compose files](https://docs.docker.com/compose/multiple-compose-files/)

### 8. **Uso de `env_file`**
```yaml
env_file:
  - .env
```
- ✅ Centraliza configuração
- ✅ Facilita diferentes ambientes (dev, staging, prod)
- ✅ Mantém segredos fora do versionamento

**Referência**: [Docker Docs - env_file](https://docs.docker.com/compose/compose-file/services/#env_file)

### 9. **Build Context Otimizado**
```yaml
build:
  context: .
  dockerfile: Dockerfile
```
- ✅ Reutiliza a mesma imagem entre serviços
- ✅ Reduz espaço em disco
- ✅ Builds mais rápidos

**Referência**: [Docker Docs - Build](https://docs.docker.com/compose/compose-file/build/)

## 🔐 Segurança

### 1. **Princípio de Menor Privilégio**
- ✅ Usuário não-root em todos os containers
- ✅ Volumes somente leitura onde apropriado
- ✅ Exposição mínima de portas

### 2. **Secrets e Variáveis Sensíveis**
- ✅ Uso de `.env` (não versionado)
- ✅ `.env.example` para documentação
- ✅ Suporte a Docker Secrets (futuro)

### 3. **Isolamento de Rede**
- ✅ Serviços em rede dedicada (`proxy_net`)
- ✅ Comunicação controlada via Traefik
- ✅ Exposição apenas de serviços necessários

## 📦 Gestão de Dependências

### 1. **Requirements.txt Fixado**
```txt
requests==2.31.0
pathlib2==2.3.7.post1
```
- ✅ Builds reproduzíveis
- ✅ Previne quebras por atualizações inesperadas
- ✅ Facilita auditoria de segurança

### 2. **Instalação durante Build (não Runtime)**
```dockerfile
RUN pip install --no-cache-dir -r requirements.txt
```
- ✅ Containers iniciam mais rápido
- ✅ Ambiente consistente
- ✅ Reduz dependências externas em runtime

## 🏗️ Arquitetura

### 1. **Serviços Configuráveis (Local/Externo)**
```bash
OLLAMA_BASE_URL=https://ollama.drake-ayu.duckdns.org  # Externo
# OLLAMA_BASE_URL=http://ollama:11434                 # Local
```
- ✅ Flexibilidade de deployment
- ✅ Facilita testes
- ✅ Suporta infraestrutura híbrida

### 2. **Separação de Responsabilidades**
- ✅ Cada arquivo docker-compose tem um propósito único
- ✅ Scripts Python focados em uma tarefa
- ✅ Configuração separada da lógica

## 🚀 Performance

### 1. **Imagens Slim**
```dockerfile
FROM python:3.11-slim
```
- ✅ Menor tempo de download
- ✅ Menor espaço em disco
- ✅ Menor superfície de ataque

### 2. **Caching Agressivo**
```dockerfile
COPY scripts/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY scripts/ .
```
- ✅ Aproveitamento máximo do cache de layers
- ✅ Builds incrementais rápidos

### 3. **Health Check com Start Period**
```yaml
healthcheck:
  start_period: 60s
```
- ✅ Tempo para serviços inicializarem
- ✅ Evita falsos positivos
- ✅ Reduz restarts desnecessários

## 📋 Observabilidade

### 1. **Logging Estruturado**
```python
basicConfig(level=INFO, format='%(asctime)s - %(levelname)s - %(message)s')
```
- ✅ Logs padronizados
- ✅ Facilita debugging
- ✅ Preparado para agregação (futuro)

### 2. **Comandos de Monitoramento**
```makefile
monitor:
    @echo "📊 Monitorando resultados..."
    @ls -la output/scripts/
```
- ✅ Visibilidade do estado do pipeline
- ✅ Facilita troubleshooting
- ✅ Automação de tarefas comuns

## 🧪 Testabilidade

### 1. **Test Network e Test Services**
```makefile
test-network:
    @docker network inspect $(TRAEFIK_NETWORK)
```
- ✅ Validação de infraestrutura
- ✅ Detecção precoce de problemas
- ✅ CI/CD friendly

## 📚 Documentação

### 1. **README Completo**
- ✅ Instruções de uso claras
- ✅ Exemplos práticos
- ✅ Troubleshooting guide

### 2. **Comentários em Código**
```yaml
# Monta input como somente leitura
- ./input:/home/appuser/app/input:ro
```
- ✅ Auto-documentação
- ✅ Facilita onboarding
- ✅ Mantém conhecimento contextual

### 3. **`.env.example`**
- ✅ Documenta todas as variáveis necessárias
- ✅ Facilita setup inicial
- ✅ Serve como template

## 🎯 Conformidade com Best Practices

| Prática | Implementado | Referência |
|---------|--------------|------------|
| Multi-stage builds | ✅ | [Docker Docs](https://docs.docker.com/build/building/multi-stage/) |
| Non-root user | ✅ | [Docker Docs](https://docs.docker.com/build/building/best-practices/#user) |
| Layer caching | ✅ | [Docker Docs](https://docs.docker.com/build/building/best-practices/#leverage-build-cache) |
| Health checks | ✅ | [Docker Docs](https://docs.docker.com/compose/compose-file/services/#healthcheck) |
| External networks | ✅ | [Docker Docs](https://docs.docker.com/compose/compose-file/networks/#external) |
| Environment variables | ✅ | [Docker Docs](https://docs.docker.com/compose/environment-variables/) |
| Read-only volumes | ✅ | [Docker Docs](https://docs.docker.com/compose/compose-file/volumes/) |
| Restart policies | ✅ | [Docker Docs](https://docs.docker.com/compose/compose-file/services/#restart) |
| .dockerignore | ✅ | [Docker Docs](https://docs.docker.com/build/building/best-practices/#exclude-with-dockerignore) |
| Secrets management | 🔄 | [Docker Docs](https://docs.docker.com/compose/use-secrets/) |

**Legenda:**
- ✅ Implementado
- 🔄 Planejado para próxima iteração

## 🔮 Próximas Melhorias

1. **Docker Secrets** para gerenciar credenciais sensíveis
2. **BuildKit** avançado com cache remoto
3. **Métricas de Performance** (Prometheus)
4. **Testes Automatizados** no pipeline CI/CD
5. **Image Scanning** para vulnerabilidades
6. **Resource Limits** para controle de recursos

---

**Última Atualização**: Novembro 2025
**Baseado em**: [Docker Official Documentation](https://docs.docker.com/)
