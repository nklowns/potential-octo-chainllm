#!/usr/bin/env python3
"""
Text-to-Speech Pipeline using a dedicated TTS Client.
Converts text scripts into WAV audio files.
"""
import logging
import time
import json
from pathlib import Path

# Adicionando o caminho do projeto ao sys.path para importação relativa
import sys
sys.path.append(str(Path(__file__).resolve().parents[2]))

from src.pipeline import config
from src.clients.tts_client import TTSClient
from src.pipeline.exceptions import TTSClientError

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class AudioGenerator:
    """
    Pipeline for converting text scripts to audio using a TTS client.
    """
    def __init__(self):
        """
        Initializes the AudioGenerator.
        """
        try:
            self.tts_client = TTSClient()
        except TTSClientError as e:
            logger.error(f"Failed to initialize TTS Client: {e}")
            raise

        self.voices = self._load_voices()
        self.default_voice = "pt_BR-faber-medium" # Fallback voice

    def _load_voices(self) -> dict:
        """
        Loads voice configurations from the JSON file.
        """
        try:
            with open(config.VOICES_CONFIG_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.warning(f"Could not load voices config: {e}. Using default voice.")
            return {}

    def _get_voice_for_script(self, script_name: str) -> str:
        """
        Determines which voice to use based on the script name or other logic.
        For now, it uses a simple logic, but can be expanded.
        """
        # Example: use a different voice for every other script
        script_number = int(script_name.split('_')[1])
        if script_number % 2 == 0 and "female_voice" in self.voices:
            return self.voices.get("female_voice", self.default_voice)
        return self.voices.get("male_voice", self.default_voice)

    def process_scripts(self):
        """
        Processes all script files in the output directory and generates audio.
        """
        script_files = list(config.SCRIPTS_OUTPUT_DIR.glob("*.txt"))
        if not script_files:
            logger.info("No scripts found to process.")
            return

        logger.info(f"Found {len(script_files)} scripts to process.")
        for script_path in script_files:
            script_name = script_path.stem
            audio_path = config.AUDIO_OUTPUT_DIR / f"{script_name}.wav"

            # Sempre regerar áudio, sobrescrevendo arquivo existente
            if audio_path.exists():
                logger.info(f"Audio for '{script_name}' exists. Regenerating and overwriting as requested.")

            try:
                with open(script_path, 'r', encoding='utf-8') as f:
                    text = f.read()

                if not text.strip():
                    logger.warning(f"Script '{script_name}' is empty. Skipping.")
                    continue

                voice = self._get_voice_for_script(script_name)
                logger.info(f"Generating audio for '{script_name}' with voice '{voice}'...")

                start_time = time.time()
                audio_content = self.tts_client.synthesize(
                    text,
                    voice,
                    length_scale=config.TTS_LENGTH_SCALE,
                    noise_scale=config.TTS_NOISE_SCALE,
                    noise_w_scale=config.TTS_NOISE_W_SCALE,
                )
                elapsed_time = time.time() - start_time

                if audio_content:
                    with open(audio_path, 'wb') as f:
                        f.write(audio_content)
                    logger.info(f"✅ Audio saved to {audio_path} ({elapsed_time:.2f}s)")
                else:
                    logger.error(f"❌ Failed to generate audio for '{script_name}'.")

            except Exception as e:
                logger.error(f"An error occurred while processing {script_path}: {e}")

if __name__ == "__main__":
    try:
        logger.info("Starting Audio Generation Pipeline...")
        pipeline = AudioGenerator()
        pipeline.process_scripts()
        logger.info("Audio Generation Pipeline finished.")
    except TTSClientError:
        logger.error("Could not start the audio generation pipeline due to a TTS client error.")
    except Exception as e:
        logger.error(f"An unexpected error occurred during the pipeline execution: {e}", exc_info=True)
