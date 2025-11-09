# 📋 Plano de Reestruturação do Projeto

## 🎯 Objetivos

1. **Escalabilidade**: Estrutura modular que suporta crescimento
2. **Manutenibilidade**: Código limpo com separação de responsabilidades
3. **Documentação**: Apenas documentos essenciais na raiz
4. **Melhores Práticas**: Seguir padrões Python e Docker

## 📊 Análise do Estado Atual

### ✅ Pontos Positivos
- Pipeline funcional (scripts + áudio)
- Variáveis de ambiente centralizadas (.env)
- Docker Compose bem organizado
- Makefile para automação

### ⚠️ Pontos a Melhorar

#### 1. **Código Python**
- ❌ Usa `requests` ao invés de `ollama-python` (biblioteca oficial)
- ❌ SSL verification desabilitado (`verify=False`)
- ❌ Falta tratamento de erros robusto
- ❌ Sem logging estruturado
- ❌ Sem testes unitários
- ❌ Sem type hints

#### 2. **Estrutura de Arquivos**
- ❌ Muitos arquivos `.md` na raiz (8 arquivos)
- ❌ Scripts sem estrutura de pacote Python
- ❌ Falta separação de config/src/tests
- ❌ Sem versionamento de schemas

#### 3. **Docker**
- ⚠️ Warnings de `FromAsCasing` no Dockerfile
- ⚠️ Version obsoleto no docker-compose
- ✅ Multi-stage builds (Piper)
- ✅ Non-root user

## 🏗️ Estrutura Proposta

```
audio-pipeline/
├── README.md                    # Visão geral do projeto
├── LICENSE                      # Licença
├── .env.example                 # Template de configuração
├── .env                         # Configuração local (git-ignored)
├── .gitignore                   # Git ignore
├── Makefile                     # Automação de tarefas
│
├── docs/                        # 📚 Documentação
│   ├── ARCHITECTURE.md          # Arquitetura do sistema
│   ├── DEPLOYMENT.md            # Guia de deploy
│   ├── DEVELOPMENT.md           # Guia para desenvolvedores
│   ├── MIGRATION_PIPER.md       # Histórico de migração
│   └── TECH_ANALYSIS.md         # Análise de tecnologias
│
├── src/                         # 🐍 Código fonte Python
│   ├── __init__.py
│   ├── pipeline/                # Módulo principal
│   │   ├── __init__.py
│   │   ├── config.py            # Configuração centralizada
│   │   ├── logging_config.py    # Setup de logging
│   │   └── exceptions.py        # Exceções customizadas
│   │
│   ├── generators/              # Geradores de conteúdo
│   │   ├── __init__.py
│   │   ├── script_generator.py  # Ollama → Scripts
│   │   ├── audio_generator.py   # Piper → Áudio
│   │   └── image_generator.py   # SD → Imagens
│   │
│   ├── clients/                 # Clientes de APIs
│   │   ├── __init__.py
│   │   ├── ollama_client.py     # Cliente Ollama (usando ollama-python)
│   │   ├── piper_client.py      # Cliente Piper TTS
│   │   └── sd_client.py         # Cliente Stable Diffusion
│   │
│   └── utils/                   # Utilitários
│       ├── __init__.py
│       ├── file_utils.py        # Manipulação de arquivos
│       └── retry.py             # Retry logic
│
├── tests/                       # 🧪 Testes
│   ├── __init__.py
│   ├── conftest.py              # Fixtures pytest
│   ├── unit/
│   │   ├── test_script_generator.py
│   │   ├── test_audio_generator.py
│   │   └── test_clients.py
│   └── integration/
│       └── test_pipeline.py
│
├── docker/                      # 🐳 Arquivos Docker
│   ├── Dockerfile               # Imagem principal
│   ├── Dockerfile.piper         # Imagem Piper TTS
│   └── .dockerignore
│
├── deploy/                      # 🚀 Deploy configs
│   ├── docker-compose.yml       # Compose principal
│   ├── docker-compose.tts.yml
│   ├── docker-compose.dev.yml   # Desenvolvimento
│   └── docker-compose.prod.yml  # Produção
│
├── config/                      # ⚙️ Configurações
│   ├── voices.json              # Config de vozes
│   ├── prompts/                 # Templates de prompts
│   │   └── script_template.txt
│   └── schemas/                 # JSON schemas
│       └── script_v1.json
│
├── data/                        # 📁 Dados
│   ├── input/
│   │   └── topics.txt
│   └── output/
│       ├── scripts/
│       ├── audio/
│       └── images/
│
└── scripts/                     # 🔧 Scripts auxiliares
    ├── setup.sh                 # Setup inicial
    ├── migrate.sh               # Migrações
    └── backup.sh                # Backup de dados
```

## 🔄 Melhorias de Código

### 1. **Usar Biblioteca Oficial Ollama**

**Antes (requests):**
```python
response = self.session.post(self.api_url, json=payload, timeout=120)
response.raise_for_status()
return response.json()['response'].strip()
```

**Depois (ollama-python):**
```python
from ollama import Client, ResponseError

try:
    response = self.client.generate(
        model=self.model,
        prompt=prompt,
        options={'temperature': 0.7}
    )
    return response.response.strip()
except ResponseError as e:
    logger.error(f"Ollama error: {e.error}")
    if e.status_code == 404:
        logger.info("Pulling model...")
        self.client.pull(self.model)
    raise
```

### 2. **Logging Estruturado**

```python
import structlog

logger = structlog.get_logger()

logger.info(
    "script_generated",
    topic=topic,
    model=self.model,
    duration=elapsed_time,
    word_count=len(script.split())
)
```

### 3. **Type Hints e Validação**

```python
from typing import List, Optional
from pydantic import BaseModel, Field

class ScriptConfig(BaseModel):
    model: str = Field(default="gemma3:4b")
    temperature: float = Field(default=0.7, ge=0.0, le=1.0)
    max_tokens: int = Field(default=150, gt=0)

def generate_script(
    self,
    topic: str,
    config: Optional[ScriptConfig] = None
) -> str:
    """Gera roteiro usando Ollama.

    Args:
        topic: Tópico do vídeo
        config: Configuração opcional

    Returns:
        Texto do roteiro gerado

    Raises:
        OllamaConnectionError: Se não conseguir conectar
        ModelNotFoundError: Se modelo não existe
    """
    pass
```

### 4. **Retry com Exponential Backoff**

```python
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type
)

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10),
    retry=retry_if_exception_type(ConnectionError)
)
def _make_request(self, payload):
    return self.client.generate(**payload)
```

### 5. **Context Managers**

```python
from contextlib import contextmanager

@contextmanager
def tts_session(base_url: str):
    """Context manager para sessão TTS."""
    session = requests.Session()
    try:
        # Test connection
        session.get(f"{base_url}/voices", timeout=5)
        yield session
    finally:
        session.close()

# Uso
with tts_session(self.tts_url) as session:
    response = session.post("/", json=payload)
```

## 📝 Documentação Essencial

### Manter na Raiz:
- ✅ `README.md` - Visão geral + quickstart
- ✅ `LICENSE` - Licença do projeto
- ✅ `.env.example` - Template de configuração
- ✅ `Makefile` - Automação

### Mover para `/docs`:
- 📦 `TECH_ANALYSIS.md`
- 📦 `MIGRATION_PIPER.md`
- 📦 `BEST_PRACTICES.md`
- 📦 `CORRECOES.md`
- 📦 `GUIA_EXECUCAO.md`
- 📦 `START_HERE.md`
- 📦 `README_PIPER.md`

### Criar em `/docs`:
- ✨ `ARCHITECTURE.md` - Diagramas e arquitetura
- ✨ `DEPLOYMENT.md` - Consolidar guias de execução
- ✨ `DEVELOPMENT.md` - Setup dev + boas práticas

## 🔧 Dependências Atualizadas

```txt
# requirements.txt
# Core
ollama>=0.4.0                    # Cliente oficial Ollama
pydantic>=2.0.0                  # Validação de dados
structlog>=24.0.0                # Logging estruturado

# HTTP
httpx>=0.27.0                    # HTTP client async-ready
tenacity>=8.0.0                  # Retry logic

# Utilities
python-dotenv>=1.0.0             # .env support
typer>=0.12.0                    # CLI interface
rich>=13.0.0                     # Terminal output

# Development
pytest>=8.0.0                    # Testing
pytest-cov>=4.0.0                # Coverage
pytest-asyncio>=0.23.0           # Async tests
black>=24.0.0                    # Code formatter
ruff>=0.3.0                      # Linter
mypy>=1.8.0                      # Type checker
```

## 🚀 Plano de Migração

### Fase 1: Estrutura (Semana 1)
1. ✅ Criar nova estrutura de diretórios
2. ✅ Mover arquivos `.md` para `/docs`
3. ✅ Reorganizar Docker files
4. ✅ Atualizar `.gitignore`

### Fase 2: Código (Semana 2)
1. ✅ Refatorar para módulos Python
2. ✅ Implementar `ollama-python`
3. ✅ Adicionar logging estruturado
4. ✅ Adicionar type hints
5. ✅ Implementar tratamento de erros

### Fase 3: Testes (Semana 3)
1. ✅ Setup pytest
2. ✅ Testes unitários
3. ✅ Testes de integração
4. ✅ Coverage > 80%

### Fase 4: Documentação (Semana 4)
1. ✅ Atualizar README.md
2. ✅ Criar ARCHITECTURE.md
3. ✅ Criar DEPLOYMENT.md
4. ✅ Adicionar docstrings

### Fase 5: CI/CD (Semana 5)
1. ✅ GitHub Actions
2. ✅ Testes automáticos
3. ✅ Build de imagens
4. ✅ Deploy automático

## 📊 Métricas de Sucesso

- ✅ Código coberto por testes (>80%)
- ✅ Type hints em todas as funções públicas
- ✅ Zero warnings do linter
- ✅ Documentação completa
- ✅ Build time < 2min
- ✅ Pipeline execution < 5min para 10 tópicos

## 🔗 Referências

- [Python Packaging Guide](https://packaging.python.org/)
- [Docker Best Practices](https://docs.docker.com/develop/dev-best-practices/)
- [Ollama Python Docs](https://github.com/ollama/ollama-python)
- [Structlog Docs](https://www.structlog.org/)
- [Pytest Docs](https://docs.pytest.org/)
