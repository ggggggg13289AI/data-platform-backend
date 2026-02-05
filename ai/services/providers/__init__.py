"""
LLM Providers - Multi-provider LLM integration with factory pattern.

Supported providers:
- Ollama (default)
- LM Studio
- OpenAI-compatible (vLLM, LocalAI, Text Generation WebUI, etc.)
"""

from ai.services.providers.base import (
    BaseLLMProvider,
    LLMProviderError,
    LLMConnectionError,
    LLMTimeoutError,
    LLMResponse,
    ModelInfo,
)
from ai.services.providers.factory import LLMProviderFactory

# Import providers to auto-register them
from ai.services.providers import ollama
from ai.services.providers import lmstudio
from ai.services.providers import openai_compatible

__all__ = [
    "BaseLLMProvider",
    "LLMProviderError",
    "LLMConnectionError",
    "LLMTimeoutError",
    "LLMResponse",
    "ModelInfo",
    "LLMProviderFactory",
]
