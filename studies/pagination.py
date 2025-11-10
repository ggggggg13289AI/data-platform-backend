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
from django.db import connection

from .schemas import FilterOptions
from .services import StudyService


class StudyPaginationInput(BaseModel):
    """Input parameters for study pagination.

    Follows Page-based pagination pattern:
    - page: Page number (1-based, default 1)
    - page_size: Items per page (default 20, max 100)
    """
    page: int = 1  # Default to first page
    page_size: int = 20  # Default page size


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
    1. Page-based pagination parameters (page, page_size)
    2. Standard pagination output (items, count)
    3. Additional filter context (filters)

    Usage in API:
        @api.get('/search', response=StudySearchResponse)
        @paginate(StudyPagination)
        def search_studies(request, ...):
            return Study.objects.filter(...)

    The paginate decorator will:
    1. Extract page and page_size from query parameters
    2. Calculate offset: (page - 1) * page_size
    3. Apply pagination to the queryset
    4. Call paginate_queryset() with the paginated data
    5. Return StudyPaginationOutput format
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
            pagination: Input parameters (page, page_size)
            **params: Additional parameters from the request

        Returns:
            Dictionary with paginated items and metadata
        """
        # Get total count before pagination
        # Handle RawQuerySet (from raw SQL) vs regular QuerySet
        if hasattr(queryset, 'count'):
            # Regular QuerySet has count() method
            total_count = queryset.count()
        else:
            # RawQuerySet doesn't support count()
            # Need to execute a separate COUNT query with same WHERE clause
            # Extract raw_query and params from RawQuerySet
            try:
                # Access the raw SQL and params from RawQuerySet
                raw_sql = queryset.raw_query
                params = queryset.params or []

                # Convert SELECT * to SELECT COUNT(*)
                # Find the position after FROM clause
                count_sql = raw_sql.replace('SELECT *', 'SELECT COUNT(*)', 1)
                # Remove ORDER BY for count query (optimization)
                if 'ORDER BY' in count_sql:
                    count_sql = count_sql[:count_sql.index('ORDER BY')]

                with connection.cursor() as cursor:
                    cursor.execute(count_sql, params)
                    total_count = cursor.fetchone()[0]
            except (AttributeError, Exception):
                # Fallback: count by iterating (less efficient but works)
                total_count = len(list(queryset))
        
        # Extract page and page_size from pagination input
        page = pagination.page
        page_size = pagination.page_size

        # Validate pagination parameters
        if page < 1:
            page = 1
        if page_size < 1 or page_size > 100:
            page_size = 20

        # Calculate offset from page and page_size
        offset = (page - 1) * page_size

        # Get paginated items
        paginated_items = queryset[offset : offset + page_size]
        
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
