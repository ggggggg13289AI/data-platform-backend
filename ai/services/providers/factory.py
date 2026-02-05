"""
LLM Provider Factory - Creates and manages LLM provider instances.

The factory pattern allows:
- Runtime provider switching
- Provider caching for performance
- Easy extension with new providers
- Configuration-based provider selection
"""

import logging
from typing import Type

from django.conf import settings

from ai.services.providers.base import BaseLLMProvider

logger = logging.getLogger(__name__)


class LLMProviderFactory:
    """
    Factory for creating and managing LLM provider instances.

    Usage:
        # Get default provider (from settings)
        provider = LLMProviderFactory.get_default()

        # Get specific provider
        provider = LLMProviderFactory.create("ollama")

        # Get provider with custom config
        provider = LLMProviderFactory.create("lmstudio", {
            "API_BASE": "http://localhost:1234/v1",
            "MODEL": "my-model",
        })

        # List available providers
        providers = LLMProviderFactory.list_providers()
    """

    _providers: dict[str, Type[BaseLLMProvider]] = {}
    _instances: dict[str, BaseLLMProvider] = {}

    @classmethod
    def register(cls, name: str, provider_class: Type[BaseLLMProvider]) -> None:
        """
        Register a provider class.

        Args:
            name: Provider identifier (e.g., "ollama", "lmstudio")
            provider_class: Class implementing BaseLLMProvider

        Example:
            LLMProviderFactory.register("my_provider", MyProvider)
        """
        normalized_name = name.lower()
        cls._providers[normalized_name] = provider_class
        logger.debug(f"Registered LLM provider: {normalized_name}")

    @classmethod
    def create(
        cls,
        provider_name: str | None = None,
        config: dict | None = None,
        use_cache: bool = True,
    ) -> BaseLLMProvider:
        """
        Create or get cached provider instance.

        Args:
            provider_name: Provider to create (defaults to settings.AI_CONFIG["PROVIDER"])
            config: Configuration dict (defaults to settings.AI_CONFIG merged with
                    provider-specific settings from AI_PROVIDERS)
            use_cache: Whether to use/update instance cache

        Returns:
            Provider instance

        Raises:
            ValueError: If provider is not registered
        """
        # Determine provider name
        name = (provider_name or cls._get_default_provider_name()).lower()

        # Build configuration
        final_config = cls._build_config(name, config)

        # Check cache
        if use_cache:
            cache_key = cls._get_cache_key(name, final_config)
            if cache_key in cls._instances:
                return cls._instances[cache_key]

        # Validate provider exists
        if name not in cls._providers:
            available = list(cls._providers.keys())
            raise ValueError(
                f"Unknown provider: '{name}'. Available providers: {available}"
            )

        # Create instance
        provider_class = cls._providers[name]
        provider = provider_class(final_config)

        # Cache instance
        if use_cache:
            cache_key = cls._get_cache_key(name, final_config)
            cls._instances[cache_key] = provider
            logger.debug(f"Created and cached provider: {name}")

        return provider

    @classmethod
    def get_default(cls) -> BaseLLMProvider:
        """
        Get default provider based on settings.

        Returns:
            Default provider instance
        """
        return cls.create()

    @classmethod
    def list_providers(cls) -> list[str]:
        """
        List registered provider names.

        Returns:
            List of provider identifiers
        """
        return sorted(cls._providers.keys())

    @classmethod
    def get_provider_class(cls, name: str) -> Type[BaseLLMProvider] | None:
        """
        Get provider class by name.

        Args:
            name: Provider identifier

        Returns:
            Provider class or None if not found
        """
        return cls._providers.get(name.lower())

    @classmethod
    def is_registered(cls, name: str) -> bool:
        """
        Check if provider is registered.

        Args:
            name: Provider identifier

        Returns:
            True if registered
        """
        return name.lower() in cls._providers

    @classmethod
    def clear_cache(cls, provider_name: str | None = None) -> None:
        """
        Clear cached provider instances.

        Args:
            provider_name: Specific provider to clear (None = clear all)
        """
        if provider_name:
            name = provider_name.lower()
            keys_to_remove = [k for k in cls._instances if k.startswith(f"{name}:")]
            for key in keys_to_remove:
                del cls._instances[key]
            logger.debug(f"Cleared cache for provider: {name}")
        else:
            cls._instances.clear()
            logger.debug("Cleared all provider cache")

    @classmethod
    def _get_default_provider_name(cls) -> str:
        """Get default provider name from settings."""
        return getattr(settings, "AI_CONFIG", {}).get("PROVIDER", "ollama")

    @classmethod
    def _build_config(cls, provider_name: str, override_config: dict | None) -> dict:
        """
        Build final configuration by merging settings.

        Priority (highest to lowest):
        1. override_config parameter
        2. AI_PROVIDERS[provider_name] from settings
        3. AI_CONFIG from settings
        """
        # Start with base AI_CONFIG
        base_config = dict(getattr(settings, "AI_CONFIG", {}))

        # Merge provider-specific config
        providers_config = getattr(settings, "AI_PROVIDERS", {})
        if provider_name in providers_config:
            base_config.update(providers_config[provider_name])

        # Merge override config
        if override_config:
            base_config.update(override_config)

        return base_config

    @classmethod
    def _get_cache_key(cls, provider_name: str, config: dict) -> str:
        """Generate cache key from provider name and config."""
        # Use relevant config values for cache key
        key_parts = [
            provider_name,
            config.get("API_BASE", ""),
            config.get("MODEL", ""),
        ]
        return ":".join(str(p) for p in key_parts)
