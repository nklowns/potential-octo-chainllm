import logging
import time
import os
from pathlib import Path

# Adicionando o caminho do projeto ao sys.path para importação relativa
import sys
sys.path.append(str(Path(__file__).resolve().parents[2]))

from src.pipeline import config
from src.clients.sd_client import SDClient
from src.pipeline.exceptions import ImageGeneratorError

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ImageGenerator:
    """
    Orchestrates image generation from text scripts using a Stable Diffusion client.
    """
    POLL_INTERVAL = 15 # seconds

    def __init__(self):
        """
        Initializes the ImageGenerator.
        """
        try:
            self.sd_client = SDClient()
        except ImageGeneratorError as e:
            logger.error(f"Failed to initialize Stable Diffusion Client: {e}")
            raise

    def _extract_prompt_from_script(self, file_path: Path) -> str:
        """
        Extracts the first non-empty line from a script to be used as a prompt.
        """
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    return line.strip()
        return "default prompt, no content found"

    def process_scripts(self):
        """
        Continuously checks for new scripts and generates images for them.
        """
        logger.info("🚀 Starting image generation process...")
        while True:
            scripts = list(config.SCRIPTS_OUTPUT_DIR.glob("*.txt"))

            if not scripts:
                logger.info(f"No scripts found. Waiting for {self.POLL_INTERVAL} seconds...")
                time.sleep(self.POLL_INTERVAL)
                continue

            logger.info(f"Found {len(scripts)} scripts to process.")
            for script_path in scripts:
                image_name = script_path.stem
                image_path = config.IMAGES_OUTPUT_DIR / f"{image_name}.png"

                if image_path.exists():
                    logger.info(f"Image for '{image_name}' already exists. Skipping.")
                    continue

                try:
                    prompt = self._extract_prompt_from_script(script_path)
                    logger.info(f"🖼️ Generating image for script: {image_name}...")

                    start_time = time.time()
                    image_data = self.sd_client.generate_image(prompt)
                    elapsed_time = time.time() - start_time

                    if image_data:
                        with open(image_path, 'wb') as f:
                            f.write(image_data)
                        logger.info(f"✅ Image saved to {image_path} ({elapsed_time:.2f}s)")
                    else:
                        logger.error(f"❌ Failed to generate image for '{image_name}'.")

                except Exception as e:
                    logger.error(f"An error occurred while processing {script_path}: {e}")

            logger.info(f"Finished processing batch. Waiting for {self.POLL_INTERVAL} seconds...")
            time.sleep(self.POLL_INTERVAL)


if __name__ == "__main__":
    try:
        generator = ImageGenerator()
        generator.process_scripts()
    except ImageGeneratorError:
        logger.error("Could not start the image generation process due to a client error.")
    except KeyboardInterrupt:
        logger.info("Image generation process stopped by user.")
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}", exc_info=True)
