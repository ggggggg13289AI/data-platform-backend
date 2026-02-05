"""
OpenAI-Compatible LLM Provider - Generic provider for OpenAI API compatible backends.

Works with:
- vLLM (https://vllm.ai/)
- LocalAI (https://localai.io/)
- Text Generation WebUI with OpenAI extension
- Any other OpenAI API compatible server

Supports:
- Chat completions via /v1/chat/completions
- Model listing via /v1/models
- Optional API key authentication
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


class OpenAICompatibleProvider(BaseLLMProvider):
    """
    Generic OpenAI-compatible API provider.

    This provider works with any backend that implements the OpenAI API spec,
    including vLLM, LocalAI, Text Generation WebUI, and others.

    Configuration:
        API_BASE: Server URL (default: http://localhost:8000/v1)
        MODEL: Default model to use (default: default)
        API_KEY: Optional API key for authentication
        TIMEOUT: Request timeout in seconds (default: 120)
        MAX_TOKENS: Max tokens in response (default: 2048)
        TEMPERATURE: Default temperature (default: 0.7)
        MAX_CONCURRENT_REQUESTS: Semaphore limit (default: 5)
    """

    provider_name = "openai_compatible"
    display_name = "OpenAI Compatible"
    description = "Generic provider for OpenAI API compatible backends (vLLM, LocalAI, etc.)"

    def __init__(self, config: dict):
        """
        Initialize OpenAI-compatible provider.

        Args:
            config: Configuration dictionary with provider settings
        """
        self.base_url = config.get("API_BASE", "http://localhost:8000/v1")
        # Ensure URL ends with /v1
        self.base_url = self.base_url.rstrip("/")
        if not self.base_url.endswith("/v1"):
            self.base_url = f"{self.base_url}/v1"

        self.default_model = config.get("MODEL", "default")
        self.api_key = config.get("API_KEY", "")
        self.timeout = config.get("TIMEOUT", 120)
        self.max_tokens = config.get("MAX_TOKENS", 2048)
        self.temperature = config.get("TEMPERATURE", 0.7)

        # Rate limiting semaphore
        max_concurrent = config.get("MAX_CONCURRENT_REQUESTS", 5)
        self._semaphore = asyncio.Semaphore(max_concurrent)

    def _get_headers(self) -> dict[str, str]:
        """Get HTTP headers including optional API key."""
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    async def chat(
        self,
        messages: list[dict[str, str]],
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        **kwargs: Any,
    ) -> LLMResponse:
        """
        Send chat completion request.

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

        # Add optional OpenAI parameters
        optional_params = [
            "top_p",
            "frequency_penalty",
            "presence_penalty",
            "stop",
            "n",
            "logprobs",
            "top_logprobs",
            "response_format",
            "seed",
            "user",
        ]
        for key in optional_params:
            if key in kwargs:
                payload[key] = kwargs[key]

        try:
            async with httpx.AsyncClient(
                timeout=self.timeout,
                headers=self._get_headers(),
            ) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()

        except httpx.TimeoutException as e:
            logger.error(f"OpenAI-compatible request timed out: {e}")
            raise LLMTimeoutError(
                f"Request timed out after {self.timeout}s"
            ) from e

        except httpx.ConnectError as e:
            logger.error(f"Cannot connect to OpenAI-compatible server: {e}")
            raise LLMConnectionError(
                f"Cannot connect to server at {self.base_url}. Is it running?"
            ) from e

        except httpx.HTTPStatusError as e:
            error_msg = self._parse_error_response(e)
            logger.error(f"OpenAI-compatible HTTP error: {error_msg}")
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

    def _parse_error_response(self, error: httpx.HTTPStatusError) -> str:
        """Parse error response from server."""
        try:
            error_data = error.response.json()
            if "error" in error_data:
                err = error_data["error"]
                if isinstance(err, dict):
                    return err.get("message", str(err))
                return str(err)
        except Exception:
            pass
        return f"Server error: {error.response.status_code}"

    async def list_models(self) -> list[ModelInfo]:
        """
        List available models from the server.

        Returns:
            List of ModelInfo with model details
        """
        try:
            async with httpx.AsyncClient(
                timeout=10,
                headers=self._get_headers(),
            ) as client:
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
                f"Cannot connect to server at {self.base_url}"
            )
        except Exception as e:
            logger.error(f"Failed to list models: {e}")
            raise

    async def health_check(self) -> dict[str, Any]:
        """
        Check service health.

        Returns:
            Dict with health status and available models
        """
        try:
            models = await self.list_models()
            model_names = [m.name for m in models]

            # Check if default model is available
            model_available = (
                self.default_model in model_names
                or self.default_model == "default"
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
                "error": "Cannot connect to server",
            }

        except Exception as e:
            return {
                "status": "unhealthy",
                "provider": self.provider_name,
                "base_url": self.base_url,
                "error": str(e),
            }

    def get_default_model(self) -> str:
        """Get default model."""
        return self.default_model


# Auto-register provider with multiple aliases
LLMProviderFactory.register("openai_compatible", OpenAICompatibleProvider)
LLMProviderFactory.register("vllm", OpenAICompatibleProvider)
LLMProviderFactory.register("localai", OpenAICompatibleProvider)
LLMProviderFactory.register("text_generation_webui", OpenAICompatibleProvider)
LLMProviderFactory.register("tgwui", OpenAICompatibleProvider)
