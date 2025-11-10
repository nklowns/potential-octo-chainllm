import logging
import requests
import base64
from typing import Optional
from pathlib import Path

from src.pipeline import config
from src.pipeline.exceptions import ImageGeneratorError

logger = logging.getLogger(__name__)

class SDClient:
    """
    Client for interacting with the Stable Diffusion API (e.g., Automatic1111).
    """
    def __init__(self):
        self.api_url = config.IMAGE_SERVER_URL
        self.session = requests.Session()
        self._verify_connection()

    def _verify_connection(self):
        """
        Verifies the connection to the Stable Diffusion server.
        """
        try:
            # A URL de verificação de saúde é geralmente a raiz
            health_check_url = self.api_url.replace("/sdapi/v1/txt2img", "/")
            response = self.session.get(health_check_url, timeout=10)
            response.raise_for_status()
            logger.info(f"✅ Successfully connected to Stable Diffusion server at {self.api_url}")
        except requests.exceptions.RequestException as e:
            raise ImageGeneratorError(f"Failed to connect to Stable Diffusion server at {self.api_url}. Error: {e}")

    def generate_image(self, prompt: str) -> Optional[bytes]:
        """
        Generates an image from a text prompt.

        Args:
            prompt: The text prompt for image generation.

        Returns:
            The generated image as bytes, or None on failure.
        """
        payload = {
            "prompt": prompt,
            "steps": 25,
            "cfg_scale": 7,
            "width": 1024,
            "height": 1024,
            "sampler_name": "DPM++ 2M Karras"
        }

        try:
            logger.info("Sending request to Stable Diffusion API...")
            response = self.session.post(url=self.api_url, json=payload, timeout=300)
            response.raise_for_status()

            r = response.json()
            image_data_b64 = r['images'][0]

            logger.info("✅ Image data received from API.")
            return base64.b64decode(image_data_b64)

        except requests.exceptions.RequestException as e:
            logger.error(f"❌ API request failed: {e}")
        except (KeyError, IndexError) as e:
            logger.error(f"❌ Failed to parse API response: {e}")
        except Exception as e:
            logger.error(f"❌ An unexpected error occurred during image generation: {e}")

        return None