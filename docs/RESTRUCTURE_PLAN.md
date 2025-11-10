# 📋 Plano de Reestruturação do Projeto

**Status de Implementação:** 35% (9/26 itens concluídos)
**Última Atualização:** 2025-11-09
**Documento Relacionado:** Ver `PROJECT_STATUS.md` para análise completa

## 🎯 Objetivos

1. **Escalabilidade**: Estrutura modular que suporta crescimento
2. **Manutenibilidade**: Código limpo com separação de responsabilidades
3. **Documentação**: Apenas documentos essenciais na raiz
4. **Melhores Práticas**: Seguir padrões Python e Docker

## 📊 Análise do Estado Atual

### ✅ Pontos Positivos
- Pipeline funcional (scripts + áudio) ✅
- Variáveis de ambiente centralizadas (.env) ✅
- Docker Compose bem organizado ✅
- Makefile para automação ✅

### ⚠️ Pontos a Melhorar

#### 1. **Código Python** - 60% Implementado (6/10)
- ✅ ~~Usa `requests` ao invés de `ollama-python`~~ → **CORRIGIDO:** ollama-python implementado
- ✅ ~~SSL verification desabilitado~~ → **CORRIGIDO:** Session com retry strategy
- ✅ ~~Falta tratamento de erros robusto~~ → **CORRIGIDO:** Retry + exponential backoff
- ⏳ Sem logging estruturado → **PARCIAL:** logging padrão (não structlog)
- ❌ Sem testes unitários → **PENDENTE**
- ✅ ~~Sem type hints~~ → **CORRIGIDO:** Type hints adicionados

#### 2. **Estrutura de Arquivos** - 0% Implementado
- ⏳ Muitos arquivos `.md` na raiz → **PARCIAL:** README.md + CHANGELOG.md criados, mas docs/ ainda fragmentado
- ❌ Scripts sem estrutura de pacote Python → **PENDENTE:** Ainda `scripts/` soltos
- ❌ Falta separação de config/src/tests → **PENDENTE:** Estrutura não criada
- ❌ Sem versionamento de schemas → **PENDENTE**

#### 3. **Docker** - 50% Implementado (4/8)
- ✅ ~~Warnings de `FromAsCasing` no Dockerfile~~ → **CORRIGIDO**
- ⏳ Version obsoleto no docker-compose → **PARCIAL:** Ainda presente em alguns
- ✅ Multi-stage builds (Piper) → **OK**
- ✅ Non-root user → **OK**
- ✅ Health checks adicionados → **NOVO:** manager services
- ❌ Resource limits → **PENDENTE:** Sem CPU/memory limits
- ❌ Log rotation → **PENDENTE:** Logs crescem indefinidamente
- ❌ Cleanup de composes não usados → **PENDENTE:** docker-compose.ollama.yml ainda existe

## 🏗️ Estrutura Proposta (PARCIALMENTE IMPLEMENTADA ~40%)

**Estado:** Estrutura base implementada sem transformar em pacote Python. Persistência via bind mounts para `data/` e `config/` aplicada nos serviços do compose. Mantivemos “Python não é pacote”. Sem `tests/` por decisão atual.

```
audio-pipeline/  (ESTRUTURA ATUAL PARCIAL)
├── README.md                    # ✅ Criado
├── LICENSE                      # ❌ Não existe
├── .env.example                 # ✅ Criado e sincronizado
├── .env                         # ✅ Existe (git-ignored)
├── .gitignore                   # ✅ Criado (111 linhas)
├── Makefile                     # ✅ Consolidado (234 linhas)
│
├── docs/                        # ⏳ Existe mas fragmentado
│   ├── ARCHITECTURE.md          # ❌ Não criado
│   ├── DEPLOYMENT.md            # ❌ Não criado
│   ├── DEVELOPMENT.md           # ❌ Não criado
│   ├── MIGRATION_PIPER.md       # ✅ Existe
│   └── TECH_ANALYSIS.md         # ✅ Existe
│
├── src/                         # ✅ EXISTE
│   ├── __init__.py              # ❌
│   ├── pipeline/                # ❌
│   │   ├── __init__.py
│   │   ├── config.py            # ✅ Centraliza env + paths (data/, config/)
│   │   ├── logging_config.py    # ❌
│   │   └── exceptions.py        # ⏳ Criado inline em scripts
│   │
│   ├── generators/              # ✅ Generators modulados
│   │   ├── __init__.py
│   │   ├── script_generator.py  # ✅ Executável via `python -m src.generators.script_generator`
│   │   ├── audio_generator.py   # ✅ Executável via `python -m src.generators.audio_generator`
│   │   └── image_generator.py   # ✅ Executável via `python -m src.generators.image_generator`
│   │
│   ├── clients/                 # ❌ Lógica inline nos generators
│   │   ├── __init__.py
│   │   ├── ollama_client.py     # ❌ Inline em generate_scripts.py
│   │   ├── piper_client.py      # ❌ Inline em text_to_speech.py
│   │   └── sd_client.py         # ❌ Inline em image_generator.py
│   │
│   └── utils/                   # ❌
│       ├── __init__.py
│       ├── file_utils.py        # ❌
│       └── retry.py             # ⏳ Retry lógica inline nos scripts
│
├── tests/                       # 🚫 Não implementado por escopo atual
│   ├── __init__.py              # ❌
│   ├── conftest.py              # ❌
│   ├── unit/                    # ❌
│   │   ├── test_script_generator.py
│   │   ├── test_audio_generator.py
│   │   └── test_clients.py
│   └── integration/             # ❌
│       └── test_pipeline.py
│
├── docker/                      # ✅ Dockerfiles organizados
│   ├── Dockerfile.manager       # ✅ Existe
│   ├── Dockerfile.piper         # ✅ Existe
│   └── .dockerignore            # ✅ Existe
│
├── deploy/                          # ✅ Composes dedicados
│   ├── docker-compose.manager.yml   # ✅ Existe na raiz
│   ├── docker-compose.tts.yml       # ✅ Existe na raiz
│   ├── docker-compose.ollama.yml    # ✅ Existe na raiz
│   └── docker-compose.images.yml    # ✅ Existe na raiz
│
├── config/                      # ⚙️ Configurações
│   ├── voices.json              # ⏳ Existe mas não usado
│   ├── prompts/                 # Templates de prompts
│   │   └── script_template.txt  # ❌ Inline em generate_scripts.py
│   └── schemas/                 # JSON schemas
│       └── script_v1.json       # ❌ Não existe
│
└── data/                        # 📁 Dados (bind mounts)
    ├── input/
    │   └── topics.txt
    └── output/
        ├── scripts/
        ├── audio/
    └── images/

Notas:
- Python NÃO é pacote: removidos `setup.py` e `pyproject.toml` do build; imagem instala somente `requirements.txt` e usa `PYTHONPATH=/home/appuser/app/src`.
- Persistência: `deploy/docker-compose.manager.yml` monta `../data` e `../config` no container e executa módulos Python diretamente do `src/`.
- Sem tests/: manteremos fora do escopo por agora.
```

## 🔄 Melhorias de Código

## 💻 Melhorias de Código

### 1. **Biblioteca Oficial Ollama** ✅ IMPLEMENTADO

**Status:** Implementado completamente em `scripts/generate_scripts.py`

```python
# ✅ IMPLEMENTADO (2025-11-09)
import ollama
from ollama import ResponseError

client = ollama.Client(host=os.getenv('OLLAMA_BASE_URL'))

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

### 2. **Logging Estruturado** ❌ NÃO IMPLEMENTADO

**Status:** Ainda usando `logging` padrão (não structlog)

```python
# ❌ PENDENTE - Ainda logging padrão
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

### 3. **Type Hints e Validação** ⏳ PARCIALMENTE IMPLEMENTADO

**Status:** Type hints adicionados, mas Pydantic NÃO implementado

```python
# ✅ Type hints implementados
def generate_script(self, topic: str) -> str:
    """Gera roteiro usando Ollama."""
    pass

# ❌ Pydantic NÃO implementado
from pydantic import BaseModel, Field

class ScriptConfig(BaseModel):
    model: str = Field(default="gemma3:4b")
    temperature: float = Field(default=0.7, ge=0.0, le=1.0)
    max_tokens: int = Field(default=150, gt=0)
```

### 4. **Retry com Exponential Backoff** ✅ IMPLEMENTADO

**Status:** Implementado inline (não usando tenacity)

```python
# ✅ IMPLEMENTADO inline em generate_scripts.py
MAX_RETRIES = 3
RETRY_DELAY = 2

for attempt in range(self.MAX_RETRIES):
    try:
        response = self.client.generate(...)
        return response.response.strip()
    except Exception as e:
        if attempt < self.MAX_RETRIES - 1:
            delay = self.RETRY_DELAY * (2 ** attempt)  # Exponential backoff
            time.sleep(delay)
        else:
            raise

# ❌ NÃO usa tenacity library (implementado manualmente)
```

### 5. **Context Managers** ❌ NÃO IMPLEMENTADO

**Status:** Session criada mas não usa context manager

```python
# ❌ PENDENTE
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
- ✅ `README.md` - **CRIADO** (visão geral + quickstart)
- ❌ `LICENSE` - **NÃO EXISTE** (deveria ser GPL-3.0 para compatibilidade com Piper)
- ✅ `.env.example` - **CRIADO E SINCRONIZADO** com .env
- ✅ `Makefile` - **CONSOLIDADO** (234 linhas)
- ✅ `CHANGELOG.md` - **CRIADO** (v1.0.0)

### Já em `/docs` (manter):
- ✅ `TECH_ANALYSIS.md` - Análise de tecnologias
- ✅ `MIGRATION_PIPER.md` - Histórico de migração
- ✅ `BEST_PRACTICES.md` - Boas práticas
- ✅ `GAPS_ANALYSIS.md` - **ATUALIZADO** com status real
- ✅ `RESTRUCTURE_PLAN.md` - Este arquivo
- ✅ `PROJECT_STATUS.md` - **NOVO** (consolidação completa)

### Limpar em `/docs`:
- ⚠️ `CORRECOES.md` - Migrar para CHANGELOG.md
- ❌ `README_OLD.md` - **DELETAR** (obsoleto)
- ❌ `README_PIPER.md` - **DELETAR** (info duplicada)
- ⏳ `GUIA_EXECUCAO.md` - Consolidar com README.md ou deletar
- ⏳ `START_HERE.md` - Consolidar com README.md ou deletar

### Criar em `/docs`:
- ❌ `ARCHITECTURE.md` - Diagramas e arquitetura detalhada
- ❌ `DEVELOPMENT.md` - Setup dev + guia de contribuição
- ❌ `CONTRIBUTING.md` - Guia para contribuidores

## 🔧 Dependências Atualizadas

**Status Atual:** requirements.txt básico (3 dependências)

```txt
# requirements.txt - ATUAL ✅
requests>=2.31.0        # ⚠️ Mantido mas pouco usado
ollama>=0.4.0           # ✅ Implementado
urllib3>=2.0.0          # ✅ Para retry strategy

# FALTAM (sugerido mas não implementado):
pydantic>=2.0.0         # ❌ Validação de dados
structlog>=24.0.0       # ❌ Logging estruturado
httpx>=0.27.0           # ❌ HTTP client async-ready
tenacity>=8.0.0         # ⏳ Retry manual (não library)
python-dotenv>=1.0.0    # ⏳ Não necessário (os.getenv funciona)
typer>=0.12.0           # ❌ CLI interface
rich>=13.0.0            # ❌ Terminal output

# Development - NENHUM INSTALADO ❌
pytest>=8.0.0           # ❌ Testing
pytest-cov>=4.0.0       # ❌ Coverage
pytest-asyncio>=0.23.0  # ❌ Async tests
black>=24.0.0           # ❌ Code formatter
ruff>=0.3.0             # ❌ Linter
mypy>=1.8.0             # ❌ Type checker
```

**Problema Crítico:** Sem `requirements.lock` ou Poetry - builds não reproduzíveis

## 🚀 Plano de Migração

**⚠️ IMPORTANTE:** Plano NÃO executado. Fases 1-2 parcialmente implementadas, Fases 3-5 não iniciadas.

### Fase 1: Estrutura (Semana 1) - ⏳ PARCIAL (30%)
1. ❌ Criar nova estrutura de diretórios (src/, tests/, docker/, deploy/)
2. ⏳ Mover arquivos `.md` para `/docs` - Já estão em docs/ mas não consolidados
3. ❌ Reorganizar Docker files - Mantidos na raiz
4. ✅ Atualizar `.gitignore` - **COMPLETO** (111 linhas)

### Fase 2: Código (Semana 2) - ⏳ PARCIAL (60%)
1. ❌ Refatorar para módulos Python - Scripts ainda soltos em `scripts/`
2. ✅ Implementar `ollama-python` - **COMPLETO**
3. ❌ Adicionar logging estruturado - Ainda logging padrão
4. ✅ Adicionar type hints - **COMPLETO** em scripts principais
5. ✅ Implementar tratamento de erros - **COMPLETO** (retry + backoff)

### Fase 3: Testes (Semana 3) - ❌ NÃO INICIADA (0%)
1. ❌ Setup pytest
2. ❌ Testes unitários
3. ❌ Testes de integração
4. ❌ Coverage > 80%

### Fase 4: Documentação (Semana 4) - ⏳ PARCIAL (40%)
1. ✅ Atualizar README.md - **CRIADO** (comprehensive)
2. ❌ Criar ARCHITECTURE.md
3. ❌ Criar DEPLOYMENT.md
4. ⏳ Adicionar docstrings - Parcial (funções principais)

### Fase 5: CI/CD (Semana 5) - ❌ NÃO INICIADA (0%)
1. ❌ GitHub Actions
2. ❌ Testes automáticos
3. ❌ Build de imagens
4. ❌ Deploy automático

**Taxa de Conclusão Geral:** 26% (7/27 itens)

## 📊 Métricas de Sucesso

**Status Atual vs. Planejado:**

| Métrica | Meta | Atual | Status |
|---------|------|-------|--------|
| Código coberto por testes | >80% | 0% | ❌ |
| Type hints em funções públicas | 100% | ~60% | ⏳ |
| Zero warnings do linter | 0 | N/A (linter não rodando) | ❌ |
| Documentação completa | 100% | ~40% | ⏳ |
| Build time | <2min | ~30s (TTS) | ✅ |
| Pipeline funcional | 100% | 100% | ✅ |

**Resumo:** Pipeline funciona perfeitamente, mas métricas de qualidade não atingidas.

---

## 📈 Status de Implementação

### Resumo Executivo
- **Taxa de conclusão:** 35% (9/26 itens do plano)
- **Pipeline:** ✅ 100% funcional
- **Estrutura:** ❌ 0% (estrutura src/tests/docker não criada)
- **Código:** ⏳ 60% (ollama-python + error handling ok, falta testes e structlog)
- **Documentação:** ⏳ 40% (README.md criado, falta ARCHITECTURE.md)
- **CI/CD:** ❌ 0% (nenhuma automação)

### Para Análise Detalhada
Ver documentos:
- `PROJECT_STATUS.md` - Análise completa de implementação vs. planejado
- `GAPS_ANALYSIS.md` - Status atualizado dos 15 gaps críticos + 10 novos gaps invisíveis

**Última Atualização:** 2025-11-09
- ✅ Pipeline execution < 5min para 10 tópicos

## 🔗 Referências

- [Python Packaging Guide](https://packaging.python.org/)
- [Docker Best Practices](https://docs.docker.com/develop/dev-best-practices/)
- [Ollama Python Docs](https://github.com/ollama/ollama-python)
- [Structlog Docs](https://www.structlog.org/)
- [Pytest Docs](https://docs.pytest.org/)
