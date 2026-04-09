"""
LLM Providers - Multi-provider LLM integration with factory pattern.

Supported providers:
- Ollama (default)
- LM Studio
- OpenAI-compatible (vLLM, LocalAI, Text Generation WebUI, etc.)
"""

# Import providers to auto-register them
from ai.services.providers import lmstudio, ollama, openai_compatible
from ai.services.providers.base import (
    BaseLLMProvider,
    LLMConnectionError,
    LLMProviderError,
    LLMResponse,
    LLMTimeoutError,
    ModelInfo,
)
from ai.services.providers.factory import LLMProviderFactory

__all__ = [
    "BaseLLMProvider",
    "LLMProviderError",
    "LLMConnectionError",
    "LLMTimeoutError",
    "LLMResponse",
    "ModelInfo",
    "LLMProviderFactory",
]
