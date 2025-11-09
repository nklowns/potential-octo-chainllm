# 🔍 Análise de Gaps e Pontas Soltas

**Data:** 2025-11-09
**Status:** Pipeline funcional, mas com gaps críticos de produção

## 🚨 Gaps Críticos Identificados

### 1. **Docker Composes Não Utilizados/Incompletos**

#### ❌ `docker-compose.ollama.yml`
- **Status:** Declarado no `Makefile` (`local-ollama`) mas **NUNCA USADO**
- **Problema:** Ollama já existe em `agpt/ollama/docker-compose.yml`
- **Ação:**
  - [ ] Remover `docker-compose.ollama.yml` (duplicado)
  - [ ] Remover target `local-ollama` do Makefile
  - [ ] Atualizar `.env` para apontar para Ollama centralizado

#### ⚠️ `docker-compose.images.yml` (Stable Diffusion)
- **Status:** Existe mas **NÃO TESTADO**
- **Problemas:**
  - Requer GPU NVIDIA (sem fallback CPU)
  - Modelo não baixado (primeiro uso demora horas)
  - Sem health check funcional
  - Comando `--nowebui` mas ainda expõe porta 7860
- **Ação:**
  - [ ] Adicionar variável `SD_ENABLED=false` no .env
  - [ ] Criar health check que valida modelo carregado
  - [ ] Adicionar script de download de modelo
  - [ ] Testar geração de imagens end-to-end

### 2. **Makefiles Fragmentados**

- **Problema:** `Makefile` + `Makefile.piper` = confusão
- **Ação:**
  - [ ] Consolidar em um único `Makefile` com seções:
    ```makefile
    ## === SETUP ===
    ## === PIPER TTS ===
    ## === PIPELINE ===
    ## === MONITORING ===
    ## === CLEANUP ===
    ```
  - [ ] Remover `Makefile.piper`

### 3. **Health Checks Incompletos**

#### ✅ Tem Health Check:
- `docker-compose.images.yml` (Stable Diffusion)
- `docker-compose.tts.yml` (Piper TTS)

#### ❌ Faltam Health Checks:
- `docker-compose.manager.yml` (ambos serviços)
- `docker-compose.ollama.yml` (se mantido)

**Problema:** Compose sobe containers antes de estarem prontos

**Ação:**
```yaml
# docker-compose.manager.yml
manager:
  healthcheck:
    test: ["CMD", "python", "-c", "import sys; sys.exit(0)"]
    interval: 10s
    timeout: 5s
    retries: 3
    start_period: 5s
  depends_on:
    piper-tts:
      condition: service_healthy
```

### 4. **Persistência de Dados Ausente**

#### 📁 Dados Críticos Atualmente em Bind Mounts:
```yaml
volumes:
  - ./output:/home/appuser/app/output  # ⚠️ Deletável acidentalmente
  - ./input:/home/appuser/app/input    # ⚠️ Sem backup
  - ./config:/home/appuser/app/config  # ⚠️ Sem versionamento
```

#### 🎯 Deveria Usar Volumes Nomeados:
```yaml
volumes:
  pipeline_outputs:
    driver: local
    driver_opts:
      type: none
      o: bind
      device: ./output

  piper_voices:    # ✅ Já existe
  piper_models:    # ❌ Falta para cache de downloads
```

**Ação:**
- [ ] Criar volume `pipeline_outputs` para outputs
- [ ] Criar volume `piper_models` para cache
- [ ] Adicionar script de backup (`scripts/backup.sh`)

### 5. **Observabilidade ZERO**

#### ❌ Falta Completamente:
- **Logs centralizados**: Cada container loga separadamente
- **Métricas**: Sem Prometheus/Grafana
- **Tracing**: Sem rastreamento de pipeline
- **Alertas**: Sem notificação de falhas

#### 🎯 Deveria Ter:
```yaml
# docker-compose.monitoring.yml
services:
  loki:           # Agregação de logs
  promtail:       # Coleta de logs
  prometheus:     # Métricas
  grafana:        # Dashboards

  # Instrumentação Python
  # - structlog com JSON output
  # - prometheus_client para métricas
  # - OpenTelemetry para tracing
```

**Ação:**
- [ ] Fase 1: Adicionar structlog com JSON output
- [ ] Fase 2: Adicionar Loki + Promtail
- [ ] Fase 3: Adicionar Prometheus + Grafana
- [ ] Fase 4: Criar dashboards

### 6. **Tratamento de Erros Frágil**

```python
# scripts/generate_scripts.py (ATUAL)
except Exception as e:
    print(f"❌ Erro ao gerar script: {e}")
    # ⚠️ Pipeline continua mesmo com erro
```

#### 🎯 Deveria Ser:
```python
from tenacity import retry, stop_after_attempt, wait_exponential
from src.pipeline.exceptions import OllamaError, RetryableError

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10),
    retry=retry_if_exception_type(RetryableError)
)
def generate_script(self, topic: str) -> str:
    try:
        response = self.client.generate(...)
        return response.response.strip()
    except ollama.ResponseError as e:
        if e.status_code == 404:
            raise ModelNotFoundError(f"Model {self.model} not found")
        elif e.status_code >= 500:
            raise RetryableError(f"Server error: {e}")
        else:
            raise OllamaError(f"Unexpected error: {e}")
```

**Ação:**
- [ ] Criar `src/pipeline/exceptions.py`
- [ ] Implementar retry com exponential backoff
- [ ] Adicionar circuit breaker para falhas persistentes

### 7. **Segurança e Certificados**

#### ⚠️ Warnings de SSL:
```
InsecureRequestWarning: Unverified HTTPS request is being made to host 'ollama.drake-ayu.duckdns.org'
```

**Problema:** `verify=False` em todas as requisições HTTPS

**Ação:**
```python
# src/clients/base.py
import certifi
import ssl

def get_ssl_context():
    """Retorna contexto SSL com certificados do sistema."""
    if os.getenv('SSL_VERIFY', 'true').lower() == 'false':
        # Desenvolvimento apenas
        return ssl._create_unverified_context()

    # Produção: usar certifi
    return ssl.create_default_context(cafile=certifi.where())

# Uso
session = requests.Session()
session.verify = get_ssl_context()
```

- [ ] Adicionar variável `SSL_VERIFY=false` no .env (dev)
- [ ] Criar helper para SSL context
- [ ] Remover todos os `verify=False` hardcoded

### 8. **Configuração sem Validação**

```python
# ATUAL
self.model = os.getenv('OLLAMA_MODEL', 'gemma3:4b')
# ⚠️ Se digitar errado, só descobre no runtime
```

**Ação:** Usar Pydantic Settings
```python
from pydantic_settings import BaseSettings

class PipelineSettings(BaseSettings):
    ollama_base_url: str
    ollama_model: str = "gemma3:4b"
    tts_base_url: str
    output_scripts: Path

    class Config:
        env_file = ".env"

    @validator('ollama_model')
    def validate_model(cls, v):
        allowed = ['gemma3:4b', 'qwen3-vl:2b', 'qwen3-vl:4b']
        if v not in allowed:
            raise ValueError(f"Model must be one of {allowed}")
        return v

settings = PipelineSettings()
```

### 9. **Sem Testes Automatizados**

**Status:** 0 testes, 0% coverage

**Ação:** Criar estrutura mínima
```python
# tests/conftest.py
@pytest.fixture
def mock_ollama_client():
    with patch('ollama.Client') as mock:
        mock.return_value.generate.return_value.response = "Test script"
        yield mock

# tests/unit/test_script_generator.py
def test_generate_script_success(mock_ollama_client):
    generator = ScriptGenerator()
    result = generator.generate_script("Docker")
    assert len(result) > 0
    assert "Docker" in result
```

### 10. **Documentação Fragmentada**

#### 📚 Arquivos `.md` (8 no total):
```
docs/
├── START_HERE.md        # ⚠️ Desatualizado
├── GUIA_EXECUCAO.md     # ✅ Atual mas verboso
├── README_PIPER.md      # ⚠️ Info duplicada
├── MIGRATION_PIPER.md   # ✅ Histórico importante
├── TECH_ANALYSIS.md     # ✅ Análise valiosa
├── BEST_PRACTICES.md    # ⚠️ Não aplicado no código
├── CORRECOES.md         # ⚠️ Log de mudanças (migrar para CHANGELOG)
└── README_OLD.md        # ❌ Deletar
```

**Ação:**
- [ ] Criar `README.md` principal (raiz)
- [ ] Consolidar `docs/DEPLOYMENT.md` (merge GUIA + START)
- [ ] Mover `CORRECOES.md` → `CHANGELOG.md`
- [ ] Deletar `README_OLD.md` e `README_PIPER.md`
- [ ] Criar `docs/ARCHITECTURE.md` com diagramas

### 11. **Versionamento e CI/CD Ausentes**

**Sem:**
- ❌ Versionamento semântico
- ❌ CHANGELOG.md
- ❌ GitHub Actions / GitLab CI
- ❌ Testes automáticos em PR
- ❌ Build de imagens em pipeline

**Ação:**
```yaml
# .github/workflows/ci.yml
name: CI Pipeline
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run tests
        run: |
          make test

  build:
    runs-on: ubuntu-latest
    steps:
      - uses: docker/build-push-action@v5
        with:
          context: .
          file: docker/Dockerfile
          tags: audio-pipeline:${{ github.sha }}
```

### 12. **Rate Limiting e Quotas**

**Problema:** Sem controle de rate limit para APIs externas

```python
# RISCO: Pode ser bloqueado por rate limit
for topic in topics:  # 100 tópicos?
    script = ollama.generate(...)  # Sem delay
    audio = piper.synthesize(...)   # Sem throttling
```

**Ação:**
```python
from ratelimit import limits, sleep_and_retry

@sleep_and_retry
@limits(calls=10, period=60)  # 10 chamadas/minuto
def generate_script(self, topic: str):
    pass
```

### 13. **Backup e Recovery**

**Status:** Nenhum mecanismo de backup

**Ação:** Criar `scripts/backup.sh`
```bash
#!/bin/bash
# Backup de outputs e configurações
BACKUP_DIR="backups/$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"

tar -czf "$BACKUP_DIR/outputs.tar.gz" output/
tar -czf "$BACKUP_DIR/config.tar.gz" config/ .env
docker volume export piper-voices > "$BACKUP_DIR/piper-voices.tar"

echo "✅ Backup criado em $BACKUP_DIR"
```

### 14. **Falta .gitignore Robusto**

**Descoberto:** Arquivo não existe!

**Ação:** Criar `.gitignore`
```gitignore
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
venv/
.venv/

# IDEs
.vscode/
.idea/
*.swp

# Docker
*.log

# Outputs (manter versionado ou não?)
output/scripts/*.txt
output/audio/*.wav
output/images/*.png

# Env
.env
!.env.example

# OS
.DS_Store
Thumbs.db
```

### 15. **Sem Mecanismo de Retry para Downloads**

**Problema:** Download de vozes/modelos pode falhar

```python
# piper_client.py
def download_voice(self, voice: str):
    # ⚠️ Sem retry se download falhar
    response = requests.get(url, stream=True)
```

**Ação:**
```python
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=2, max=60)
)
def download_with_resume(url: str, dest: Path):
    """Download com retry e resumo."""
    if dest.exists():
        size = dest.stat().st_size
        headers = {'Range': f'bytes={size}-'}
    else:
        headers = {}

    with requests.get(url, headers=headers, stream=True) as r:
        r.raise_for_status()
        with open(dest, 'ab' if headers else 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
```

## 📊 Resumo de Impacto

| Gap | Severidade | Impacto em Prod | Esforço |
|-----|------------|-----------------|---------|
| Observabilidade | 🔴 Crítico | Impossível debugar | Alto |
| Health Checks | 🟡 Médio | Falhas silenciosas | Baixo |
| Backup/Recovery | 🔴 Crítico | Perda de dados | Médio |
| Testes | 🟡 Médio | Regressões | Alto |
| Error Handling | 🟡 Médio | Pipeline frágil | Médio |
| SSL Verification | 🟠 Baixo | Segurança | Baixo |
| Rate Limiting | 🟠 Baixo | Bloqueios de API | Baixo |
| CI/CD | 🟡 Médio | Deploy manual | Médio |
| Docs Consolidadas | 🟢 Baixo | Onboarding lento | Baixo |
| .gitignore | 🔴 Crítico | Secrets vazados | Trivial |

## 🎯 Priorização de Ações

### Sprint 1 (Crítico - 1 semana)
1. ✅ Criar `.gitignore` robusto
2. ✅ Adicionar health checks em manager
3. ✅ Implementar backup.sh
4. ✅ Consolidar Makefiles
5. ✅ Adicionar SSL_VERIFY no .env

### Sprint 2 (Importante - 2 semanas)
1. ✅ Refatorar error handling com retry
2. ✅ Adicionar logging estruturado (structlog)
3. ✅ Implementar Pydantic settings
4. ✅ Remover docker-compose.ollama.yml duplicado
5. ✅ Criar README.md principal

### Sprint 3 (Médio - 2 semanas)
1. ✅ Setup pytest + testes básicos
2. ✅ Adicionar Loki + Promtail
3. ✅ Criar CHANGELOG.md
4. ✅ Testar SD end-to-end
5. ✅ Consolidar docs em /docs

### Sprint 4 (Baixo - 1 semana)
1. ✅ GitHub Actions CI
2. ✅ Rate limiting
3. ✅ Prometheus + Grafana
4. ✅ Documentação de arquitetura
5. ✅ Cleanup final

## 🔗 Próximos Passos

1. **Revisar este documento** com o time
2. **Priorizar Sprints** baseado em roadmap
3. **Criar issues** no GitHub/GitLab
4. **Executar Sprint 1** (crítico)
5. **Atualizar RESTRUCTURE_PLAN.md** com estas descobertas
