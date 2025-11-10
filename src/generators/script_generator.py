#!/usr/bin/env python3
"""
Script Generator using Ollama.
Generates video scripts from topics using LLMs via Ollama.
"""
import time
import logging
from typing import List, Optional
from pathlib import Path

from ollama import Client, ResponseError
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

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
        # Garante diretórios necessários
        config.ensure_dirs()
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

            # Compatível com ollama-python: response.models pode ser lista de objetos com atributo .model
            available_models: List[str] = []
            try:
                if hasattr(response, 'models'):
                    for m in getattr(response, 'models', []):
                        if hasattr(m, 'model') and isinstance(m.model, str):
                            available_models.append(m.model)
                        elif isinstance(m, dict):
                            name = m.get('model') or m.get('name') or m.get('tag')
                            if name:
                                available_models.append(name)
                elif isinstance(response, dict):
                    for m in response.get('models', []):
                        if isinstance(m, dict):
                            name = m.get('model') or m.get('name') or m.get('tag')
                            if name:
                                available_models.append(name)
                        elif isinstance(m, str):
                            available_models.append(m)
                elif isinstance(response, list):
                    for m in response:
                        if isinstance(m, str):
                            available_models.append(m)
                        elif isinstance(m, dict):
                            name = m.get('model') or m.get('name') or m.get('tag')
                            if name:
                                available_models.append(name)
            except Exception as parse_err:
                logger.warning(f"Could not parse model list: {parse_err}")

            if self.model not in available_models:
                # Tenta show() antes de fazer pull
                try:
                    _info = self.client.show(self.model)
                    logger.info(f"ℹ️ Model '{self.model}' detected via show(); skipping pull.")
                except Exception:
                    logger.warning(f"Model '{self.model}' not listed; pulling...")
                    try:
                        for progress in self.client.pull(self.model, stream=True):
                            status = getattr(progress, 'status', None) or progress.get('status') if isinstance(progress, dict) else None
                            if status:
                                logger.info(f"Pull progress: {status}")
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

        # Aplica rate limiting simples se configurado
        if config.OLLAMA_RATE_LIMIT > 0:
            # tempo mínimo entre requisições = 60 / RATE_LIMIT
            min_interval = 60.0 / config.OLLAMA_RATE_LIMIT
            # Usa atributo interno para controlar última chamada
            now = time.time()
            last = getattr(self, '_last_call_ts', None)
            if last is not None:
                delta = now - last
                if delta < min_interval:
                    sleep_time = min_interval - delta
                    logger.info(f"⏳ Rate limit active. Sleeping {sleep_time:.2f}s before generation...")
                    time.sleep(sleep_time)
            self._last_call_ts = time.time()

        response = self.client.generate(
            model=self.model,
            prompt=prompt,
            options={
                'temperature': config.OLLAMA_TEMPERATURE,
                'top_k': config.OLLAMA_TOP_K,
                'top_p': config.OLLAMA_TOP_P,
                'num_predict': config.OLLAMA_NUM_PREDICT,
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
