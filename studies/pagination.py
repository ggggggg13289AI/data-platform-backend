"""
Custom pagination for Django Ninja studies API.

Implements Django Ninja's PaginationBase to provide LimitOffsetPagination
with additional filter context in the response.

Reference: https://django-ninja.dev/guides/response/pagination/
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel
from ninja.pagination import PaginationBase
from django.db.models import QuerySet

from .schemas import FilterOptions
from .services import StudyService


class StudyPaginationInput(BaseModel):
    """Input parameters for study pagination.
    
    Follows LimitOffsetPagination pattern:
    - limit: Items per page (max 100)
    - offset: Number of items to skip
    """
    limit: int = 20  # Default page size
    offset: int = 0  # Default start at first item


class StudyPaginationOutput(BaseModel):
    """Output format for paginated study responses.
    
    Extends standard pagination with filter options for API compatibility.
    
    Note: Django Ninja's @paginate decorator wraps the paginate_queryset
    output with this format automatically.
    """
    items: List[Any]  # List of StudyListItem dictionaries
    count: int  # Total number of items
    filters: FilterOptions  # Available filter options (custom extension)


class StudyPagination(PaginationBase):
    """
    Custom pagination class for studies endpoint.
    
    This implements Django Ninja's PaginationBase to provide:
    1. LimitOffsetPagination parameters (limit, offset)
    2. Standard pagination output (items, count)
    3. Additional filter context (filters)
    
    Usage in API:
        @api.get('/search', response=StudySearchResponse)
        @paginate(StudyPagination)
        def search_studies(request, ...):
            return Study.objects.filter(...)
    
    The paginate decorator will:
    1. Extract limit and offset from query parameters
    2. Apply pagination to the queryset
    3. Call paginate_queryset() with the paginated data
    4. Return StudyPaginationOutput format
    """
    
    class Input(StudyPaginationInput):
        """Input parameters for pagination."""
        pass
    
    class Output(StudyPaginationOutput):
        """Output format for paginated responses."""
        pass
    
    def paginate_queryset(
        self,
        queryset: QuerySet,
        pagination: Input,
        **params: Any
    ) -> Dict[str, Any]:
        """
        Paginate the queryset and return formatted output.
        
        Args:
            queryset: Django QuerySet to paginate
            pagination: Input parameters (limit, offset)
            **params: Additional parameters from the request
        
        Returns:
            Dictionary with paginated items and metadata
        """
        # Get total count before pagination
        total_count = queryset.count()
        
        # Apply offset and limit
        offset = pagination.offset
        limit = pagination.limit
        
        # Validate pagination parameters
        if offset < 0:
            offset = 0
        if limit < 1 or limit > 100:
            limit = 20
        
        # Get paginated items
        paginated_items = queryset[offset : offset + limit]
        
        # Convert queryset to list of dicts for schema conversion
        items = [item.to_dict() for item in paginated_items]
        
        # Get filter options (cached after first request)
        filters = StudyService.get_filter_options()
        
        # Return as dictionary for Django Ninja compatibility
        return {
            'items': items,
            'count': total_count,
            'filters': filters,
        }
