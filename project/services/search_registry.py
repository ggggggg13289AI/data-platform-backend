from typing import List, Dict, Any, Callable
from dataclasses import dataclass
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
    _providers: Dict[str, Callable[[str, str], List[SearchResult]]] = {}

    @classmethod
    def register(cls, resource_type: str):
        def decorator(func):
            cls._providers[resource_type] = func
            return func
        return decorator

    @classmethod
    def search(cls, project_id: str, query: str) -> List[SearchResult]:
        results = []
        for r_type, provider in cls._providers.items():
            try:
                # Provider signature: (project_id, query) -> List[SearchResult]
                provider_results = provider(project_id, query)
                results.extend(provider_results)
            except Exception as e:
                logger.error(f"Search provider {r_type} failed: {e}")
                continue
        
        # Sort by score desc
        results.sort(key=lambda x: x.score, reverse=True)
        return results

