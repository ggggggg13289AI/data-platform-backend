"""
Ollama LLM Provider - Integration with Ollama local LLM server.

Ollama API documentation: https://github.com/ollama/ollama/blob/main/docs/api.md

Supports:
- Chat completions via /api/chat
- Model listing via /api/tags
- Model pulling via /api/pull (optional)
"""

import asyncio
import logging
import time
from typing import Any

import httpx

from ai.services.providers.base import (
    BaseLLMProvider,
    LLMConnectionError,
    LLMModelNotFoundError,
    LLMResponse,
    LLMTimeoutError,
    ModelInfo,
)
from ai.services.providers.factory import LLMProviderFactory

logger = logging.getLogger(__name__)


class OllamaProvider(BaseLLMProvider):
    """
    Ollama LLM provider.

    Ollama is a local LLM server that supports various open-source models
    like Llama, Mistral, Qwen, etc.

    Configuration:
        API_BASE: Ollama server URL (default: http://localhost:11434)
        MODEL: Default model to use (default: qwen2.5:7b)
        TIMEOUT: Request timeout in seconds (default: 120)
        MAX_TOKENS: Max tokens in response (default: 2048)
        TEMPERATURE: Default temperature (default: 0.7)
        MAX_RETRIES: Retry count for failed requests (default: 3)
        RETRY_DELAY: Base delay between retries in seconds (default: 2)
        MAX_CONCURRENT_REQUESTS: Semaphore limit (default: 5)
    """

    provider_name = "ollama"
    display_name = "Ollama"
    description = "Local LLM server supporting Llama, Mistral, Qwen, and other open-source models"

    def __init__(self, config: dict):
        """
        Initialize Ollama provider.

        Args:
            config: Configuration dictionary with provider settings
        """
        self.base_url = config.get("API_BASE", "http://localhost:11434")
        self.default_model = config.get("MODEL", "qwen2.5:7b")
        self.timeout = config.get("TIMEOUT", 120)
        self.max_tokens = config.get("MAX_TOKENS", 2048)
        self.temperature = config.get("TEMPERATURE", 0.7)
        self.max_retries = config.get("MAX_RETRIES", 3)
        self.retry_delay = config.get("RETRY_DELAY", 2)

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
        Send chat completion request to Ollama.

        Args:
            messages: List of message dicts with 'role' and 'content'
            model: Model to use (defaults to self.default_model)
            temperature: Sampling temperature
            max_tokens: Maximum tokens in response
            **kwargs: Additional Ollama options

        Returns:
            LLMResponse with content and metadata

        Raises:
            LLMConnectionError: Cannot connect to Ollama
            LLMTimeoutError: Request timed out
            LLMModelNotFoundError: Model not found
        """
        async with self._semaphore:
            return await self._chat_with_retry(
                messages=messages,
                model=model or self.default_model,
                temperature=temperature if temperature is not None else self.temperature,
                max_tokens=max_tokens or self.max_tokens,
                **kwargs,
            )

    async def _chat_with_retry(
        self,
        messages: list[dict[str, str]],
        model: str,
        temperature: float,
        max_tokens: int,
        **kwargs: Any,
    ) -> LLMResponse:
        """Execute chat with retry logic."""
        last_error: Exception | None = None

        for attempt in range(self.max_retries + 1):
            try:
                return await self._execute_chat(
                    messages=messages,
                    model=model,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    **kwargs,
                )
            except (LLMConnectionError, LLMTimeoutError) as e:
                last_error = e
                if attempt < self.max_retries:
                    delay = self.retry_delay * (attempt + 1)
                    logger.warning(
                        f"Ollama request failed (attempt {attempt + 1}/{self.max_retries + 1}): {e}. "
                        f"Retrying in {delay}s..."
                    )
                    await asyncio.sleep(delay)
            except LLMModelNotFoundError:
                # Don't retry for model not found
                raise

        raise last_error  # type: ignore

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

        # Build Ollama payload
        payload = {
            "model": model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
                **kwargs.get("options", {}),
            },
        }

        # Add optional parameters
        if "format" in kwargs:
            payload["format"] = kwargs["format"]

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/api/chat",
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()

        except httpx.TimeoutException as e:
            logger.error(f"Ollama request timed out: {e}")
            raise LLMTimeoutError(
                f"Request timed out after {self.timeout}s. "
                "Consider increasing AI_TIMEOUT or using a smaller model."
            ) from e

        except httpx.ConnectError as e:
            logger.error(f"Cannot connect to Ollama: {e}")
            raise LLMConnectionError(
                f"Cannot connect to Ollama at {self.base_url}. "
                "Is Ollama running? Start it with 'ollama serve'"
            ) from e

        except httpx.HTTPStatusError as e:
            error_msg = self._parse_error_response(e, model)
            logger.error(f"Ollama HTTP error: {error_msg}")
            raise LLMConnectionError(error_msg) from e

        latency_ms = int((time.time() - start_time) * 1000)

        # Extract response
        content = data.get("message", {}).get("content", "")
        tokens_used = data.get("eval_count")
        prompt_tokens = data.get("prompt_eval_count")
        finish_reason = data.get("done_reason")

        return LLMResponse(
            content=content,
            model=model,
            provider=self.provider_name,
            latency_ms=latency_ms,
            tokens_used=tokens_used,
            prompt_tokens=prompt_tokens,
            completion_tokens=tokens_used,
            finish_reason=finish_reason,
            raw_response=data,
        )

    def _parse_error_response(self, error: httpx.HTTPStatusError, model: str) -> str:
        """Parse error response and return user-friendly message."""
        try:
            error_data = error.response.json()
            if "error" in error_data:
                error_msg = error_data["error"]
                # Model not found
                if "not found" in error_msg.lower():
                    raise LLMModelNotFoundError(
                        f"模型 '{model}' 不存在。請執行 'ollama pull {model}' 或更新 AI_MODEL 設定。"
                    )
                return error_msg
        except (ValueError, LLMModelNotFoundError):
            raise
        except Exception:
            pass

        return f"Ollama service error: {error.response.status_code}"

    async def list_models(self) -> list[ModelInfo]:
        """
        List available models from Ollama.

        Returns:
            List of ModelInfo with model details
        """
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(f"{self.base_url}/api/tags")
                response.raise_for_status()
                data = response.json()

            models = []
            for m in data.get("models", []):
                details = m.get("details", {})
                models.append(
                    ModelInfo(
                        name=m.get("name", ""),
                        provider=self.provider_name,
                        size=self._format_size(m.get("size")),
                        size_bytes=m.get("size"),
                        family=details.get("family"),
                        parameter_size=details.get("parameter_size"),
                        quantization=details.get("quantization_level"),
                        modified_at=m.get("modified_at"),
                        digest=m.get("digest"),
                    )
                )

            return models

        except httpx.ConnectError:
            raise LLMConnectionError(
                f"Cannot connect to Ollama at {self.base_url}"
            )
        except Exception as e:
            logger.error(f"Failed to list Ollama models: {e}")
            raise

    async def health_check(self) -> dict[str, Any]:
        """
        Check Ollama service health.

        Returns:
            Dict with health status and available models
        """
        try:
            models = await self.list_models()
            model_names = [m.name for m in models]

            # Check if default model is available
            model_available = self.default_model in model_names or any(
                self.default_model.split(":")[0] in m for m in model_names
            )

            return {
                "status": "healthy",
                "provider": self.provider_name,
                "base_url": self.base_url,
                "model": self.default_model,
                "model_available": model_available,
                "available_models": model_names[:10],  # First 10 models
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
                "error": "Cannot connect to Ollama. Is it running?",
            }

        except Exception as e:
            return {
                "status": "unhealthy",
                "provider": self.provider_name,
                "base_url": self.base_url,
                "error": str(e),
            }

    def get_default_model(self) -> str:
        """Get default model for Ollama."""
        return self.default_model

    @staticmethod
    def _format_size(size_bytes: int | None) -> str | None:
        """Format size in bytes to human-readable string."""
        if size_bytes is None:
            return None

        for unit in ["B", "KB", "MB", "GB"]:
            if size_bytes < 1024:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024

        return f"{size_bytes:.1f} TB"


# Auto-register provider
LLMProviderFactory.register("ollama", OllamaProvider)
