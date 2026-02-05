"""
AI Services - LLM integration, analysis services, and review workflows.

This package provides:
- LLMService: Multi-provider LLM integration (Ollama, LM Studio, vLLM, etc.)
- LLMProviderFactory: Factory for creating LLM provider instances
- GuidelineService: Classification guideline management with version control
- BatchAnalysisService: Batch AI analysis execution
- SamplingService: Stratified and random sampling
- ReviewService: Physician review workflow management
"""

from ai.services.batch_analysis_service import (
    BatchAnalysisError,
    BatchAnalysisService,
    BatchAnalysisTaskNotFoundError,
)
from ai.services.guideline_service import (
    GuidelineNotFoundError,
    GuidelineService,
    GuidelineServiceError,
    GuidelineStatusError,
    GuidelineVersionError,
)
from ai.services.llm_service import (
    LLMConnectionError,
    LLMService,
    LLMTimeoutError,
    get_llm_service,
    clear_llm_service_cache,
)
from ai.services.providers import (
    LLMProviderFactory,
    BaseLLMProvider,
    LLMResponse,
    ModelInfo,
)
from ai.services.review_service import (
    ReviewSampleNotFoundError,
    ReviewService,
    ReviewServiceError,
    ReviewTaskNotFoundError,
)
from ai.services.sampling_service import (
    SamplingError,
    SamplingService,
)

__all__ = [
    # LLM Service & Providers
    "LLMService",
    "LLMConnectionError",
    "LLMTimeoutError",
    "LLMResponse",
    "ModelInfo",
    "get_llm_service",
    "clear_llm_service_cache",
    "LLMProviderFactory",
    "BaseLLMProvider",
    # Guideline Service
    "GuidelineService",
    "GuidelineServiceError",
    "GuidelineNotFoundError",
    "GuidelineStatusError",
    "GuidelineVersionError",
    # Batch Analysis Service
    "BatchAnalysisService",
    "BatchAnalysisError",
    "BatchAnalysisTaskNotFoundError",
    # Sampling Service
    "SamplingService",
    "SamplingError",
    # Review Service
    "ReviewService",
    "ReviewServiceError",
    "ReviewTaskNotFoundError",
    "ReviewSampleNotFoundError",
]
