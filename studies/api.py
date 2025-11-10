"""
Django Ninja API endpoints.
CRITICAL: Response format must match FastAPI exactly (per ../docs/api/API_CONTRACT.md)
Using Pydantic type hints ensures validation and correct serialization.
"""

from typing import Optional, List
from ninja import Router, Query
from ninja.pagination import paginate
from django.http import Http404
from .schemas import StudyDetail, FilterOptions, StudyListItem
from .pagination import StudyPagination
from .services import StudyService
from .exceptions import StudyNotFoundError, DatabaseQueryError
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
    exam_equipment: Optional[List[str]] = Query(None),
    application_order_no: Optional[str] = Query(None),
    patient_gender: Optional[List[str]] = Query(None),
    exam_description: Optional[List[str]] = Query(None),
    exam_room: Optional[List[str]] = Query(None),
    patient_age_min: Optional[int] = Query(None),
    patient_age_max: Optional[int] = Query(None),
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
    - q: Text search query (searched across 9 fields: exam_id, medical_record_no, etc.)
    - exam_status: Filter by exam status (pending, completed, cancelled)
    - exam_source: Filter by exam source (CT, MRI, X-ray, etc.)
    - exam_equipment: Filter by equipment (multi-select array)
    - application_order_no: Filter by application order number (exact match)
    - patient_gender: Filter by patient gender (multi-select array)
    - exam_description: Filter by exam description (multi-select array)
    - exam_room: Filter by exam room (multi-select array)
    - patient_age_min: Filter by minimum patient age
    - patient_age_max: Filter by maximum patient age
    - start_date: Check-in datetime from (YYYY-MM-DD format)
    - end_date: Check-in datetime to (YYYY-MM-DD format)
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
        # CRITICAL FIX: Handle array parameters with brackets (e.g., patient_gender[]=F)
        # Frontend sends patient_gender[]=F, but Django Ninja Query expects patient_gender=F
        # We need to manually extract from request.GET to support both formats

        def get_array_param(param_name: str) -> Optional[List[str]]:
            """
            Extract array parameter supporting both formats:
            - patient_gender[]=F (frontend format)
            - patient_gender=F&patient_gender=M (Django Ninja format)
            """
            # Try bracket format first
            bracket_values = request.GET.getlist(f'{param_name}[]')
            if bracket_values:
                return [v for v in bracket_values if v]  # Filter empty strings

            # Try standard format
            standard_values = request.GET.getlist(param_name)
            if standard_values:
                return [v for v in standard_values if v]  # Filter empty strings

            return None

        # Extract array parameters with bracket support
        exam_equipment_array = get_array_param('exam_equipment') or exam_equipment
        patient_gender_array = get_array_param('patient_gender') or patient_gender
        exam_description_array = get_array_param('exam_description') or exam_description
        exam_room_array = get_array_param('exam_room') or exam_room

        # Call service to get filtered queryset
        # Service no longer handles pagination - that's done by @paginate decorator
        queryset = StudyService.get_studies_queryset(
            q=q if q else None,
            exam_status=exam_status,
            exam_source=exam_source,
            exam_equipment=exam_equipment_array,
            application_order_no=application_order_no,
            patient_gender=patient_gender_array,
            exam_description=exam_description_array,
            exam_room=exam_room_array,
            patient_age_min=patient_age_min,
            patient_age_max=patient_age_max,
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
    - 500: If database error occurs
    """
    try:
        study_dict = StudyService.get_study_detail(exam_id)
        return StudyDetail(**study_dict)

    except StudyNotFoundError as e:
        # Convert domain exception to HTTP 404
        raise Http404(str(e))
    except DatabaseQueryError as e:
        # Log database errors and let Django Ninja handle as 500
        logger.error(f'Database error in get_study_detail: {str(e)}')
        raise
    except Exception as e:
        logger.error(f'Unexpected error in get_study_detail: {str(e)}')
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

    Raises:
    - 500: If database error occurs

    Note: Cache failures are logged but don't affect response (graceful degradation)
    """
    try:
        return StudyService.get_filter_options()
    except DatabaseQueryError as e:
        # Log database errors and let Django Ninja handle as 500
        logger.error(f'Database error in get_filter_options: {str(e)}')
        raise
    except Exception as e:
        logger.error(f'Unexpected error in get_filter_options: {str(e)}')
        raise
