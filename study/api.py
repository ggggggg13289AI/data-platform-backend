"""
Django Ninja API endpoints for Study operations.

This module defines all HTTP endpoints for the Study API. It provides a RESTful
interface for searching, filtering, exporting, and retrieving medical examination
records.

Architecture:
    - router: Main entry point for all study endpoints
    - @router.get('/search'): Paginated search with filters
    - @router.get('/export'): Export filtered results to CSV/Excel
    - @router.get('/{exam_id}'): Get detailed study information
    - @router.get('/filters/options'): Get available filter values

API Design Principles:
    1. RESTful endpoints following standard conventions
    2. Query parameters for filtering and pagination
    3. JSON responses matching API_CONTRACT specification
    4. Consistent error handling and HTTP status codes
    5. Pagination support for large result sets

CRITICAL: Response format MUST match FastAPI exactly (per ../docs/api/API_CONTRACT.md)
Using Pydantic type hints ensures validation and correct serialization.

Type Hints & Validation:
    - All endpoints use Pydantic schemas for request/response validation
    - Query parameters automatically parsed and validated
    - Invalid parameters rejected with 422 Unprocessable Entity
    - Response serialization: Django model → dict → JSON

Error Handling:
    - StudyNotFoundError → 404 Not Found
    - DatabaseQueryError → 500 Internal Server Error
    - Invalid parameters → 422 Unprocessable Entity
    - All errors logged for monitoring

See Also:
    - Schemas: study.schemas
    - Service: study.services.StudyService
    - Models: study.models.Study
    - API Contract: ../docs/api/API_CONTRACT.md
"""

import logging

from django.http import Http404, HttpResponse
from ninja import Query, Router
from ninja.pagination import paginate

from common.exceptions import DatabaseQueryError, StudyNotFoundError
from common.export_service import ExportConfig, ExportService
from common.pagination import StudyPagination
from study.schemas import FilterOptions, StudyDetail, StudyListItem
from study.services import StudyService

logger = logging.getLogger(__name__)

# ========== ROUTER SETUP ==========
# Create router for all study endpoints
# Endpoints will be mounted at /api/v1/studies/ prefix
router = Router()


@router.get("/search", response=list[StudyListItem])
@paginate(StudyPagination)
def search_studies(
    request,
    q: str = Query(default=""),
    exam_status: str | None = Query(None),
    exam_source: str | None = Query(None),
    exam_equipment: list[str] | None = Query(None),
    exam_item: str | None = Query(None),
    application_order_no: str | None = Query(None),
    patient_gender: list[str] | None = Query(None),
    exam_description: list[str] | None = Query(None),
    exam_room: list[str] | None = Query(None),
    patient_age_min: int | None = Query(None),
    patient_age_max: int | None = Query(None),
    start_date: str | None = Query(None),
    end_date: str | None = Query(None),
    sort: str = Query("order_datetime_desc"),
):
    """
    Search medical examination studies with advanced filtering and pagination.

    Provides a comprehensive search interface for finding medical examination
    records based on multiple criteria including text search, date ranges, and
    enumerated filters. Results are paginated for efficient data transfer.

    HTTP Method: GET
    Path: /api/v1/studies/search
    Response Format: StudySearchResponse (paginated)

    Request Format (Query Parameters):
        Text Search:
            - q (str): Text search query (default: '')
                Searched across 9 fields: exam_id, medical_record_no, application_order_no,
                patient_name, exam_description, exam_item, exam_room, exam_equipment,
                certified_physician
                Case-insensitive PostgreSQL ILIKE search
                Max length: 200 characters
                Example: q=chest

        Exact Match Filters:
            - exam_status (str | None): Examination status filter
                Valid values: 'pending', 'completed', 'cancelled'
                Example: exam_status=completed

            - exam_source (str | None): Examination modality/source
                Examples: 'CT', 'MRI', 'X-ray', 'Ultrasound'
                Example: exam_source=CT

            - application_order_no (str | None): Application order number
                Example: application_order_no=ORD_12345

        Multi-Select Filters (Array Parameters):
            - exam_equipment (list[str] | None): Equipment filter
                Format: exam_equipment=val1&exam_equipment=val2
                or with brackets: exam_equipment[]=val1&exam_equipment[]=val2
                Example: exam_equipment=GE&exam_equipment=Siemens

            - patient_gender (list[str] | None): Gender filter
                Valid values: 'M', 'F', 'U'
                Format: patient_gender=M&patient_gender=F

            - exam_description (list[str] | None): Description filter
                Format: exam_description=val1&exam_description=val2

            - exam_room (list[str] | None): Room/facility filter
                Format: exam_room=RoomA&exam_room=RoomB

        Range Filters:
            - patient_age_min (int | None): Minimum patient age (inclusive)
                Example: patient_age_min=18

            - patient_age_max (int | None): Maximum patient age (inclusive)
                Example: patient_age_max=65

            - start_date (str | None): Start date (ISO 8601: YYYY-MM-DD)
                Filters check_in_datetime >= start_date
                Example: start_date=2024-01-01

            - end_date (str | None): End date (ISO 8601: YYYY-MM-DD)
                Filters check_in_datetime <= end_date
                Example: end_date=2024-12-31

        Sorting & Pagination:
            - sort (str): Sort order (default: 'order_datetime_desc')
                Valid values:
                  - 'order_datetime_desc': Newest first (default)
                  - 'order_datetime_asc': Oldest first
                  - 'patient_name_asc': Alphabetical by patient name
                Example: sort=order_datetime_desc

            - limit (int): Items per page (default: 20, max: 100)
                Clamped to 1-100 range
                Example: limit=20

            - offset (int): Number of items to skip (default: 0)
                Example: offset=20  (skip first 20, get items 21-40 with limit=20)

    Response Format (StudySearchResponse):
        {
            "items": [
                {
                    "exam_id": "EXAM_001",
                    "patient_name": "张三",
                    "exam_status": "completed",
                    "order_datetime": "2024-01-15T14:30:00",
                    ...
                }
            ],
            "count": 42,
            "filters": {
                "exam_statuses": ["cancelled", "completed", "pending"],
                "exam_sources": ["CT", "MRI"],
                ...
            }
        }

    Response Fields:
        - items (list[StudyListItem]): Paginated study records
        - count (int): Total matching records (not affected by pagination)
        - filters (FilterOptions): Available filter values for UI

    HTTP Status Codes:
        - 200 OK: Success, results returned
        - 422 Unprocessable Entity: Invalid parameter types or ranges
        - 500 Internal Server Error: Database error

    Pagination Calculation:
        offset = (page - 1) * page_size
        Example: limit=20, offset=20 retrieves items 21-40

    Pagination Implementation:
        The @paginate(StudyPagination) decorator:
        1. Extracts limit and offset from query parameters
        2. Passes to service layer for database-level pagination
        3. Gets total count separately
        4. Fetches filter options
        5. Constructs StudySearchResponse

    Performance Characteristics:
        - Empty query (all records): ~100-500ms depending on DB size
        - Text search (q parameter): ~200-1000ms depending on search complexity
        - With filters: ~100-300ms (indexed columns)
        - Filter options fetched from cache (24-hour TTL): ~10ms

    Example Requests:
        1. Simple text search with pagination:
           GET /api/v1/studies/search?q=chest&limit=10&offset=0

        2. Filter by status and date range:
           GET /api/v1/studies/search?exam_status=completed&start_date=2024-01-01&end_date=2024-12-31&limit=20

        3. Multi-select filter:
           GET /api/v1/studies/search?exam_equipment=GE&exam_equipment=Siemens&limit=50

        4. Complex query with multiple filters:
           GET /api/v1/studies/search?q=follow-up&exam_source=CT&exam_status=completed&patient_age_min=18&patient_age_max=65&sort=order_datetime_desc&limit=20

    CRITICAL: Response format MUST match ../docs/api/API_CONTRACT.md exactly.
    This ensures consistency with API specification and frontend expectations.

    See Also:
        - Detail endpoint: GET /api/v1/studies/{exam_id}
        - Export endpoint: GET /api/v1/studies/export
        - Filter options: GET /api/v1/studies/filters/options
        - Service layer: study.services.StudyService.get_studies_queryset()
        - Schema: study.schemas.StudySearchResponse
        - Pagination: common.pagination.StudyPagination
        - API Contract: ../docs/api/API_CONTRACT.md
    """
    try:
        # CRITICAL FIX: Handle array parameters with brackets (e.g., patient_gender[]=F)
        # Frontend sends patient_gender[]=F, but Django Ninja Query expects patient_gender=F
        # We need to manually extract from request.GET to support both formats

        def get_array_param(param_name: str) -> list[str] | None:
            """
            Extract array parameter supporting both formats:
            - patient_gender[]=F (frontend format)
            - patient_gender=F&patient_gender=M (Django Ninja format)
            """
            # Try bracket format first
            bracket_values = request.GET.getlist(f"{param_name}[]")
            if bracket_values:
                return [v for v in bracket_values if v]  # Filter empty strings

            # Try standard format
            standard_values = request.GET.getlist(param_name)
            if standard_values:
                return [v for v in standard_values if v]  # Filter empty strings

            return None

        # Extract array parameters with bracket support
        exam_equipment_array = get_array_param("exam_equipment") or exam_equipment
        patient_gender_array = get_array_param("patient_gender") or patient_gender
        exam_description_array = get_array_param("exam_description") or exam_description
        exam_room_array = get_array_param("exam_room") or exam_room

        # Extract pagination parameters from request
        # Support BOTH old (limit/offset) and new (page/page_size) parameter formats
        # for backward compatibility with existing tests and clients

        # Try new format first (page/page_size)
        if "page" in request.GET or "page_size" in request.GET:
            page = int(request.GET.get("page", 1))
            page_size = int(request.GET.get("page_size", 20))

            # Validate pagination parameters
            page = max(1, page)  # Page must be at least 1
            page_size = max(1, min(100, page_size))  # Page size between 1 and 100
            offset = (page - 1) * page_size
        else:
            # Fall back to old format (limit/offset) for backward compatibility
            limit = int(request.GET.get("limit", 20))
            offset = int(request.GET.get("offset", 0))

            # Validate parameters
            # If limit is < 1, use default of 20
            if limit < 1:
                page_size = 20
            else:
                page_size = min(100, limit)  # Clamp to max 100
            offset = max(0, offset)  # Offset must be non-negative

        # PERFORMANCE OPTIMIZATION: Pass limit/offset to service layer
        # This allows the service to apply LIMIT/OFFSET at database level
        # reducing query time from 5000ms+ to <100ms for paginated results
        queryset = StudyService.get_studies_queryset(
            q=q if q else None,
            exam_status=exam_status,
            exam_source=exam_source,
            exam_equipment=exam_equipment_array,
            exam_item=exam_item,
            application_order_no=application_order_no,
            patient_gender=patient_gender_array,
            exam_description=exam_description_array,
            exam_room=exam_room_array,
            patient_age_min=patient_age_min,
            patient_age_max=patient_age_max,
            start_date=start_date,
            end_date=end_date,
            sort=sort,
            limit=page_size,
            offset=offset,
        )

        return queryset

    except Exception as e:
        logger.error(f"Search failed: {str(e)}")
        raise


@router.get("/export", response={200: None})
def export_studies(
    request,
    format: str = Query("csv", description="Export format: csv or xlsx"),
    q: str = Query(default=""),
    exam_status: str | None = Query(None),
    exam_source: str | None = Query(None),
    exam_equipment: list[str] | None = Query(None),
    application_order_no: str | None = Query(None),
    patient_gender: list[str] | None = Query(None),
    exam_description: list[str] | None = Query(None),
    exam_room: list[str] | None = Query(None),
    patient_age_min: int | None = Query(None),
    patient_age_max: int | None = Query(None),
    start_date: str | None = Query(None),
    end_date: str | None = Query(None),
    sort: str = Query("order_datetime_desc"),
    exam_ids: list[str] | None = Query(None),
):
    """
    Export filtered study records as CSV or Excel file.

    This endpoint supports the same filters as the search endpoint but returns
    a downloadable file instead of JSON response. Users can export search results
    for external analysis, reporting, or archival.

    HTTP Method: GET
    Path: /api/v1/studies/export
    Response: File attachment (binary/text)

    Export Formats:
        CSV (Comma-Separated Values):
            - Content-Type: text/csv; charset=utf-8-sig
            - Encoding: UTF-8 with BOM (Excel compatibility)
            - Line endings: CRLF (Windows/Excel standard)
            - Delimiter: Comma (,)
            - Quote character: Double quote (") when needed
            - File extension: .csv
            - Typical file size: ~100KB per 1000 records

        XLSX (Excel Workbook):
            - Content-Type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet
            - Format: Office Open XML spreadsheet
            - Encoding: UTF-8 (XML-based)
            - File extension: .xlsx
            - Typical file size: ~50KB per 1000 records
            - Features: Formulas, formatting, multiple sheets (if supported)

    Query Parameters (Same as Search Endpoint):
        format (str): Export format
            Default: 'csv'
            Valid values: 'csv', 'xlsx'
            Invalid values: Defaults to 'csv'

        q (str): Text search query (same as search endpoint)

        exam_status (str | None): Status filter (same as search endpoint)

        exam_source (str | None): Modality filter (same as search endpoint)

        exam_equipment (list[str] | None): Multi-select equipment filter

        application_order_no (str | None): Order number filter

        patient_gender (list[str] | None): Multi-select gender filter

        exam_description (list[str] | None): Multi-select description filter

        exam_room (list[str] | None): Multi-select room filter

        patient_age_min (int | None): Minimum age filter

        patient_age_max (int | None): Maximum age filter

        start_date (str | None): Start date filter (YYYY-MM-DD)

        end_date (str | None): End date filter (YYYY-MM-DD)

        sort (str): Sort order
            Default: 'order_datetime_desc' (newest first)

        exam_ids (list[str] | None): Specific exam IDs to export
            Used for "Export Selected" feature
            Overrides other filters when provided
            Format: exam_ids=ID1&exam_ids=ID2&exam_ids=ID3

    Response Headers:
        Content-Type: text/csv or application/vnd.openxmlformats-...
        Content-Disposition: attachment; filename="{filename}"
            Instructs browser to download as file
            Filename format: studies_{timestamp}.csv or studies_{timestamp}.xlsx

        Access-Control-Expose-Headers: Content-Disposition
            Allows browser to access Content-Disposition in CORS requests

    Response Example (Headers):
        HTTP/1.1 200 OK
        Content-Type: text/csv; charset=utf-8-sig
        Content-Length: 125432
        Content-Disposition: attachment; filename="studies_20240115_143000.csv"

    File Format:
        CSV Headers (Column Names):
            exam_id, medical_record_no, application_order_no, patient_name,
            patient_gender, patient_birth_date, patient_age, exam_status,
            exam_source, exam_item, exam_description, exam_room, exam_equipment,
            equipment_type, order_datetime, check_in_datetime,
            report_certification_datetime, certified_physician, data_load_time

        XLSX Headers:
            Same column headers in first row, with automatic formatting
            Columns auto-sized for readability

    Performance & Limits:
        - Maximum export size: 10,000 records (to prevent memory issues)
        - Typical performance: 1000 records → 2-5 seconds
        - File generation time: ~1ms per record
        - Network transfer: Depends on file size and connection speed

    HTTP Status Codes:
        - 200 OK: Export successful, file returned
        - 422 Unprocessable Entity: Invalid format or parameter types
        - 500 Internal Server Error: Database or export generation error

    Error Handling:
        - Invalid format: Defaults to CSV
        - Database query error: Returns 500 with error details
        - Export generation error: Returns 500 with error details
        - All errors logged for debugging

    Use Cases:
        1. Export search results for analysis:
           GET /api/v1/studies/export?format=csv&q=chest&limit=100

        2. Export by status and date:
           GET /api/v1/studies/export?format=xlsx&exam_status=completed&start_date=2024-01-01

        3. Export selected records (from UI checkboxes):
           GET /api/v1/studies/export?format=xlsx&exam_ids=ID123&exam_ids=ID456&exam_ids=ID789

        4. Export with complex filters:
           GET /api/v1/studies/export?format=csv&exam_source=CT&patient_age_min=18&patient_age_max=65

    Browser Behavior:
        - Most browsers automatically download files with Content-Disposition: attachment
        - File saved to default download folder with specified filename
        - Users can then open in Excel, Numbers, or text editor

    Data Privacy Considerations:
        - No data modification: Export contains exact database values
        - No PII masking: Full patient information included
        - Access control: Check authentication/authorization at app level
        - Audit logging: Export operations should be logged for compliance

    Excel Features:
        - XLSX format preserves datetime formatting
        - Column widths optimized for readability
        - Future enhancement: Add styling, formulas, pivot tables

    Example Requests:
        1. Export all completed studies as CSV:
           GET /api/v1/studies/export?format=csv&exam_status=completed

        2. Export with advanced filtering:
           GET /api/v1/studies/export?format=xlsx&exam_source=CT&exam_status=completed&start_date=2024-01-01

        3. Export selected records:
           GET /api/v1/studies/export?format=xlsx&exam_ids=EXAM_001&exam_ids=EXAM_002

        4. Export with text search:
           GET /api/v1/studies/export?format=csv&q=chest&sort=order_datetime_desc

    See Also:
        - Search endpoint: GET /api/v1/studies/search
        - Detail endpoint: GET /api/v1/studies/{exam_id}
        - Export service: common.export_service.ExportService
        - Schema: study.schemas.StudyListItem
    """
    try:
        # Validate export format
        if format not in ExportConfig.ALLOWED_EXPORT_FORMATS:
            format = ExportConfig.DEFAULT_EXPORT_FORMAT

        # Handle array parameters with bracket support (same as search endpoint)
        def get_array_param(param_name: str) -> list[str] | None:
            """Extract array parameter supporting both bracket and standard formats."""
            bracket_values = request.GET.getlist(f"{param_name}[]")
            if bracket_values:
                return [v for v in bracket_values if v]
            standard_values = request.GET.getlist(param_name)
            if standard_values:
                return [v for v in standard_values if v]
            return None

        # Extract array parameters with bracket support
        exam_equipment_array = get_array_param("exam_equipment") or exam_equipment
        patient_gender_array = get_array_param("patient_gender") or patient_gender
        exam_description_array = get_array_param("exam_description") or exam_description
        exam_room_array = get_array_param("exam_room") or exam_room
        exam_ids_array = get_array_param("exam_ids") or exam_ids

        # Get filtered queryset (reusing search logic)
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
            exam_ids=exam_ids_array,
        )

        # Generate export based on format
        if format == "xlsx":
            content = ExportService.export_to_excel(queryset)
            content_type = ExportService.get_content_type("xlsx")
            filename = ExportService.generate_export_filename("xlsx")
        else:  # Default to CSV
            content = ExportService.export_to_csv(queryset)
            content_type = ExportService.get_content_type("csv")
            filename = ExportService.generate_export_filename("csv")

        # Create HTTP response with file download
        response = HttpResponse(content, content_type=content_type)
        response["Content-Disposition"] = f'attachment; filename="{filename}"'

        # Add CORS headers if needed
        response["Access-Control-Expose-Headers"] = "Content-Disposition"

        logger.info(f"Export generated: {filename} ({len(content)} bytes)")
        return response

    except DatabaseQueryError as e:
        logger.error(f"Database error in export_studies: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Export failed: {str(e)}")
        raise


@router.get("/{exam_id}", response=StudyDetail)
def get_study_detail(request, exam_id: str):
    """
    Get complete study information by examination ID.

    Retrieves a single study record with all available fields by its primary key.
    This endpoint provides comprehensive details for viewing full examination records.

    HTTP Method: GET
    Path: /api/v1/studies/{exam_id}
    Response Schema: StudyDetail

    Path Parameters:
        exam_id (str): Unique examination identifier
            Example: "EXAM_001"
            This is the primary key for the study record

    Response Fields:
        Complete StudyDetail schema including:
        - All patient demographics
        - Complete examination details
        - All temporal information (order, check-in, certification times)
        - Physician certification
        - Data load timestamp

        All datetime fields in ISO 8601 format (YYYY-MM-DDTHH:MM:SS)
        Optional fields may be None/null

    Response Example:
        {
            "exam_id": "EXAM_001",
            "patient_name": "张三",
            "patient_age": 45,
            "exam_status": "completed",
            "exam_source": "CT",
            "exam_item": "Chest CT",
            "order_datetime": "2024-01-15T14:30:00",
            "check_in_datetime": "2024-01-15T14:45:00",
            "report_certification_datetime": "2024-01-15T16:30:00",
            ...
        }

    HTTP Status Codes:
        - 200 OK: Study found, details returned
        - 404 Not Found: Study with given exam_id does not exist
        - 500 Internal Server Error: Database error

    Performance:
        - Primary key lookup: <10ms (indexed)
        - Dictionary conversion: <1ms
        - Total response time: ~15ms typical

    Error Handling:
        - StudyNotFoundError: exam_id doesn't exist
            Returns 404 Not Found with error message

        - DatabaseQueryError: Database connection/query failure
            Returns 500 Internal Server Error
            Exception logged for debugging

    Example Requests:
        1. Get specific examination:
           GET /api/v1/studies/EXAM_001

        2. With various IDs:
           GET /api/v1/studies/MRN_20240115_001
           GET /api/v1/studies/CT_CHEST_2024_042

    See Also:
        - List/search endpoint: GET /api/v1/studies/search
        - Export endpoint: GET /api/v1/studies/export
        - Schema: study.schemas.StudyDetail
        - Service layer: study.services.StudyService.get_study_detail()
    """
    try:
        study_dict = StudyService.get_study_detail(exam_id)
        return StudyDetail(**study_dict)

    except StudyNotFoundError as e:
        # Convert domain exception to HTTP 404
        raise Http404(str(e)) from e
    except DatabaseQueryError as e:
        # Log database errors and let Django Ninja handle as 500
        logger.error(f"Database error in get_study_detail: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error in get_study_detail: {str(e)}")
        raise


@router.get("/filters/options", response=FilterOptions, operation_id="study_get_filter_options")
def get_filter_options(request):
    """
    Get available filter options for UI dropdowns and faceted search.

    Returns all distinct values for each filterable field, used by the frontend
    to populate filter selection menus in the search interface. Results are
    cached for 24 hours to reduce database load.

    HTTP Method: GET
    Path: /api/v1/studies/filters/options
    Response Schema: FilterOptions
    Operation ID: study_get_filter_options

    Response Fields:
        exam_statuses (list[str]): All distinct examination statuses
            Sorted alphabetically
            Examples: ["cancelled", "completed", "pending"]

        exam_sources (list[str]): All distinct examination modalities
            Sorted alphabetically
            Examples: ["CT", "MRI", "X-ray", "Ultrasound"]

        equipment_types (list[str]): All distinct equipment type classifications
            Sorted alphabetically
            Examples: ["CT Scanner", "MRI Scanner", "X-ray Machine"]

        exam_rooms (list[str]): All distinct examination rooms/facilities
            Sorted alphabetically
            Examples: ["Operating Theater 1", "Room A", "Room B"]

        exam_equipments (list[str]): All distinct equipment names/models
            Sorted alphabetically
            Examples: ["GE LightSpeed 16", "Siemens SOMATOM"]

        exam_descriptions (list[str]): All distinct examination descriptions
            Limited to 100 rows to prevent excessive response size
            Sorted alphabetically
            Examples: ["Follow-up imaging", "Routine chest scan"]

    Response Example:
        {
            "exam_statuses": ["cancelled", "completed", "pending"],
            "exam_sources": ["CT", "MRI", "X-ray"],
            "equipment_types": ["CT Scanner", "MRI Scanner"],
            "exam_rooms": ["Room A", "Room B", "Room C"],
            "exam_equipments": ["GE LightSpeed", "Siemens SOMATOM"],
            "exam_descriptions": ["Routine imaging", "Follow-up scan"]
        }

    Caching Strategy:
        - Cache Key: 'study_filter_options'
        - Cache TTL: 24 hours (filters change infrequently)
        - Cache Backend: Redis (or Django's configured cache)
        - Cache Miss: Queries database and repopulates cache
        - Cache Unavailable: Falls back to direct database query

    Performance Characteristics:
        - Cache hit: ~10ms (Redis roundtrip)
        - Cache miss: ~100-150ms (6 DISTINCT queries + cache set)
        - Cache unavailable: ~100ms (database queries only)

    HTTP Status Codes:
        - 200 OK: Filter options returned
        - 500 Internal Server Error: Database error (cache unavailable is not an error)

    Error Handling:
        - Database errors: Caught and raised as DatabaseQueryError → HTTP 500
        - Cache failures: Logged as warning but don't affect response (graceful degradation)
        - All errors logged for monitoring and debugging

    Data Characteristics:
        - All values are sorted alphabetically
        - No duplicate values in any list
        - Empty strings and NULL values are excluded
        - Values fetched directly from database using DISTINCT queries
        - Limited to current data (not historical)

    Usage in Frontend:
        These options are typically used to populate:
        1. Status filter dropdown
        2. Modality/source filter dropdown
        3. Equipment type multi-select
        4. Room/facility multi-select
        5. Equipment name multi-select
        6. Description multi-select (if shown)

    Query Optimization:
        Uses raw SQL DISTINCT queries for performance:
        - DISTINCT on indexed columns: <50ms (exam_status, exam_source)
        - DISTINCT on unindexed columns: <50-100ms (others)
        - LIMIT on descriptions: Prevents excessive response size
        Total time for all 6 queries: <500ms typical

    Cache Invalidation:
        - Manual invalidation needed when records significantly change
        - TTL expiry: 24 hours (time-based invalidation)
        - No automatic invalidation on INSERT/UPDATE/DELETE

    Example Requests:
        GET /api/v1/studies/filters/options

    Response Headers:
        Content-Type: application/json
        Cache-Control: public, max-age=300  (frontend can cache for 5 minutes)

    See Also:
        - Search endpoint: GET /api/v1/studies/search
        - Service layer: study.services.StudyService.get_filter_options()
        - Schema: study.schemas.FilterOptions
        - API Contract: ../docs/api/API_CONTRACT.md
    """
    try:
        return StudyService.get_filter_options()
    except DatabaseQueryError as e:
        # Log database errors and let Django Ninja handle as 500
        logger.error(f"Database error in get_filter_options: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error in get_filter_options: {str(e)}")
        raise
