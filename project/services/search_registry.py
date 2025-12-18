from dataclasses import dataclass
from typing import Any, Callable, Dict, List
import logging

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    resource_type: str
    accession_number: str
    score: float
    snippet: str
    resource_payload: Dict[str, Any]
    resource_timestamp: str


class ProjectSearchRegistry:
    _providers: Dict[str, Callable[[str, str, int], List[SearchResult]]] = {}

    @classmethod
    def register_provider(
        cls,
        resource_type: str,
        provider_func: Callable[[str, str, int], List[SearchResult]],
    ) -> Callable[[str, str, int], List[SearchResult]]:
        cls._providers[resource_type] = provider_func
        return provider_func

    @classmethod
    def register(cls, resource_type: str):
        def decorator(func: Callable[[str, str, int], List[SearchResult]]):
            return cls.register_provider(resource_type, func)

        return decorator

    @classmethod
    def search(
        cls,
        project_id: str,
        query: str,
        resource_types: List[str] | None = None,
        per_provider_limit: int = 50,
    ) -> List[SearchResult]:
        providers = cls._providers
        if resource_types:
            providers = {
                name: provider
                for name, provider in providers.items()
                if name in resource_types
            }

        results: list[SearchResult] = []
        for resource_type, provider in providers.items():
            try:
                provider_results = provider(project_id, query, per_provider_limit)
                results.extend(provider_results)
            except Exception as exc:
                logger.error(f"Search provider {resource_type} failed: {exc}")
                continue

        cls._normalize_scores(results)
        results.sort(
            key=lambda item: (
                item.score,
                item.resource_timestamp or '',
            ),
            reverse=True,
        )
        return results

    @staticmethod
    def _normalize_scores(results: List[SearchResult]) -> None:
        max_score = max((item.score for item in results), default=0.0)
        if max_score <= 0:
            for item in results:
                item.score = 0.0
            return
        for item in results:
            item.score = item.score / max_score


