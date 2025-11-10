# 🏗️ Architecture - Audio Pipeline

**Last Updated**: November 10, 2025

This document provides a detailed overview of the Audio Pipeline architecture, design decisions, and system components.

---

## 📋 Table of Contents

- [System Overview](#system-overview)
- [Architecture Diagram](#architecture-diagram)
- [Component Details](#component-details)
- [Data Flow](#data-flow)
- [Technology Stack](#technology-stack)
- [Design Decisions](#design-decisions)
- [Deployment Architecture](#deployment-architecture)

---

## 🎯 System Overview

The Audio Pipeline is a modular content generation system that automates the creation of video content components:

1. **Script Generation** - Using LLMs (via Ollama)
2. **Audio Synthesis** - Using TTS (Piper)
3. **Image Generation** - Using Stable Diffusion (optional)

**Key Characteristics**:
- Microservices architecture
- Docker-based deployment
- External service integration
- File-based persistence
- Event-driven processing

---

## 🗺️ Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                        Host System                          │
│                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │ data/input/  │  │   config/    │  │ data/output/ │    │
│  │ topics.txt   │  │  prompts/    │  │  scripts/    │    │
│  │              │  │  schemas/    │  │  audio/      │    │
│  │              │  │  voices.json │  │  images/     │    │
│  └──────┬───────┘  └──────┬───────┘  └──────▲───────┘    │
│         │                 │                 │             │
│         │ (bind mount)    │                 │             │
│         ▼                 ▼                 │             │
│  ┌─────────────────────────────────────────┴──────────┐  │
│  │           Docker Container: pipeline-manager       │  │
│  │                                                    │  │
│  │  ┌──────────────────────────────────────────────┐ │  │
│  │  │          src/generators/                     │ │  │
│  │  │                                              │ │  │
│  │  │  ┌────────────────┐  ┌──────────────────┐  │ │  │
│  │  │  │ script_        │  │ audio_           │  │ │  │
│  │  │  │ generator.py   │  │ generator.py     │  │ │  │
│  │  │  └────────┬───────┘  └────────┬─────────┘  │ │  │
│  │  │           │                   │            │ │  │
│  │  └───────────┼───────────────────┼────────────┘ │  │
│  │              │                   │              │  │
│  │  ┌───────────▼───────────────────▼────────────┐ │  │
│  │  │          src/pipeline/                     │ │  │
│  │  │  - config.py (centralized config)          │ │  │
│  │  │  - exceptions.py (custom errors)           │ │  │
│  │  └────────────────────────────────────────────┘ │  │
│  │                                                  │  │
│  │  ┌────────────────────────────────────────────┐ │  │
│  │  │          src/clients/                      │ │  │
│  │  │  - tts_client.py (Piper TTS wrapper)       │ │  │
│  │  │  - sd_client.py (SD API wrapper)           │ │  │
│  │  └────────────────────────────────────────────┘ │  │
│  └──────────┬─────────────────────┬─────────────────┘  │
│             │                     │                     │
└─────────────┼─────────────────────┼─────────────────────┘
              │                     │
              │ (HTTP/API)          │ (HTTP/API)
              ▼                     ▼
     ┌─────────────────┐   ┌─────────────────┐
     │  Ollama Service │   │ Piper TTS       │
     │  (LLM)          │   │ (Text-to-Speech)│
     │  - Local or     │   │  - Docker       │
     │  - External     │   │  - GPL v1.3.1   │
     └─────────────────┘   └─────────────────┘
              │
              ▼
     ┌─────────────────┐
     │ Stable Diffusion│
     │ (Images)        │
     │  - Optional     │
     │  - External     │
     └─────────────────┘
```

---

## 🔧 Component Details

### 1. Pipeline Manager Container

**Purpose**: Main orchestration container that runs generators

**Key Files**:
- `src/generators/script_generator.py` - Script generation
- `src/generators/audio_generator.py` - Audio synthesis
- `src/generators/image_generator.py` - Image generation

**Responsibilities**:
- Read topics from input
- Call external services (Ollama, TTS)
- Write outputs to mounted volumes
- Handle retries and errors

**Execution**:
```bash
# Sequential execution
python -m src.generators.script_generator && \
python -m src.generators.audio_generator
```

### 2. Configuration Module

**Location**: `src/pipeline/config.py`

**Purpose**: Centralized configuration management

**Features**:
- Environment variable loading
- Path management (data/, config/)
- Service URL configuration
- Default values

**Usage**:
```python
from src.pipeline.config import config

# Access paths
topics_file = config.TOPICS_FILE_PATH
output_dir = config.SCRIPTS_OUTPUT_DIR

# Access service URLs
ollama_url = config.OLLAMA_BASE_URL
tts_url = config.TTS_SERVER_URL
```

### 3. Exception Module

**Location**: `src/pipeline/exceptions.py`

**Purpose**: Custom exception hierarchy

**Classes**:
- `PipelineError` - Base exception
- `OllamaConnectionError` - Ollama service errors
- `ModelNotFoundError` - LLM model not found
- `TTSConnectionError` - TTS service errors
- `TTSPipelineError` - TTS processing errors

### 4. Client Modules

**Location**: `src/clients/`

**Purpose**: Wrap external service APIs

**Components**:
- `tts_client.py` - Piper TTS HTTP client
- `sd_client.py` - Stable Diffusion API client

**Features**:
- Connection pooling
- Retry logic
- Error handling

### 5. External Services

#### Ollama (LLM Service)
- **Type**: Local or external
- **Protocol**: HTTP REST API
- **Models**: gemma3:4b, llama2, etc.
- **Function**: Generate video scripts

#### Piper TTS
- **Type**: Docker container
- **Protocol**: HTTP REST API
- **Version**: 1.3.1 (GPL)
- **Function**: Convert scripts to audio

#### Stable Diffusion (Optional)
- **Type**: External service
- **Protocol**: HTTP REST API
- **Function**: Generate images

---

## 🔄 Data Flow

### Script Generation Flow

```
1. Read topics.txt
   ↓
2. For each topic:
   ↓
3. Load prompt template
   ↓
4. Call Ollama API
   │ - Model: gemma3:4b
   │ - Temperature: 0.7
   │ - Max tokens: 150
   ↓
5. Receive generated script
   ↓
6. Save to data/output/scripts/{topic}.txt
   ↓
7. Log success
```

### Audio Generation Flow

```
1. List all scripts in data/output/scripts/
   ↓
2. For each script:
   ↓
3. Read script content
   ↓
4. Call Piper TTS API
   │ - Voice: pt_BR-faber-medium
   │ - Length scale: 1.0
   │ - Noise scale: 0.667
   ↓
5. Receive audio WAV
   ↓
6. Save to data/output/audio/{topic}.wav
   ↓
7. Log success
```

### Complete Pipeline Flow

```
User Input (topics.txt)
   ↓
[Script Generator]
   │
   ├─► Ollama API → Generate text
   │
   └─► Save scripts (.txt)
       ↓
[Audio Generator]
   │
   ├─► Read scripts (.txt)
   │
   ├─► Piper TTS → Generate audio
   │
   └─► Save audio (.wav)
       ↓
[Image Generator] (Optional)
   │
   ├─► Read scripts (.txt)
   │
   ├─► SD API → Generate images
   │
   └─► Save images (.png)
       ↓
Output (scripts/, audio/, images/)
```

---

## 🛠️ Technology Stack

### Core Technologies

| Component | Technology | Version | Purpose |
|-----------|-----------|---------|---------|
| Language | Python | 3.11 | Core logic |
| Container | Docker | 20.10+ | Deployment |
| Orchestration | Docker Compose | v2.0+ | Multi-container |
| Build Tool | Make | GNU Make | Automation |

### Python Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| ollama | 0.4.0+ | Ollama Python client |
| requests | 2.31.0+ | HTTP requests |
| urllib3 | 2.0.0+ | HTTP retry strategy |
| tenacity | 8.0.0+ | Retry with backoff |

### External Services

| Service | Technology | License | Purpose |
|---------|-----------|---------|---------|
| Ollama | Go binary | MIT | LLM inference |
| Piper TTS | C++/Python | GPL-3.0 | Text-to-speech |
| Stable Diffusion | Python | AGPL-3.0 | Image generation |

---

## 🎯 Design Decisions

### 1. Not a Python Package

**Decision**: Don't use `setup.py` or `pyproject.toml`

**Rationale**:
- Simpler deployment (just copy files)
- No need for editable installs
- Focus on Docker-based execution
- Easier to understand for non-Python devs

**Implementation**:
- Set `PYTHONPATH=/home/appuser/app/src` in container
- Use absolute imports: `from src.pipeline import config`
- Execute modules directly: `python -m src.generators.script_generator`

### 2. File-Based Persistence

**Decision**: Use file system instead of database

**Rationale**:
- Simple and transparent
- Easy to inspect outputs
- No database overhead
- Works well with bind mounts

**Implementation**:
- Input: `data/input/topics.txt`
- Output: `data/output/{scripts,audio,images}/`
- Config: `config/{prompts,schemas}/`

### 3. Microservices Architecture

**Decision**: Separate services for TTS, LLM, and pipeline

**Rationale**:
- Independent scaling
- Service isolation
- Flexible deployment (local or external)
- Easy to replace components

**Implementation**:
- Each service in own container
- Communication via HTTP/REST
- Shared Docker network

### 4. Bind Mounts Over Volumes

**Decision**: Use bind mounts for data/ and config/

**Rationale**:
- Easy to access from host
- Direct file editing
- Simple backup (just copy directory)
- No volume management needed

**Implementation**:
```yaml
volumes:
  - ../data/input:/home/appuser/app/data/input:ro
  - ../data/output:/home/appuser/app/data/output
  - ../config:/home/appuser/app/config:ro
```

### 5. Sequential Processing

**Decision**: Process topics sequentially, not in parallel

**Rationale**:
- Simpler code
- Respects rate limits
- Predictable resource usage
- Easier debugging

**Future**: Could add parallel processing with queue

### 6. Centralized Configuration

**Decision**: Single `config.py` for all configuration

**Rationale**:
- Single source of truth
- Easy to understand
- Type hints and defaults
- Environment variable support

**Implementation**:
```python
from src.pipeline.config import config
# All configuration accessed via config object
```

---

## 🚀 Deployment Architecture

### Local Development

```
Host Machine
├── Docker Engine
├── Docker Compose
└── Make
    ↓
Containers
├── pipeline-manager (app code)
├── piper-tts (TTS service)
└── ollama (optional, LLM)
```

### Production (External Services)

```
Host Machine
├── Docker Engine (app only)
└── pipeline-manager
    │
    ├─► External Ollama (HTTPS)
    ├─► External Piper TTS (HTTPS)
    └─► External SD API (HTTPS)
```

### Network Topology

```
┌─────────────────────────────────────┐
│        Docker Network: proxy_net    │
│                                     │
│  ┌──────────┐   ┌──────────┐      │
│  │ manager  │   │ piper-   │      │
│  │          ├──►│ tts      │      │
│  └────┬─────┘   └──────────┘      │
│       │                            │
└───────┼────────────────────────────┘
        │
        ▼ (external)
   ┌──────────┐
   │ Ollama   │
   │ (HTTPS)  │
   └──────────┘
```

---

## 🔒 Security Architecture

### Container Security

- **Non-root user**: All processes run as `appuser`
- **Read-only mounts**: Input and config are read-only
- **No secrets in images**: Environment variables only
- **Minimal base image**: python:3.11-slim

### Network Security

- **HTTPS for external**: External services use HTTPS
- **Internal network**: Containers on isolated Docker network
- **No exposed ports**: Only Traefik proxy exposes services

### Data Security

- **Git-ignored secrets**: `.env` never committed
- **Local data**: All data stays on host filesystem
- **No cloud storage**: No external data storage

---

## 📊 Performance Characteristics

### Throughput

- **Scripts**: ~10 scripts/minute (depends on Ollama)
- **Audio**: ~5 audio files/minute (depends on TTS)
- **End-to-end**: ~5 topics/minute (sequential)

### Resource Usage

- **Manager container**: ~200MB RAM, <5% CPU
- **Piper TTS**: ~500MB RAM, 10-20% CPU
- **Ollama**: ~2-8GB RAM (depends on model)

### Bottlenecks

1. **Ollama inference** - Slowest step (~10-30s per script)
2. **TTS synthesis** - Moderate (~5-10s per audio)
3. **Disk I/O** - Fast (local filesystem)

---

## 🔄 Future Enhancements

### Planned

- [ ] Parallel processing with queue
- [ ] Database for metadata
- [ ] API server for web UI
- [ ] Monitoring and metrics
- [ ] Auto-scaling based on load

### Under Consideration

- [ ] Support for more LLM providers
- [ ] Additional TTS engines
- [ ] Video editing integration
- [ ] CI/CD pipeline
- [ ] Kubernetes deployment

---

## 🔗 Related Documentation

- [README.md](../README.md) - Project overview
- [DEPLOYMENT.md](DEPLOYMENT.md) - Deployment guide
- [DEVELOPMENT.md](DEVELOPMENT.md) - Development guide
- [TECH_ANALYSIS.md](TECH_ANALYSIS.md) - Technical analysis
