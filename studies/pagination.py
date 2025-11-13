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

        PERFORMANCE OPTIMIZATION: For RawQuerySet, this method now expects
        the service layer to apply LIMIT/OFFSET at database level, avoiding
        the need to fetch all rows into memory before slicing.

        Args:
            queryset: Django QuerySet to paginate (already paginated if RawQuerySet)
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
                query_params = queryset.params or []

                # Convert SELECT * to SELECT COUNT(*)
                # Find the position after FROM clause
                count_sql = raw_sql.replace('SELECT *', 'SELECT COUNT(*)', 1)
                # Remove ORDER BY and LIMIT for count query (optimization)
                if 'ORDER BY' in count_sql:
                    count_sql = count_sql[:count_sql.index('ORDER BY')]
                if 'LIMIT' in count_sql:
                    count_sql = count_sql[:count_sql.index('LIMIT')]

                with connection.cursor() as cursor:
                    # For COUNT query, we only need params up to the WHERE clause
                    # If LIMIT/OFFSET were added, we need to exclude those params
                    # The service layer adds [limit, offset] at the end if pagination applied
                    count_params = query_params
                    if 'LIMIT' in raw_sql:
                        # Remove last 2 params (limit and offset)
                        count_params = query_params[:-2] if len(query_params) >= 2 else query_params

                    cursor.execute(count_sql, count_params)
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

        # PERFORMANCE FIX: For RawQuerySet, don't slice here
        # The service layer already applied LIMIT/OFFSET at database level
        # Just iterate over the queryset which will only contain requested rows
        if hasattr(queryset, 'raw_query'):
            # RawQuerySet - already paginated by service layer
            paginated_items = list(queryset)
        else:
            # Regular QuerySet - apply Python-level slicing
            offset = (page - 1) * page_size
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


class ProjectPaginationInput(BaseModel):
    """Input parameters for project pagination."""

    page: int = 1
    page_size: int = 20


class ProjectPaginationOutput(BaseModel):
    """Standard pagination response for projects."""

    items: List[Any]
    count: int


class ProjectPagination(PaginationBase):
    """Pagination helper for project endpoints."""

    class Input(ProjectPaginationInput):
        pass

    class Output(ProjectPaginationOutput):
        pass

    def paginate_queryset(
        self,
        queryset,
        pagination: Input,
        **params: Any,
    ) -> Dict[str, Any]:
        from .permissions import ProjectPermissions  # Local import to avoid circular deps

        request = params.get('request')
        user = getattr(request, 'user', None)

        total_count = self._get_total_count(queryset)

        page = max(1, pagination.page)
        page_size = pagination.page_size
        if page_size < 1 or page_size > 100:
            page_size = 20

        offset = (page - 1) * page_size
        paginated_projects = self._slice(queryset, offset, page_size)

        items = []
        if paginated_projects and hasattr(paginated_projects[0], 'study'):
            for assignment in paginated_projects:
                study = assignment.study
                assigned_by = assignment.assigned_by
                items.append(
                    {
                        'exam_id': study.exam_id,
                        'patient_name': study.patient_name,
                        'exam_date': study.order_datetime.isoformat() if study.order_datetime else None,
                        'modality': study.exam_source,
                        'assigned_at': assignment.assigned_at,
                        'assigned_by': {
                            'id': str(assigned_by.id),
                            'name': assigned_by.get_full_name() or assigned_by.get_username(),
                            'email': assigned_by.email,
                        },
                    }
                )
        else:
            for project in paginated_projects:
                member_count = getattr(project, 'member_count', None)
                if member_count is None:
                    member_count = project.project_members.count()

                project_dict = project.to_dict()
                project_dict['member_count'] = member_count
                project_dict['user_role'] = ProjectPermissions.get_user_role(project, user)

                items.append(project_dict)

        return {
            'items': items,
            'count': total_count,
        }

    @staticmethod
    def _get_total_count(data: Any) -> int:
        if hasattr(data, 'count'):
            try:
                return data.count()
            except TypeError:
                pass
        if isinstance(data, list):
            return len(data)
        return len(list(data))

    @staticmethod
    def _slice(data: Any, offset: int, limit: int) -> List[Any]:
        if isinstance(data, list):
            return data[offset: offset + limit]
        return list(data[offset: offset + limit])
