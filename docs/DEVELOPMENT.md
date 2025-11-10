# 💻 Development Guide - Audio Pipeline

**Last Updated**: November 10, 2025

This guide covers development practices for contributors to the Audio Pipeline project.

---

## 🏗️ Architecture Overview

The project follows a modular architecture with clear separation of concerns:

```
src/
├── pipeline/           # Core pipeline configuration and exceptions
│   ├── config.py      # Centralized configuration management
│   └── exceptions.py  # Custom exception classes
├── generators/         # Content generators (executable modules)
│   ├── script_generator.py   # LLM-based script generation
│   ├── audio_generator.py    # Text-to-speech conversion
│   └── image_generator.py    # Image generation (placeholder)
├── clients/           # External service clients
│   ├── tts_client.py # Piper TTS client
│   └── sd_client.py  # Stable Diffusion client
└── utils/             # Utility functions (future)
```

---

## 🚀 Development Setup

### Prerequisites

- Python 3.11+
- Docker and Docker Compose
- Make
- Git

### Local Development Environment

**All development is done inside Docker containers**. The host machine only needs Docker and Make.

```bash
# 1. Clone repository
git clone https://github.com/nklowns/potential-octo-chainllm.git
cd potential-octo-chainllm

# 2. Setup environment
cp .env.example .env
make setup

# 3. Build development image
make build
```

### Running Code Inside Container

```bash
# Execute a generator directly
docker-compose -f deploy/docker-compose.manager.yml run --rm manager \
  python -m src.generators.script_generator

# Open shell in container for debugging
docker-compose -f deploy/docker-compose.manager.yml run --rm manager bash
```

---

## 📦 Project Structure

### Python Module Organization

The project is **NOT** a Python package (no `setup.py` or `pyproject.toml`). Instead:

- Modules are executed directly: `python -m src.generators.script_generator`
- `PYTHONPATH=/home/appuser/app/src` is set in container
- All imports use absolute paths: `from src.pipeline import config`

### Configuration Management

All configuration is centralized in `src/pipeline/config.py`:

```python
from src.pipeline.config import config

# Access configuration
print(config.OLLAMA_BASE_URL)
print(config.INPUT_DIR)
print(config.SCRIPTS_OUTPUT_DIR)
```

Configuration values come from:
1. Environment variables (`.env` file)
2. Defaults in `config.py`

### Data Persistence

All data is persisted via Docker bind mounts:

- `data/input/` → Container input (read-only)
- `data/output/` → Container output (read-write)
- `config/` → Container config (read-only)

**Never write directly to host filesystem from Python code**. Always use the configured paths.

---

## 🔧 Development Workflow

### Making Changes

1. **Edit code** in your local editor (files are in `src/`)
2. **Rebuild image** if dependencies changed: `make build`
3. **Test changes** inside container:
   ```bash
   make pipeline
   # or
   docker-compose -f deploy/docker-compose.manager.yml run --rm manager \
     python -m src.generators.script_generator
   ```
4. **Check outputs**: `make monitor`

### Adding New Dependencies

1. Update `requirements.txt`:
   ```txt
   new-package>=1.0.0
   ```

2. Rebuild image:
   ```bash
   make build
   ```

3. Test in container:
   ```bash
   docker-compose -f deploy/docker-compose.manager.yml run --rm manager \
     python -c "import new_package; print(new_package.__version__)"
   ```

### Creating New Generators

1. Create new module in `src/generators/`:
   ```python
   # src/generators/new_generator.py
   """New content generator."""
   import logging
   from src.pipeline.config import config
   
   logger = logging.getLogger(__name__)
   
   def generate():
       """Generate content."""
       logger.info("Generating content...")
       # Implementation here
   
   if __name__ == "__main__":
       generate()
   ```

2. Update `src/generators/__init__.py` if needed

3. Test the generator:
   ```bash
   docker-compose -f deploy/docker-compose.manager.yml run --rm manager \
     python -m src.generators.new_generator
   ```

---

## 🧪 Testing

Currently, the project has **no automated tests** (by design decision).

**Manual testing workflow**:

1. Run pipeline: `make pipeline`
2. Verify outputs: `make monitor`
3. Check logs: `make logs`
4. Inspect files: `ls -lh data/output/*/`

### Service Testing

```bash
# Test individual services
make tts-test
make ollama-test
make test-services
```

---

## 📝 Code Style

### Python Style Guide

- Follow PEP 8
- Use type hints for function signatures
- Write docstrings for public functions
- Use meaningful variable names

Example:
```python
from typing import List, Optional

def generate_script(topic: str, temperature: float = 0.7) -> str:
    """Generate a script for the given topic.
    
    Args:
        topic: The topic to generate a script about
        temperature: LLM temperature (0.0-1.0)
    
    Returns:
        Generated script text
    
    Raises:
        OllamaConnectionError: If Ollama service is unavailable
    """
    pass
```

### Import Organization

1. Standard library imports
2. Third-party imports
3. Local imports

```python
import logging
import time
from typing import List

from ollama import Client
from tenacity import retry

from src.pipeline.config import config
from src.pipeline.exceptions import OllamaConnectionError
```

### Error Handling

Use custom exceptions from `src.pipeline.exceptions`:

```python
from src.pipeline.exceptions import OllamaConnectionError

try:
    response = client.generate(...)
except Exception as e:
    raise OllamaConnectionError(f"Failed to generate: {e}")
```

---

## 🐛 Debugging

### Container Debugging

```bash
# View logs
docker logs pipeline-manager

# Execute commands in running container
docker exec -it pipeline-manager bash

# Run with environment variables
docker-compose -f deploy/docker-compose.manager.yml run --rm \
  -e DEBUG=1 manager python -m src.generators.script_generator
```

### Python Debugging

Add print statements or logging:

```python
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

logger.debug(f"Processing topic: {topic}")
logger.info(f"Generated script: {len(script)} chars")
```

### Network Debugging

```bash
# Check if services are reachable from container
docker-compose -f deploy/docker-compose.manager.yml run --rm manager \
  curl -s https://piper-tts.drake-ayu.duckdns.org/voices

# Test Ollama
docker-compose -f deploy/docker-compose.manager.yml run --rm manager \
  curl -s http://ollama:11434/api/tags
```

---

## 🔄 Git Workflow

### Branch Strategy

- `main` - Production-ready code
- `feature/*` - New features
- `fix/*` - Bug fixes
- `refactor/*` - Code refactoring

### Commit Messages

Follow conventional commits:

```
type(scope): subject

- feat: New feature
- fix: Bug fix
- docs: Documentation changes
- refactor: Code refactoring
- chore: Maintenance tasks
```

Examples:
```
feat(generators): Add new image generator
fix(tts): Fix audio quality issue
docs(deployment): Update deployment guide
refactor(config): Centralize configuration
```

---

## 📚 Adding Documentation

### Where to Document

- **README.md** - Project overview, quick start
- **docs/DEPLOYMENT.md** - Deployment instructions
- **docs/DEVELOPMENT.md** - This file (development guide)
- **docs/ARCHITECTURE.md** - Detailed architecture (to be created)
- **Code docstrings** - Function/class documentation

### Documentation Style

- Use Markdown
- Include code examples
- Add emoji for visual clarity (🚀 💻 📝 etc.)
- Keep it concise and actionable

---

## 🔒 Security Guidelines

1. **Never commit secrets** - Use `.env` for sensitive data
2. **Run as non-root** - All containers use `appuser`
3. **Read-only mounts** - Input and config are read-only
4. **No hardcoded URLs** - Use environment variables
5. **Validate inputs** - Check file existence, formats

---

## 📊 Performance Considerations

1. **Minimize Docker rebuilds** - Only rebuild when dependencies change
2. **Use volume mounts** - Avoid copying large files into images
3. **Lazy loading** - Import modules only when needed
4. **Connection pooling** - Reuse HTTP sessions
5. **Batch processing** - Process multiple items efficiently

---

## 🤝 Contributing

### Before Submitting a PR

1. Test your changes locally
2. Update documentation if needed
3. Follow code style guidelines
4. Commit with clear messages

### Review Process

1. Submit PR with clear description
2. Respond to review comments
3. Update based on feedback
4. Merge when approved

---

## 🔗 Related Documentation

- [README.md](../README.md) - Project overview
- [DEPLOYMENT.md](DEPLOYMENT.md) - Deployment guide
- [BEST_PRACTICES.md](BEST_PRACTICES.md) - Best practices
- [TECH_ANALYSIS.md](TECH_ANALYSIS.md) - Technical analysis

---

## 📝 Questions?

For questions or issues:
1. Check existing documentation
2. Review code examples
3. Check Docker logs
4. Open an issue on GitHub
