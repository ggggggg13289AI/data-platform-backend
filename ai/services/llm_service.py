"""
LLM Service - Ollama integration for AI chat and analysis.

Provides async LLM communication with proper error handling,
timeout management, and rate limiting.
"""

import asyncio
import logging
import time
from dataclasses import dataclass
from typing import Any

import httpx
from django.conf import settings

logger = logging.getLogger(__name__)


class LLMConnectionError(Exception):
    """Raised when unable to connect to LLM service."""

    pass


class LLMTimeoutError(Exception):
    """Raised when LLM request times out."""

    pass


@dataclass
class LLMResponse:
    """Response from LLM service."""

    content: str
    model: str
    latency_ms: int
    tokens_used: int | None = None
    finish_reason: str | None = None


class LLMService:
    """
    LLM Service for Ollama integration.

    Provides chat completion with:
    - Async HTTP communication
    - Timeout handling
    - Connection error handling
    - Rate limiting via semaphore
    - Retry logic
    """

    def __init__(self):
        self.config = settings.AI_CONFIG
        self.base_url = self.config["API_BASE"]
        self.model = self.config["MODEL"]
        self.timeout = self.config["TIMEOUT"]
        self.max_tokens = self.config["MAX_TOKENS"]
        self.temperature = self.config["TEMPERATURE"]
        self.max_retries = self.config["MAX_RETRIES"]
        self.retry_delay = self.config["RETRY_DELAY"]

        # Rate limiting semaphore
        self._semaphore = asyncio.Semaphore(self.config["MAX_CONCURRENT_REQUESTS"])

    async def chat(
        self,
        messages: list[dict[str, str]],
        temperature: float | None = None,
        max_tokens: int | None = None,
        model: str | None = None,
    ) -> LLMResponse:
        """
        Send chat completion request to Ollama.

        Args:
            messages: List of message dicts with 'role' and 'content'
            temperature: Override default temperature
            max_tokens: Override default max tokens
            model: Override default model

        Returns:
            LLMResponse with content and metadata

        Raises:
            LLMConnectionError: Cannot connect to Ollama
            LLMTimeoutError: Request timed out
        """
        async with self._semaphore:
            return await self._chat_with_retry(
                messages=messages,
                temperature=temperature or self.temperature,
                max_tokens=max_tokens or self.max_tokens,
                model=model or self.model,
            )

    async def _chat_with_retry(
        self,
        messages: list[dict[str, str]],
        temperature: float,
        max_tokens: int,
        model: str,
    ) -> LLMResponse:
        """Execute chat with retry logic."""
        last_error: Exception | None = None

        for attempt in range(self.max_retries + 1):
            try:
                return await self._execute_chat(
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    model=model,
                )
            except (LLMConnectionError, LLMTimeoutError) as e:
                last_error = e
                if attempt < self.max_retries:
                    logger.warning(
                        f"LLM request failed (attempt {attempt + 1}/{self.max_retries + 1}): {e}"
                    )
                    await asyncio.sleep(self.retry_delay * (attempt + 1))

        raise last_error  # type: ignore

    async def _execute_chat(
        self,
        messages: list[dict[str, str]],
        temperature: float,
        max_tokens: int,
        model: str,
    ) -> LLMResponse:
        """Execute single chat request."""
        start_time = time.time()

        payload = {
            "model": model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/api/chat",
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()

        except httpx.TimeoutException as e:
            logger.error(f"LLM request timed out: {e}")
            raise LLMTimeoutError(f"Request timed out after {self.timeout}s") from e

        except httpx.ConnectError as e:
            logger.error(f"Cannot connect to LLM service: {e}")
            raise LLMConnectionError(
                f"Cannot connect to Ollama at {self.base_url}. Is it running?"
            ) from e

        except httpx.HTTPStatusError as e:
            # Try to get error message from response body
            error_msg = f"LLM service error: {e.response.status_code}"
            try:
                error_data = e.response.json()
                if "error" in error_data:
                    error_msg = error_data["error"]
                    # Model not found is a common issue
                    if "not found" in error_msg.lower():
                        error_msg = f"模型 '{model}' 不存在。請執行 'ollama pull {model}' 或更新 AI_MODEL 設定。"
            except Exception:
                pass
            logger.error(f"LLM HTTP error: {error_msg}")
            raise LLMConnectionError(error_msg) from e

        latency_ms = int((time.time() - start_time) * 1000)

        # Extract response
        content = data.get("message", {}).get("content", "")
        tokens_used = data.get("eval_count")
        finish_reason = data.get("done_reason")

        return LLMResponse(
            content=content,
            model=model,
            latency_ms=latency_ms,
            tokens_used=tokens_used,
            finish_reason=finish_reason,
        )

    async def quick_chat(self, message: str, system_prompt: str | None = None) -> LLMResponse:
        """
        Quick single-turn chat.

        Args:
            message: User message
            system_prompt: Optional system prompt

        Returns:
            LLMResponse
        """
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": message})

        return await self.chat(messages)

    async def health_check(self) -> dict[str, Any]:
        """
        Check Ollama service health.

        Returns:
            Dict with health status and available models
        """
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                response = await client.get(f"{self.base_url}/api/tags")
                response.raise_for_status()
                data = response.json()

                models = [m["name"] for m in data.get("models", [])]
                model_available = self.model in models or any(
                    self.model.split(":")[0] in m for m in models
                )

                return {
                    "status": "healthy",
                    "provider": "ollama",
                    "base_url": self.base_url,
                    "model": self.model,
                    "model_available": model_available,
                    "available_models": models[:5],  # First 5 models
                }

        except httpx.TimeoutException:
            return {
                "status": "unhealthy",
                "error": "Connection timeout",
                "provider": "ollama",
                "base_url": self.base_url,
            }

        except httpx.ConnectError:
            return {
                "status": "unhealthy",
                "error": "Cannot connect to Ollama",
                "provider": "ollama",
                "base_url": self.base_url,
            }

        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "provider": "ollama",
                "base_url": self.base_url,
            }


# Singleton instance
_llm_service: LLMService | None = None


def get_llm_service() -> LLMService:
    """Get singleton LLM service instance."""
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService()
    return _llm_service
