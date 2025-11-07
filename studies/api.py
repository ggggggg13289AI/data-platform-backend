"""
Django Ninja API endpoints.
CRITICAL: Response format must match FastAPI exactly (per ../docs/api/API_CONTRACT.md)
Using Pydantic type hints ensures validation and correct serialization.
"""

from typing import Optional, List
from ninja import Router, Query
from ninja.pagination import paginate
from django.http import Http404
from .schemas import StudySearchResponse, StudyDetail, FilterOptions, StudyListItem
from .pagination import StudyPagination
from .services import StudyService
import logging

logger = logging.getLogger(__name__)

# Create router
router = Router()


@router.get('/search', response=List[StudyListItem])
@paginate(StudyPagination)
def search_studies(
    request,
    q: str = Query(default=''),
    exam_status: Optional[str] = Query(None),
    exam_source: Optional[str] = Query(None),
    exam_item: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    sort: str = Query('order_datetime_desc'),
):
    """
    Search medical studies with filters and pagination.
    
    CRITICAL: Response format must match ../docs/api/API_CONTRACT.md exactly.
    
    This endpoint uses Django Ninja's @paginate decorator with custom
    StudyPagination class that supports filter context.
    
    Query Parameters:
    - q: Text search query (searched in patient_name, exam_description, exam_item)
    - exam_status: Filter by exam status (pending, completed, cancelled)
    - exam_source: Filter by exam source (CT, MRI, X-ray, etc.)
    - exam_item: Filter by exam item/type
    - start_date: Order datetime from (ISO 8601)
    - end_date: Order datetime to (ISO 8601)
    - limit: Items per page (default: 20, max: 100)
    - offset: Number of items to skip (default: 0)
    - sort: Sort order (order_datetime_desc, order_datetime_asc, patient_name_asc)
    
    Returns:
    StudySearchResponse with:
    - items: Array of study records
    - count: Total count of matching records
    - filters: Available filter options
    
    The @paginate decorator handles pagination automatically:
    - Extracts limit and offset from query parameters
    - Applies pagination to the queryset
    - Calls StudyPagination.paginate_queryset()
    - Returns formatted StudySearchResponse
    
    Example requests:
    - /api/v1/studies/search?q=chest&limit=10&offset=0
    - /api/v1/studies/search?exam_status=completed&limit=20&offset=20
    """
    try:
        # Call service to get filtered queryset
        # Service no longer handles pagination - that's done by @paginate decorator
        queryset = StudyService.get_studies_queryset(
            q=q if q else None,
            exam_status=exam_status,
            exam_source=exam_source,
            exam_item=exam_item,
            start_date=start_date,
            end_date=end_date,
            sort=sort,
        )
        
        return queryset
    
    except Exception as e:
        logger.error(f'Search failed: {str(e)}')
        raise


@router.get('/{exam_id}', response=StudyDetail)
def get_study_detail(request, exam_id: str):
    """
    Get detailed study information by exam_id.

    Path Parameters:
    - exam_id: The examination ID

    Returns:
    Complete study record details (StudyDetail schema)

    Raises:
    - 404: If study not found
    """
    try:
        study_dict = StudyService.get_study_detail(exam_id)

        if not study_dict:
            raise Http404(f"Study with exam_id '{exam_id}' not found")

        return StudyDetail(**study_dict)

    except Http404:
        raise
    except Exception as e:
        logger.error(f'Failed to get study detail: {str(e)}')
        raise


@router.get('/filters/options', response=FilterOptions)
def get_filter_options(request):
    """
    Get available filter options for search.
    
    Returns all distinct values for filter fields:
    - exam_statuses
    - exam_sources
    - exam_items
    - equipment_types
    
    All values are sorted alphabetically and have no duplicates.
    Matches ../docs/api/API_CONTRACT.md specification.
    
    Returns:
    FilterOptions with all available filter values
    """
    try:
        return StudyService.get_filter_options()
    except Exception as e:
        logger.error(f'Failed to get filter options: {str(e)}')
        raise
