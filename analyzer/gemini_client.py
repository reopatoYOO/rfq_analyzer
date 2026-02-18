"""
Gemini Client - Manages Google Gemini API interactions with retry logic.
"""

import logging
import time

from google import genai
from google.genai.types import GenerateContentConfig

logger = logging.getLogger(__name__)


class GeminiClient:
    """Wrapper for Google Gemini API with retry and rate limit handling."""

    def __init__(
        self,
        api_key: str,
        model_name: str = "gemini-2.0-flash",
        max_retries: int = 3,
        retry_delay: float = 2.0,
        temperature: float = 0.1,
    ):
        self.client = genai.Client(api_key=api_key)
        self.model_name = model_name
        self.config = GenerateContentConfig(temperature=temperature)
        self.max_retries = max_retries
        self.retry_delay = retry_delay

    def generate(self, prompt: str) -> str:
        """
        Send a prompt to Gemini and return the response text.
        Includes retry logic for transient errors.

        Args:
            prompt: The prompt to send.

        Returns:
            Response text from Gemini.

        Raises:
            Exception: If all retries are exhausted.
        """
        last_error = None

        for attempt in range(1, self.max_retries + 1):
            try:
                response = self.client.models.generate_content(
                    model=self.model_name, contents=prompt, config=self.config
                )
                return response.text.strip()
            except Exception as e:
                last_error = e
                logger.warning(
                    f"Gemini API call failed (attempt {attempt}/{self.max_retries}): {e}"
                )
                if attempt < self.max_retries:
                    wait_time = self.retry_delay * attempt  # Exponential backoff
                    logger.info(f"Retrying in {wait_time:.1f}s...")
                    time.sleep(wait_time)

        logger.error(f"All {self.max_retries} Gemini API attempts failed")
        raise last_error
