import logging
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from typing import Optional

# Adicionando o caminho do projeto ao sys.path para importação relativa
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[2]))

from src.pipeline import config
from src.pipeline.exceptions import TTSClientError

logger = logging.getLogger(__name__)

class TTSClient:
    """
    Client for interacting with the Piper TTS server.
    """
    def __init__(self):
        """
        Initializes the TTS client and sets up a session with retry logic.
        """
        self.base_url = config.TTS_SERVER_URL
        self.session = self._create_session()
        self._verify_connection()

    def _create_session(self) -> requests.Session:
        """
        Creates a requests.Session with a robust retry strategy.
        """
        session = requests.Session()
        retry_strategy = Retry(
            total=config.MAX_RETRIES,
            backoff_factor=1,  # Exponential backoff (1s, 2s, 4s...)
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        return session

    def _verify_connection(self):
        """
        Verifies the connection to the TTS server and checks for available voices.
        """
        try:
            voices_url = f"{self.base_url}/voices"
            response = self.session.get(voices_url, timeout=10)
            response.raise_for_status()
            logger.info(f"✅ Successfully connected to TTS server at {self.base_url}")
        except requests.exceptions.RequestException as e:
            raise TTSClientError(f"Failed to connect to TTS server at {self.base_url}. Error: {e}")

    def synthesize(self, text: str, voice: str, length_scale: float = 1.0, noise_scale: float = 0.667, noise_w_scale: float = 0.8) -> Optional[bytes]:
        """
        Synthesizes audio from text using the TTS server.

        Args:
            text: The text to synthesize.
            voice: The voice model to use.
            length_scale: The speed of the speech.

        Returns:
            The audio content in bytes, or None if synthesis fails.
        """
        payload = {
            "text": text,
            "voice": voice,
            "length_scale": length_scale,
            "noise_scale": noise_scale,
            "noise_w_scale": noise_w_scale,
        }
        try:
            response = self.session.post(self.base_url, json=payload, timeout=180)
            response.raise_for_status()
            logger.info(f"Audio synthesized for text snippet (voice: {voice}).")
            return response.content
        except requests.exceptions.RequestException as e:
            logger.error(f"TTS synthesis failed: {e}")
            return None
