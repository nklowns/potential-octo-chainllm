#!/usr/bin/env python3
"""
Text-to-Speech Pipeline using a dedicated TTS Client.
Converts text scripts into WAV audio files.
"""
import logging
from src.application.orchestrators.audio_orchestrator import AudioOrchestrator
from src.pipeline import config

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class AudioGenerator:
    """Wrapper legado que delega ao novo AudioOrchestrator."""
    def __init__(self):
        self.orchestrator = AudioOrchestrator()

    def process_scripts(self):
        self.orchestrator.run()


if __name__ == "__main__":
    logger.info("Starting Audio Generation Pipeline (orchestrator)...")
    AudioGenerator().process_scripts()
    logger.info("Audio Generation Pipeline finished.")
