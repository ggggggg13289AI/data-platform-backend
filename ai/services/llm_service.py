"""
LLM Service - Unified interface for AI/LLM operations.

This module provides a high-level interface for LLM operations using the
provider factory pattern. It maintains backward compatibility with existing
code while enabling multi-provider support.

Usage:
    # Get default service (uses settings.AI_CONFIG)
    service = get_llm_service()

    # Chat
    response = await service.chat([{"role": "user", "content": "Hello"}])

    # Quick chat
    response = await service.quick_chat("Hello", system_prompt="You are helpful")

    # Health check
    health = await service.health_check()

    # List models
    models = await service.list_models()
"""

import logging
from typing import Any

from ai.services.providers import (
    LLMProviderFactory,
    BaseLLMProvider,
    LLMResponse,
    LLMConnectionError,
    LLMTimeoutError,
    ModelInfo,
)

logger = logging.getLogger(__name__)

# Re-export for backward compatibility
__all__ = [
    "LLMService",
    "LLMResponse",
    "LLMConnectionError",
    "LLMTimeoutError",
    "ModelInfo",
    "get_llm_service",
]


class LLMService:
    """
    High-level LLM service with provider abstraction.

    This class wraps the provider factory to provide a clean interface
    for LLM operations. It supports multiple providers and maintains
    backward compatibility with the original Ollama-only implementation.

    Attributes:
        provider: The underlying LLM provider instance
    """

    def __init__(
        self,
        provider_name: str | None = None,
        config: dict | None = None,
    ):
        """
        Initialize LLM service.

        Args:
            provider_name: Provider to use (defaults to settings.AI_CONFIG["PROVIDER"])
            config: Custom configuration (defaults to settings.AI_CONFIG)
        """
        self.provider: BaseLLMProvider = LLMProviderFactory.create(
            provider_name=provider_name,
            config=config,
        )

    async def chat(
        self,
        messages: list[dict[str, str]],
        temperature: float | None = None,
        max_tokens: int | None = None,
        model: str | None = None,
        **kwargs: Any,
    ) -> LLMResponse:
        """
        Send chat completion request.

        Args:
            messages: List of message dicts with 'role' and 'content'
            temperature: Override default temperature
            max_tokens: Override default max tokens
            model: Override default model
            **kwargs: Provider-specific parameters

        Returns:
            LLMResponse with content and metadata

        Raises:
            LLMConnectionError: Cannot connect to provider
            LLMTimeoutError: Request timed out
        """
        return await self.provider.chat(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            model=model,
            **kwargs,
        )

    async def quick_chat(
        self,
        message: str,
        system_prompt: str | None = None,
        **kwargs: Any,
    ) -> LLMResponse:
        """
        Quick single-turn chat.

        Args:
            message: User message
            system_prompt: Optional system prompt
            **kwargs: Additional parameters passed to chat()

        Returns:
            LLMResponse
        """
        return await self.provider.quick_chat(
            message=message,
            system_prompt=system_prompt,
            **kwargs,
        )

    async def health_check(self) -> dict[str, Any]:
        """
        Check provider health status.

        Returns:
            Dict with health status and available models
        """
        return await self.provider.health_check()

    async def list_models(self) -> list[ModelInfo]:
        """
        List available models from current provider.

        Returns:
            List of ModelInfo objects
        """
        return await self.provider.list_models()

    def get_provider_name(self) -> str:
        """Get current provider name."""
        return self.provider.provider_name

    def get_default_model(self) -> str:
        """Get default model for current provider."""
        return self.provider.get_default_model()

    def get_base_url(self) -> str:
        """Get base URL for current provider."""
        return self.provider.get_base_url()

    @staticmethod
    def list_available_providers() -> list[str]:
        """List all available provider names."""
        return LLMProviderFactory.list_providers()

    @staticmethod
    def create_for_provider(
        provider_name: str,
        config: dict | None = None,
    ) -> "LLMService":
        """
        Create service for specific provider.

        Args:
            provider_name: Provider identifier (e.g., "ollama", "lmstudio")
            config: Custom configuration

        Returns:
            LLMService instance configured for the provider
        """
        return LLMService(provider_name=provider_name, config=config)


# Singleton instance cache
_llm_service: LLMService | None = None


def get_llm_service(
    provider_name: str | None = None,
    config: dict | None = None,
    use_singleton: bool = True,
) -> LLMService:
    """
    Get LLM service instance.

    Args:
        provider_name: Provider to use (defaults to settings)
        config: Custom configuration
        use_singleton: Whether to use/update singleton instance

    Returns:
        LLMService instance

    Example:
        # Default provider from settings
        service = get_llm_service()

        # Specific provider
        service = get_llm_service("lmstudio")

        # Custom configuration
        service = get_llm_service("ollama", {"MODEL": "llama2:7b"})
    """
    global _llm_service

    # Return new instance if custom config or specific provider requested
    if config is not None or provider_name is not None:
        service = LLMService(provider_name=provider_name, config=config)
        if use_singleton and provider_name is None and config is None:
            _llm_service = service
        return service

    # Return or create singleton
    if use_singleton:
        if _llm_service is None:
            _llm_service = LLMService()
        return _llm_service

    return LLMService()


def clear_llm_service_cache() -> None:
    """Clear the singleton service cache."""
    global _llm_service
    _llm_service = None
    LLMProviderFactory.clear_cache()
