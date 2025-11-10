"""Custom exceptions for the audio pipeline."""


class PipelineError(Exception):
    """Base exception for pipeline errors."""
    pass


class OllamaConnectionError(PipelineError):
    """Raised when cannot connect to Ollama server."""
    pass


class ModelNotFoundError(PipelineError):
    """Raised when Ollama model is not found."""
    pass


class OllamaClientError(PipelineError):
    """Generic error communicating with Ollama API."""
    pass


class TTSConnectionError(PipelineError):
    """Raised when cannot connect to TTS server."""
    pass


class TTSPipelineError(PipelineError):
    """Raised when TTS generation fails."""
    pass


class TTSClientError(PipelineError):
    """Raised when TTS client setup or synthesis fails."""
    pass


class ImageGeneratorError(PipelineError):
    """Raised for Stable Diffusion image generation issues."""
    pass
