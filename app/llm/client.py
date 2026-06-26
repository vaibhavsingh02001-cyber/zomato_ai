"""Groq API client wrapper for generating completions."""

import logging
from groq import Groq
from app.config import settings

logger = logging.getLogger(__name__)


class LLMClient:
    """Wrapper for the Groq SDK client to communicate with the Groq API."""

    def __init__(self):
        self.api_key = settings.groq_api_key
        self.model = settings.groq_model
        self._client = None

    @property
    def client(self) -> Groq:
        """Lazily initializes and returns the Groq client.

        Raises ValueError if the api key is missing.
        """
        if self._client is None:
            if not self.api_key:
                msg = "GROQ_API_KEY is not configured. Please set it in your .env file."
                logger.error(msg)
                raise ValueError(msg)
            self._client = Groq(api_key=self.api_key)
        return self._client

    def get_recommendations(self, system_prompt: str, user_prompt: str) -> str:
        """Sends the recommendation prompts to Groq API and returns the response string.

        Applies a 30s timeout to the request.
        """
        logger.info(f"Sending request to Groq API using model: {self.model}")
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.3,
                response_format={"type": "json_object"},
                timeout=30.0,  # 30-second timeout
            )
            content = response.choices[0].message.content
            logger.info("Successfully received response from Groq API.")
            return content
        except Exception as e:
            logger.error(f"Groq API completion request failed: {e}")
            raise
