"""Configuration management for the pipeline."""

import os
from pathlib import Path
from typing import Optional


class Config:
    """Centralized configuration for the audio pipeline."""

    # Base paths
    BASE_DIR = Path(__file__).parent.parent.parent
    DATA_DIR = BASE_DIR / "data"
    INPUT_DIR = DATA_DIR / "input"
    OUTPUT_DIR = DATA_DIR / "output"
    CONFIG_DIR = BASE_DIR / "config"

    # Ollama configuration
    OLLAMA_BASE_URL: str = os.getenv('OLLAMA_BASE_URL', 'http://ollama:11434')
    DEFAULT_SCRIPT_MODEL: str = os.getenv('OLLAMA_MODEL', 'gemma3:4b')
    OLLAMA_TEMPERATURE: float = float(os.getenv('OLLAMA_TEMPERATURE', '0.7'))
    OLLAMA_TOP_K: int = int(os.getenv('OLLAMA_TOP_K', '40'))
    OLLAMA_TOP_P: float = float(os.getenv('OLLAMA_TOP_P', '0.9'))
    OLLAMA_NUM_PREDICT: int = int(os.getenv('OLLAMA_NUM_PREDICT', '150'))
    OLLAMA_RATE_LIMIT: int = int(os.getenv('OLLAMA_RATE_LIMIT', '0'))

    # TTS configuration
    TTS_SERVER_URL: str = os.getenv('TTS_BASE_URL', 'http://piper-tts:5000')
    TTS_VOICE: str = os.getenv('TTS_VOICE', 'pt_BR-faber-medium')
    TTS_LENGTH_SCALE: float = float(os.getenv('TTS_LENGTH_SCALE', '1.0'))
    TTS_NOISE_SCALE: float = float(os.getenv('TTS_NOISE_SCALE', '0.667'))
    TTS_NOISE_W_SCALE: float = float(os.getenv('TTS_NOISE_W_SCALE', '0.8'))
    TTS_RATE_LIMIT: int = int(os.getenv('TTS_RATE_LIMIT', '0'))

    # Input/Output paths
    # Input/Output paths
    TOPICS_FILE_PATH: Path = Path(os.getenv('INPUT_FILE', str(INPUT_DIR / 'topics.txt')))
    SCRIPTS_OUTPUT_DIR: Path = Path(os.getenv('OUTPUT_SCRIPTS', str(OUTPUT_DIR / 'scripts')))
    AUDIO_OUTPUT_DIR: Path = Path(os.getenv('OUTPUT_AUDIO', str(OUTPUT_DIR / 'audio')))
    IMAGES_OUTPUT_DIR: Path = Path(os.getenv('IMAGES_DIR', str(OUTPUT_DIR / 'images')))

    # Config files
    PROMPT_TEMPLATE_PATH: Path = Path(os.getenv('PROMPT_TEMPLATE_PATH', str((CONFIG_DIR / 'prompts' / 'script_template.txt'))))
    VOICES_CONFIG_PATH: Path = Path(os.getenv('VOICES_CONFIG_PATH', str(CONFIG_DIR / 'voices.json')))

    # External image server (e.g., Automatic1111)
    IMAGE_SERVER_URL: str = os.getenv('IMAGE_SERVER_URL', 'http://stable-diffusion:7860/sdapi/v1/txt2img')

    # Retry configuration
    MAX_RETRIES: int = int(os.getenv('MAX_RETRIES', '3'))
    RETRY_DELAY: int = int(os.getenv('RETRY_DELAY', '2'))

    @classmethod
    def ensure_dirs(cls):
        """Ensure all required directories exist."""
        cls.INPUT_DIR.mkdir(parents=True, exist_ok=True)
        cls.SCRIPTS_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        cls.AUDIO_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        cls.IMAGES_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# Singleton instance
config = Config()
