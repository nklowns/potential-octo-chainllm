"""
Audio Pipeline - Automated content generation system.

This package provides tools for generating video scripts using LLMs,
converting text to speech, and creating images.
"""

__version__ = "1.0.0"
__author__ = "Audio Pipeline Team"

from src.pipeline.exceptions import (
    PipelineError,
    OllamaConnectionError,
    ModelNotFoundError,
    TTSConnectionError,
    TTSPipelineError
)

__all__ = [
    "PipelineError",
    "OllamaConnectionError",
    "ModelNotFoundError",
    "TTSConnectionError",
    "TTSPipelineError",
]
