"""
Base LLM Provider - Abstract interface for all LLM providers.

This module defines the contract that all LLM providers must implement,
ensuring consistent behavior across different backends (Ollama, LM Studio, vLLM, etc.).
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


class LLMProviderError(Exception):
    """Base exception for LLM provider errors."""

    pass


class LLMConnectionError(LLMProviderError):
    """Raised when unable to connect to LLM service."""

    pass


class LLMTimeoutError(LLMProviderError):
    """Raised when LLM request times out."""

    pass


class LLMModelNotFoundError(LLMProviderError):
    """Raised when the requested model is not found."""

    pass


@dataclass
class LLMResponse:
    """Standardized LLM response across all providers."""

    content: str
    model: str
    provider: str
    latency_ms: int
    tokens_used: int | None = None
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    finish_reason: str | None = None
    raw_response: dict | None = field(default=None, repr=False)


@dataclass
class ModelInfo:
    """Model information from provider."""

    name: str
    provider: str = ""
    size: str | None = None
    size_bytes: int | None = None
    family: str | None = None
    parameter_size: str | None = None
    quantization: str | None = None
    modified_at: str | None = None
    digest: str | None = None


class BaseLLMProvider(ABC):
    """
    Abstract base class for LLM providers.

    All LLM providers (Ollama, LM Studio, vLLM, etc.) must implement this interface
    to ensure consistent behavior across the application.

    Attributes:
        provider_name: Unique identifier for the provider (e.g., "ollama", "lmstudio")
        display_name: Human-readable name for UI display
        description: Brief description of the provider
    """

    provider_name: str = "base"
    display_name: str = "Base Provider"
    description: str = "Abstract base LLM provider"

    @abstractmethod
    async def chat(
        self,
        messages: list[dict[str, str]],
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        **kwargs: Any,
    ) -> LLMResponse:
        """
        Send chat completion request.

        Args:
            messages: List of message dicts with 'role' and 'content' keys.
                      Roles: 'system', 'user', 'assistant'
            model: Model to use (defaults to provider's default model)
            temperature: Sampling temperature (0.0-2.0)
            max_tokens: Maximum tokens in response
            **kwargs: Provider-specific parameters

        Returns:
            LLMResponse with content and metadata

        Raises:
            LLMConnectionError: Cannot connect to provider
            LLMTimeoutError: Request timed out
            LLMModelNotFoundError: Model not available
        """
        pass

    @abstractmethod
    async def list_models(self) -> list[ModelInfo]:
        """
        List available models from the provider.

        Returns:
            List of ModelInfo objects describing available models
        """
        pass

    @abstractmethod
    async def health_check(self) -> dict[str, Any]:
        """
        Check provider health status.

        Returns:
            Dict with health information:
            - status: "healthy" | "unhealthy"
            - provider: provider name
            - base_url: API base URL
            - model: default model (if configured)
            - model_available: whether default model is available
            - available_models: list of first N available models
            - error: error message if unhealthy
        """
        pass

    @abstractmethod
    def get_default_model(self) -> str:
        """
        Get the default model for this provider.

        Returns:
            Model name/identifier
        """
        pass

    def get_base_url(self) -> str:
        """
        Get the base URL for this provider.

        Returns:
            API base URL
        """
        return getattr(self, "base_url", "")

    async def quick_chat(
        self,
        message: str,
        system_prompt: str | None = None,
        **kwargs: Any,
    ) -> LLMResponse:
        """
        Convenience method for single-turn chat.

        Args:
            message: User message
            system_prompt: Optional system prompt
            **kwargs: Additional parameters passed to chat()

        Returns:
            LLMResponse
        """
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": message})

        return await self.chat(messages, **kwargs)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(provider={self.provider_name}, url={self.get_base_url()})"
