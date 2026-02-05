"""
LM Studio LLM Provider - Integration with LM Studio local server.

LM Studio provides an OpenAI-compatible API endpoint.
Documentation: https://lmstudio.ai/docs/local-server

Supports:
- Chat completions via /v1/chat/completions
- Model listing via /v1/models
"""

import asyncio
import logging
import time
from typing import Any

import httpx

from ai.services.providers.base import (
    BaseLLMProvider,
    LLMConnectionError,
    LLMResponse,
    LLMTimeoutError,
    ModelInfo,
)
from ai.services.providers.factory import LLMProviderFactory

logger = logging.getLogger(__name__)


class LMStudioProvider(BaseLLMProvider):
    """
    LM Studio LLM provider.

    LM Studio is a desktop application for running local LLMs with an
    OpenAI-compatible API server.

    Configuration:
        API_BASE: LM Studio server URL (default: http://localhost:1234/v1)
        MODEL: Default model to use (default: local-model)
        TIMEOUT: Request timeout in seconds (default: 120)
        MAX_TOKENS: Max tokens in response (default: 2048)
        TEMPERATURE: Default temperature (default: 0.7)
        MAX_CONCURRENT_REQUESTS: Semaphore limit (default: 5)
    """

    provider_name = "lmstudio"
    display_name = "LM Studio"
    description = "Desktop application for running local LLMs with OpenAI-compatible API"

    def __init__(self, config: dict):
        """
        Initialize LM Studio provider.

        Args:
            config: Configuration dictionary with provider settings
        """
        self.base_url = config.get("API_BASE", "http://localhost:1234/v1")
        # Remove /v1 suffix if present (we add it in requests)
        self.base_url = self.base_url.rstrip("/")
        if not self.base_url.endswith("/v1"):
            self.base_url = f"{self.base_url}/v1"

        self.default_model = config.get("MODEL", "local-model")
        self.timeout = config.get("TIMEOUT", 120)
        self.max_tokens = config.get("MAX_TOKENS", 2048)
        self.temperature = config.get("TEMPERATURE", 0.7)

        # Rate limiting semaphore
        max_concurrent = config.get("MAX_CONCURRENT_REQUESTS", 5)
        self._semaphore = asyncio.Semaphore(max_concurrent)

    async def chat(
        self,
        messages: list[dict[str, str]],
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        **kwargs: Any,
    ) -> LLMResponse:
        """
        Send chat completion request to LM Studio.

        Args:
            messages: List of message dicts with 'role' and 'content'
            model: Model to use (defaults to self.default_model)
            temperature: Sampling temperature
            max_tokens: Maximum tokens in response
            **kwargs: Additional OpenAI-compatible parameters

        Returns:
            LLMResponse with content and metadata
        """
        async with self._semaphore:
            return await self._execute_chat(
                messages=messages,
                model=model or self.default_model,
                temperature=temperature if temperature is not None else self.temperature,
                max_tokens=max_tokens or self.max_tokens,
                **kwargs,
            )

    async def _execute_chat(
        self,
        messages: list[dict[str, str]],
        model: str,
        temperature: float,
        max_tokens: int,
        **kwargs: Any,
    ) -> LLMResponse:
        """Execute single chat request."""
        start_time = time.time()

        # Build OpenAI-compatible payload
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False,
        }

        # Add optional parameters
        for key in ["top_p", "frequency_penalty", "presence_penalty", "stop"]:
            if key in kwargs:
                payload[key] = kwargs[key]

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()

        except httpx.TimeoutException as e:
            logger.error(f"LM Studio request timed out: {e}")
            raise LLMTimeoutError(
                f"Request timed out after {self.timeout}s"
            ) from e

        except httpx.ConnectError as e:
            logger.error(f"Cannot connect to LM Studio: {e}")
            raise LLMConnectionError(
                f"Cannot connect to LM Studio at {self.base_url}. "
                "Is LM Studio running with the local server enabled?"
            ) from e

        except httpx.HTTPStatusError as e:
            error_msg = f"LM Studio error: {e.response.status_code}"
            try:
                error_data = e.response.json()
                if "error" in error_data:
                    error_msg = error_data["error"].get("message", error_msg)
            except Exception:
                pass
            logger.error(f"LM Studio HTTP error: {error_msg}")
            raise LLMConnectionError(error_msg) from e

        latency_ms = int((time.time() - start_time) * 1000)

        # Extract OpenAI-format response
        choice = data.get("choices", [{}])[0]
        content = choice.get("message", {}).get("content", "")
        finish_reason = choice.get("finish_reason")

        usage = data.get("usage", {})
        tokens_used = usage.get("total_tokens")
        prompt_tokens = usage.get("prompt_tokens")
        completion_tokens = usage.get("completion_tokens")

        return LLMResponse(
            content=content,
            model=data.get("model", model),
            provider=self.provider_name,
            latency_ms=latency_ms,
            tokens_used=tokens_used,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            finish_reason=finish_reason,
            raw_response=data,
        )

    async def list_models(self) -> list[ModelInfo]:
        """
        List available models from LM Studio.

        Returns:
            List of ModelInfo with model details
        """
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(f"{self.base_url}/models")
                response.raise_for_status()
                data = response.json()

            models = []
            for m in data.get("data", []):
                models.append(
                    ModelInfo(
                        name=m.get("id", ""),
                        provider=self.provider_name,
                        family=m.get("owned_by"),
                    )
                )

            return models

        except httpx.ConnectError:
            raise LLMConnectionError(
                f"Cannot connect to LM Studio at {self.base_url}"
            )
        except Exception as e:
            logger.error(f"Failed to list LM Studio models: {e}")
            raise

    async def health_check(self) -> dict[str, Any]:
        """
        Check LM Studio service health.

        Returns:
            Dict with health status and available models
        """
        try:
            models = await self.list_models()
            model_names = [m.name for m in models]

            # Check if default model is available
            model_available = (
                self.default_model in model_names
                or self.default_model == "local-model"
                or len(model_names) > 0
            )

            return {
                "status": "healthy",
                "provider": self.provider_name,
                "base_url": self.base_url,
                "model": self.default_model,
                "model_available": model_available,
                "available_models": model_names[:10],
            }

        except httpx.TimeoutException:
            return {
                "status": "unhealthy",
                "provider": self.provider_name,
                "base_url": self.base_url,
                "error": "Connection timeout",
            }

        except httpx.ConnectError:
            return {
                "status": "unhealthy",
                "provider": self.provider_name,
                "base_url": self.base_url,
                "error": "Cannot connect to LM Studio. Is the local server running?",
            }

        except Exception as e:
            return {
                "status": "unhealthy",
                "provider": self.provider_name,
                "base_url": self.base_url,
                "error": str(e),
            }

    def get_default_model(self) -> str:
        """Get default model for LM Studio."""
        return self.default_model


# Auto-register provider
LLMProviderFactory.register("lmstudio", LMStudioProvider)
