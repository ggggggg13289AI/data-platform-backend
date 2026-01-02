"""
Pydantic schemas for Study API responses.

This module defines the request and response schemas for all Study API endpoints.
All schemas use Pydantic with Django Ninja integration for automatic validation
and serialization.

Serialization Strategy:
    - All datetime fields are serialized to ISO 8601 format (YYYY-MM-DDTHH:MM:SS)
    - All optional fields can be None
    - Request schemas validate input data types and ranges
    - Response schemas ensure consistent API contract across all endpoints

CRITICAL: Response format MUST match ../docs/api/API_CONTRACT.md exactly.
"""

from datetime import datetime

from ninja import Field, Schema


class StudyDetail(Schema):
    """
    Complete study record with all available information.

    Used for the detail endpoint GET /api/v1/studies/{exam_id}.
    Contains all fields from the Study model in their full form.

    This schema represents a single comprehensive medical examination record
    with complete patient and examination information.

    Fields:
        exam_id (str): Unique examination identifier
        medical_record_no (str | None): Patient medical record number
        application_order_no (str | None): Application order number
        patient_name (str): Patient full name
        patient_gender (str | None): Patient gender (M/F/U)
        patient_birth_date (str | None): Patient birth date (YYYY-MM-DD)
        patient_age (int | None): Patient age in years
        exam_status (str): Current examination status
        exam_source (str): Examination modality (CT, MRI, X-ray, etc.)
        exam_item (str): Specific procedure type
        exam_description (str | None): Detailed exam description
        exam_room (str | None): Hospital room/facility
        exam_equipment (str | None): Equipment name
        equipment_type (str): Equipment type classification
        order_datetime (datetime): When exam was ordered (ISO format)
        check_in_datetime (datetime | None): When patient checked in
        report_certification_datetime (datetime | None): When report was certified
        certified_physician (str | None): Physician who certified report
        data_load_time (datetime | None): When record was loaded

    See Also:
        - API Contract: ../docs/api/API_CONTRACT.md
        - Model: study.models.Study
        - Endpoint: study.api.get_study_detail()

    Examples:
        >>> # API Response for GET /api/v1/studies/EXAM_001
        >>> response = {
        ...     "exam_id": "EXAM_001",
        ...     "patient_name": "张三",
        ...     "exam_status": "completed",
        ...     "order_datetime": "2024-01-15T14:30:00",
        ...     ...
        ... }

    CRITICAL: Response format MUST match API contract exactly.
    """

    # Required fields
    exam_id: str = Field(..., description="Unique examination identifier")
    patient_name: str = Field(..., description="Patient full name")
    exam_status: str = Field(..., description="Current examination status")
    exam_source: str = Field(..., description="Examination modality (CT, MRI, X-ray)")
    exam_item: str = Field(..., description="Specific procedure type")
    equipment_type: str = Field(..., description="Equipment type classification")
    order_datetime: datetime = Field(..., description="When exam was ordered")

    # Optional fields (patient identifiers)
    medical_record_no: str | None = Field(None, description="Patient medical record number")
    application_order_no: str | None = Field(None, description="Application order number")

    # Optional fields (patient demographics)
    patient_gender: str | None = Field(None, description="Patient gender (M/F/U)")
    patient_birth_date: str | None = Field(None, description="Patient birth date (YYYY-MM-DD)")
    patient_age: int | None = Field(None, description="Patient age in years")

    # Optional fields (exam details)
    exam_description: str | None = Field(None, description="Detailed exam description")
    exam_room: str | None = Field(None, description="Hospital room/facility")
    exam_equipment: str | None = Field(None, description="Equipment name/model")

    # Optional fields (temporal)
    check_in_datetime: datetime | None = Field(None, description="When patient checked in")
    report_certification_datetime: datetime | None = Field(
        None, description="When report was certified"
    )

    # Optional fields (authorization)
    certified_physician: str | None = Field(None, description="Physician who certified report")
    data_load_time: datetime | None = Field(None, description="When record was loaded")

    class Config:
        # Allow creation from Django model instances using .from_attributes()
        from_attributes = True

        # Custom JSON encoder for datetime fields - ensures ISO format
        # All datetime objects are serialized to ISO 8601 format without timezone
        json_encoders = {datetime: lambda v: v.isoformat() if v else None}


class StudyListItem(Schema):
    """
    Study record in search results (subset of StudyDetail).

    Used for paginated search results in GET /api/v1/studies/search.
    Contains a curated subset of fields optimized for list display.

    This schema is more compact than StudyDetail, omitting fields that are
    typically not shown in search result listings (exam_room, exam_equipment, etc.)
    to reduce response payload size.

    Fields:
        exam_id (str): Unique examination identifier
        medical_record_no (str | None): Patient medical record number
        application_order_no (str | None): Application order number
        patient_name (str): Patient full name
        patient_gender (str | None): Patient gender
        patient_age (int | None): Patient age
        exam_status (str): Examination status
        exam_source (str): Examination modality
        exam_item (str): Procedure type
        exam_description (str | None): Brief exam description
        order_datetime (datetime): Order date/time (ISO format)
        check_in_datetime (datetime | None): Check-in date/time
        report_certification_datetime (datetime | None): Certification date/time
        certified_physician (str | None): Physician name

    Differences from StudyDetail:
        - Excludes: exam_room, exam_equipment, equipment_type, data_load_time
        - Optimized for fast serialization and smaller response payload
        - Includes all fields needed for list display and filtering

    See Also:
        - StudyDetail: Full record details
        - API Contract: ../docs/api/API_CONTRACT.md
        - Endpoint: study.api.search_studies()

    Examples:
        >>> # Item in search results array
        >>> item = {
        ...     "exam_id": "EXAM_001",
        ...     "patient_name": "张三",
        ...     "exam_status": "completed",
        ...     "order_datetime": "2024-01-15T14:30:00",
        ...     ...
        ... }

    CRITICAL: Response format MUST match API contract exactly.
    """

    # Required fields
    exam_id: str = Field(..., description="Unique examination identifier")
    patient_name: str = Field(..., description="Patient full name")
    exam_status: str = Field(..., description="Examination status")
    exam_source: str = Field(..., description="Examination modality (CT, MRI, X-ray)")
    exam_item: str = Field(..., description="Specific procedure type")
    order_datetime: datetime = Field(..., description="When exam was ordered")

    # Optional fields (identifiers)
    medical_record_no: str | None = Field(None, description="Patient medical record number")
    application_order_no: str | None = Field(None, description="Application order number")

    # Optional fields (patient info - subset for list view)
    patient_gender: str | None = Field(None, description="Patient gender (M/F/U)")
    patient_age: int | None = Field(None, description="Patient age in years")

    # Optional fields (exam info - subset for list view)
    exam_description: str | None = Field(None, description="Brief exam description")

    # Optional temporal fields
    check_in_datetime: datetime | None = Field(None, description="When patient checked in")
    report_certification_datetime: datetime | None = Field(
        None, description="When report was certified"
    )

    # Optional field (authorization)
    certified_physician: str | None = Field(None, description="Physician who certified report")

    class Config:
        # Custom JSON encoder for datetime fields
        json_encoders = {datetime: lambda v: v.isoformat() if v else None}


class FilterOptions(Schema):
    """
    Available filter options for search refinement.

    Contains all distinct values for each filterable field, used by the frontend
    to populate filter dropdown/selection menus in the search interface.

    Data Characteristics:
        - All values are sorted alphabetically
        - No duplicate values in any list
        - Empty strings and NULL values are excluded
        - Fetched directly from database using DISTINCT queries
        - Cached for 24 hours to reduce database load

    Fields:
        exam_statuses (list[str]): All distinct examination statuses
            Examples: ['pending', 'completed', 'cancelled']

        exam_sources (list[str]): All distinct examination modalities
            Examples: ['CT', 'MRI', 'X-ray', 'Ultrasound']

        equipment_types (list[str]): All distinct equipment type classifications
            Examples: ['CT Scanner', 'MRI Scanner', 'X-ray Machine']

        exam_rooms (list[str]): All distinct examination rooms/facilities
            Examples: ['Room A', 'Room B', 'Operating Theater 1']

        exam_equipments (list[str]): All distinct equipment names/models
            Examples: ['GE LightSpeed 16', 'Siemens SOMATOM']

        exam_descriptions (list[str]): All distinct examination descriptions
            Limited to prevent excessive response size
            Examples: ['Routine chest imaging', 'Follow-up CT scan']

    Caching:
        - Cache key: 'study_filter_options'
        - Cache TTL: 24 hours (configured in ServiceConfig.FILTER_OPTIONS_CACHE_TTL)
        - Cache miss handling: Gracefully falls back to database query
        - Cache unavailable: Gracefully continues (logged as warning)

    See Also:
        - Service Layer: study.services.StudyService.get_filter_options()
        - Endpoint: study.api.get_filter_options()
        - API Contract: ../docs/api/API_CONTRACT.md

    Examples:
        >>> # GET /api/v1/studies/filters/options response
        >>> options = {
        ...     "exam_statuses": ["cancelled", "completed", "pending"],
        ...     "exam_sources": ["CT", "MRI", "X-ray"],
        ...     "equipment_types": ["CT Scanner", "MRI Scanner"],
        ...     "exam_rooms": ["Room A", "Room B"],
        ...     "exam_equipments": ["GE LightSpeed", "Siemens SOMATOM"],
        ...     "exam_descriptions": ["Routine imaging", "Follow-up"]
        ... }

    CRITICAL: Response format MUST match API contract exactly.
    """

    exam_statuses: list[str] = Field(
        ..., description="All distinct examination statuses (sorted alphabetically)"
    )
    exam_sources: list[str] = Field(
        ..., description="All distinct examination modalities/sources (sorted alphabetically)"
    )
    equipment_types: list[str] = Field(
        ..., description="All distinct equipment type classifications (sorted alphabetically)"
    )
    exam_rooms: list[str] = Field(
        ..., description="All distinct examination rooms/facilities (sorted alphabetically)"
    )
    exam_equipments: list[str] = Field(
        ..., description="All distinct equipment names/models (sorted alphabetically)"
    )
    exam_descriptions: list[str] = Field(
        ...,
        description="All distinct exam descriptions - limited to prevent large response (sorted alphabetically)",
    )


class StudySearchResponse(Schema):
    """
    Complete search response with pagination and available filters.

    This schema represents the complete response from the search endpoint,
    including paginated results and available filter options for UI rendering.

    The structure is designed to support both pagination and filter refinement
    in a single response, allowing frontend to display results and update
    filter options dynamically.

    Response Structure:
        items (list[StudyListItem]): Paginated array of study records
            - Each item is a StudyListItem with selected fields
            - Contains only the records for the current page
            - Sorted according to requested sort order

        count (int): Total count of matching records
            - Full count across ALL pages
            - Allows frontend to calculate total pages
            - Not affected by limit/offset pagination

        filters (FilterOptions): Available filter values
            - All distinct values for each filterable field
            - Used to populate filter UI dropdowns
            - Includes same filter values across all pages

    Pagination Handling:
        The @paginate(StudyPagination) decorator automatically constructs this
        response by:
        1. Extracting limit/offset from query parameters
        2. Counting total matching records (without LIMIT/OFFSET)
        3. Fetching paginated results with LIMIT/OFFSET
        4. Getting available filter options
        5. Serializing all into StudySearchResponse format

    See Also:
        - StudyListItem: Individual item schema
        - FilterOptions: Available filter values schema
        - Pagination: common.pagination.StudyPagination
        - API Contract: ../docs/api/API_CONTRACT.md

    Examples:
        >>> # Response for GET /api/v1/studies/search?q=chest&limit=10&offset=0
        >>> response = {
        ...     "items": [
        ...         {"exam_id": "EXAM_001", "patient_name": "张三", ...},
        ...         {"exam_id": "EXAM_002", "patient_name": "李四", ...},
        ...     ],
        ...     "count": 42,
        ...     "filters": {
        ...         "exam_statuses": ["completed", "pending"],
        ...         ...
        ...     }
        ... }

    CRITICAL: Response structure MUST match API contract exactly.
    This ensures compatibility with frontend and other backend services.
    """

    items: list[StudyListItem] = Field(
        ..., description="Paginated array of study records for current page"
    )
    count: int = Field(..., description="Total count of all matching records (across all pages)")
    filters: FilterOptions = Field(..., description="Available filter options for UI refinement")

    class Config:
        # Custom JSON encoder for datetime fields in nested StudyListItem objects
        json_encoders = {datetime: lambda v: v.isoformat() if v else None}


class StudySearchRequest(Schema):
    """
    Search request parameters schema.

    Maps to query parameters in GET /api/v1/studies/search endpoint.
    Combines text search, filtering, and pagination parameters.

    Query Parameters:
        q (str | None): Text search query
            - Searched across 9 fields: exam_id, medical_record_no, application_order_no,
              patient_name, exam_description, exam_item, exam_room, exam_equipment,
              certified_physician
            - Case-insensitive PostgreSQL ILIKE search
            - Max length: 200 characters
            - Example: "chest imaging"

        exam_status (str | None): Filter by examination status
            - Valid values: 'pending', 'completed', 'cancelled'
            - Exact match (case-sensitive)
            - Example: "completed"

        exam_source (str | None): Filter by examination modality
            - Valid values: 'CT', 'MRI', 'X-ray', 'Ultrasound', etc.
            - Exact match (case-sensitive)
            - Example: "CT"

        exam_item (str | None): Filter by specific procedure type
            - Examples: "Chest CT", "Spine MRI"
            - Exact match

        start_date (str | None): Filter start date (ISO 8601)
            - Format: YYYY-MM-DD
            - Compares against check_in_datetime (inclusive)
            - Example: "2024-01-01"

        end_date (str | None): Filter end date (ISO 8601)
            - Format: YYYY-MM-DD
            - Compares against check_in_datetime (inclusive)
            - Example: "2024-12-31"

        page (int): Page number (pagination)
            - Default: 1 (first page)
            - Minimum: 1
            - Used with page_size to calculate offset

        page_size (int): Items per page (pagination)
            - Default: 20 items
            - Range: 1-100 items
            - Prevents excessively large responses

        sort (str): Sort order
            - Default: 'order_datetime_desc' (newest first)
            - Valid values: 'order_datetime_asc', 'order_datetime_desc', 'patient_name_asc'
            - Example: "order_datetime_desc"

    Pagination Calculation:
        offset = (page - 1) * page_size
        Example: page=2, page_size=20 → offset=20 (skip first 20 records)

    See Also:
        - Response Schema: StudySearchResponse
        - Endpoint: study.api.search_studies()
        - Service: study.services.StudyService.get_studies_queryset()
        - API Contract: ../docs/api/API_CONTRACT.md

    Examples:
        >>> # Search for chest exams completed in 2024
        >>> request = {
        ...     "q": "chest",
        ...     "exam_status": "completed",
        ...     "start_date": "2024-01-01",
        ...     "end_date": "2024-12-31",
        ...     "page": 1,
        ...     "page_size": 20,
        ...     "sort": "order_datetime_desc"
        ... }

        >>> # Complete URL:
        >>> # GET /api/v1/studies/search?q=chest&exam_status=completed&start_date=2024-01-01&end_date=2024-12-31&page=1&page_size=20

    CRITICAL: All parameters are optional (None by default).
    At least one filter should be provided for meaningful results.
    """

    q: str | None = Field(
        None, max_length=200, description="Text search query across 9 fields (case-insensitive)"
    )
    exam_status: str | None = Field(
        None, description="Filter by exam status (pending/completed/cancelled)"
    )
    exam_source: str | None = Field(
        None, description="Filter by exam modality/source (CT/MRI/X-ray/etc.)"
    )
    exam_item: str | None = Field(None, description="Filter by specific procedure type")
    start_date: str | None = Field(
        None, description="Filter start date (ISO 8601 format: YYYY-MM-DD)"
    )
    end_date: str | None = Field(None, description="Filter end date (ISO 8601 format: YYYY-MM-DD)")

    page: int = Field(1, ge=1, description="Page number for pagination (starts at 1)")
    page_size: int = Field(20, ge=1, le=100, description="Items per page (max: 100)")
    sort: str = Field(
        "order_datetime_desc",
        description="Sort order (order_datetime_desc/order_datetime_asc/patient_name_asc)",
    )
