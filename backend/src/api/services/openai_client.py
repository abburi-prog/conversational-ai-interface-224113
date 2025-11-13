import os
from typing import List, Optional

from pydantic import BaseModel, Field
from fastapi import HTTPException, status

try:
    # OpenAI python SDK v1+
    from openai import OpenAI
except Exception:  # pragma: no cover
    OpenAI = None  # type: ignore


class _Config(BaseModel):
    """Internal configuration model for OpenAI client."""
    api_key: Optional[str] = Field(default=None)
    model: str = Field(default="gpt-4o-mini")


class _OpenAIClientWrapper:
    """Encapsulates OpenAI client initialization and chat completion calls."""
    def __init__(self) -> None:
        # Read configuration from environment (no secrets hardcoded)
        api_key = os.getenv("OPENAI_API_KEY")
        model = os.getenv("OPENAI_MODEL") or "gpt-4o-mini"
        # Fallback to older model name if newer is unavailable in environment
        if not model:
            model = "gpt-3.5-turbo"

        self._cfg = _Config(api_key=api_key, model=model)
        self._client = None

        # Initialize lazily to allow app startup without key for non-chat routes
        if self._is_available():
            try:
                if OpenAI is None:
                    raise RuntimeError("OpenAI SDK not available")
                self._client = OpenAI(api_key=self._cfg.api_key)
            except Exception as e:
                # Do not leak secret. Provide safe message.
                raise RuntimeError("Failed to initialize OpenAI client") from e

    def _is_available(self) -> bool:
        return bool(self._cfg.api_key)

    # PUBLIC_INTERFACE
    def is_configured(self) -> bool:
        """Check if OPENAI_API_KEY is present and client can be used."""
        return self._is_available() and self._client is not None

    # PUBLIC_INTERFACE
    def get_model(self) -> str:
        """Return selected OpenAI model name."""
        return self._cfg.model

    # PUBLIC_INTERFACE
    def create_chat_completion(self, messages: List[dict]) -> str:
        """Create a chat completion and return assistant reply content."""
        if not self.is_configured():
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="LLM service not configured"
            )
        try:
            # Using Chat Completions API
            resp = self._client.chat.completions.create(
                model=self._cfg.model,
                messages=messages,
                temperature=0.5,
            )
            choice = resp.choices[0]
            content = getattr(choice.message, "content", None)
            if not content:
                raise RuntimeError("Empty response from model")
            return content
        except HTTPException:
            raise
        except Exception as e:
            # Map to generic server error without exposing sensitive info
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Upstream LLM request failed"
            ) from e


# Singleton instance used by routes
openai_client = _OpenAIClientWrapper()
