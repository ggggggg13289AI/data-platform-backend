from datetime import datetime

from ninja import Field, Schema


class StudyDetail(Schema):
    """Complete study record - used for detail endpoint.

    MUST match ../docs/api/API_CONTRACT.md specification exactly.
    """
    exam_id: str
    medical_record_no: str | None = None
    application_order_no: str | None = None
    patient_name: str
    patient_gender: str | None = None
    patient_birth_date: str | None = None
    patient_age: int | None = None
    exam_status: str
    exam_source: str
    exam_item: str
    exam_description: str | None = None
    exam_room: str | None = None
    exam_equipment: str | None = None
    equipment_type: str
    order_datetime: datetime
    check_in_datetime: datetime | None = None
    report_certification_datetime: datetime | None = None
    certified_physician: str | None = None
    data_load_time: datetime | None = None

    class Config:
        from_attributes = True
        # Ensure datetime serialization is ISO format
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }


class StudyListItem(Schema):
    """Study record in search results.

    MUST match ../docs/api/API_CONTRACT.md search response format.
    Excludes some fields from detail endpoint.
    """
    exam_id: str
    medical_record_no: str | None = None
    application_order_no: str | None = None
    patient_name: str
    patient_gender: str | None = None
    patient_age: int | None = None
    exam_status: str
    exam_source: str
    exam_item: str
    exam_description: str | None = None
    order_datetime: datetime
    check_in_datetime: datetime | None = None
    report_certification_datetime: datetime | None = None
    certified_physician: str | None = None

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }


class FilterOptions(Schema):
    """Available filter options for searches.

    MUST match ../docs/api/API_CONTRACT.md filters specification.
    All values from database, sorted, no duplicates.
    """
    exam_statuses: list[str]
    exam_sources: list[str]
    equipment_types: list[str]
    exam_rooms: list[str]  # Examination room options
    exam_equipments: list[str]  # Specific equipment options
    exam_descriptions: list[str]  # Exam description options (limited to common values)


class StudySearchResponse(Schema):
    """Search response with pagination using Django Ninja paginate decorator.

    CRITICAL: Structure must match FastAPI exactly:
    - "items" array of studies (Django Ninja standard)
    - "count" total count (Django Ninja standard)
    - "filters" with available options (custom extension)

    Note: When using @paginate(StudyPagination), the output will be
    automatically serialized to this format.
    """
    items: list[StudyListItem]
    count: int
    filters: FilterOptions

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }


class StudySearchRequest(Schema):
    """Search request parameters.

    Maps to query parameters in GET /api/v1/studies/search
    """
    q: str | None = Field(None, max_length=200, description='Text search query')
    exam_status: str | None = Field(None, description='Filter by exam status')
    exam_source: str | None = Field(None, description='Filter by exam source')
    exam_item: str | None = Field(None, description='Filter by exam item')
    start_date: str | None = Field(None, description='Start date ISO 8601')
    end_date: str | None = Field(None, description='End date ISO 8601')
    page: int = Field(1, ge=1, description='Page number')
    page_size: int = Field(20, ge=1, le=100, description='Items per page')
    sort: str = Field('order_datetime_desc', description='Sort order')

