#!/usr/bin/env python3
"""
Script Generator using Ollama.
Generates video scripts from topics using LLMs via Ollama.
"""
import time
import logging
from typing import List, Optional

from ollama import Client, ResponseError
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

# Adicionando o caminho do projeto ao sys.path para importação relativa
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[2]))

from src.pipeline import config
from src.pipeline.exceptions import ModelNotFoundError, OllamaClientError

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class ScriptGenerator:
    """
    Generator for scripts using Ollama.
    """
    def __init__(self):
        """
        Initializes the ScriptGenerator with configuration from the pipeline config.
        """
        self.client = Client(host=config.OLLAMA_BASE_URL, timeout=120)
        self.model = config.DEFAULT_SCRIPT_MODEL
        self.prompt_template = self._load_prompt_template()
        self._validate_connection_and_model()

    def _load_prompt_template(self) -> str:
        """
        Loads the script generation prompt template from the file.
        """
        try:
            with open(config.PROMPT_TEMPLATE_PATH, 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            logger.error(f"Prompt template not found at: {config.PROMPT_TEMPLATE_PATH}")
            # Fallback to a simple default prompt
            return "Create a short, engaging video script about {topic}."

    def _validate_connection_and_model(self) -> None:
        """
        Tests the connection to Ollama and ensures the required model is available.
        """
        try:
            logger.info(f"Connecting to Ollama at {config.OLLAMA_BASE_URL}...")
            response = self.client.list()
            logger.info("✅ Successfully connected to Ollama.")

            available_models = [model['name'] for model in response.get('models', [])]
            if self.model not in available_models:
                logger.warning(f"Model '{self.model}' not found. Attempting to pull it...")
                try:
                    self.client.pull(self.model)
                    logger.info(f"✅ Model '{self.model}' pulled successfully.")
                except ResponseError as e:
                    raise ModelNotFoundError(f"Failed to pull model '{self.model}': {e.error}")
            else:
                logger.info(f"✅ Model '{self.model}' is available.")

        except ResponseError as e:
            raise OllamaClientError(f"Error communicating with Ollama: {e.error}")
        except Exception as e:
            # Catches requests.exceptions.ConnectionError and other network issues
            raise OllamaClientError(f"Could not connect to Ollama at {config.OLLAMA_BASE_URL}. Error: {e}")

    def load_topics(self) -> List[str]:
        """
        Loads topics from the input file specified in the config.
        """
        if not config.TOPICS_FILE_PATH.exists():
            logger.error(f"Topics file not found: {config.TOPICS_FILE_PATH}")
            return []

        with open(config.TOPICS_FILE_PATH, 'r', encoding='utf-8') as f:
            topics = [line.strip() for line in f if line.strip() and not line.startswith('#')]

        logger.info(f"📝 Loaded {len(topics)} topics from {config.TOPICS_FILE_PATH}")
        return topics

    @retry(
        stop=stop_after_attempt(config.MAX_RETRIES),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((OllamaClientError, ResponseError)),
        before_sleep=lambda retry_state: logger.info(f"⏳ Retrying in {retry_state.next_action.sleep} seconds...")
    )
    def generate_script(self, topic: str) -> Optional[str]:
        """
        Generates a script for a given topic using Ollama with a retry mechanism.

        Args:
            topic: The video topic.

        Returns:
            The generated script as a string, or None if generation fails.
        """
        prompt = self.prompt_template.format(topic=topic)
        logger.info(f"Generating script for topic: '{topic}'...")

        response = self.client.generate(
            model=self.model,
            prompt=prompt,
            options={
                'temperature': 0.7,
                'top_k': 40,
                'top_p': 0.9,
            }
        )
        script_text = response.get('response', '').strip()

        if script_text:
            logger.info(f"✅ Script generated for '{topic}'.")
            return script_text
        else:
            logger.warning("Generated script is empty.")
            return None

    def _sanitize_filename(self, text: str) -> str:
        """
        Sanitizes a string to be used as a valid filename.
        """
        return "".join(c for c in text if c.isalnum() or c in (' ', '_')).rstrip().replace(' ', '_')

    def run(self):
        """
        Main execution loop to generate scripts for all topics.
        """
        topics = self.load_topics()
        if not topics:
            logger.warning("No topics to process. Exiting.")
            return

        for i, topic in enumerate(topics, 1):
            start_time = time.time()
            try:
                script_content = self.generate_script(topic)
                elapsed_time = time.time() - start_time

                if script_content:
                    safe_topic = self._sanitize_filename(topic)[:50]
                    filename = f"script_{i:03d}_{safe_topic}.txt"
                    filepath = config.SCRIPTS_OUTPUT_DIR / filename

                    try:
                        with open(filepath, 'w', encoding='utf-8') as f:
                            f.write(script_content)
                        logger.info(f"✅ Script saved to {filepath} ({elapsed_time:.2f}s)")
                    except IOError as e:
                        logger.error(f"Failed to write script to file {filepath}: {e}")
                else:
                    logger.error(f"❌ Failed to generate script for topic: '{topic}' after retries.")
            except Exception as e:
                elapsed_time = time.time() - start_time
                logger.error(f"❌ Failed to generate script for topic: '{topic}' after {elapsed_time:.2f}s. Error: {e}")


if __name__ == '__main__':
    try:
        # Adicionando uma verificação para garantir que o config.py seja carregado
        logger.info("Starting Script Generator...")
        generator = ScriptGenerator()
        generator.run()
        logger.info("Script generation process finished.")
    except (OllamaClientError, ModelNotFoundError) as e:
        logger.error(f"A critical client or model error occurred: {e}")
    except Exception as e:
        logger.error(f"An unexpected error prevented the script from running: {e}", exc_info=True)
