"""
Pydantic schemas for Django Ninja API.
CRITICAL: These must match FastAPI response format EXACTLY.
Type safety through Pydantic validation.
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class StudyDetail(BaseModel):
    """Complete study record - used for detail endpoint.
    
    MUST match ../docs/api/API_CONTRACT.md specification exactly.
    """
    exam_id: str
    medical_record_no: Optional[str] = None
    application_order_no: Optional[str] = None
    patient_name: str
    patient_gender: Optional[str] = None
    patient_birth_date: Optional[str] = None
    patient_age: Optional[int] = None
    exam_status: str
    exam_source: str
    exam_item: str
    exam_description: Optional[str] = None
    exam_room: Optional[str] = None
    exam_equipment: Optional[str] = None
    equipment_type: str
    order_datetime: datetime
    check_in_datetime: Optional[datetime] = None
    report_certification_datetime: Optional[datetime] = None
    certified_physician: Optional[str] = None
    data_load_time: Optional[datetime] = None
    
    class Config:
        # Ensure datetime serialization is ISO format
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }


class StudyListItem(BaseModel):
    """Study record in search results.
    
    MUST match ../docs/api/API_CONTRACT.md search response format.
    Excludes some fields from detail endpoint.
    """
    exam_id: str
    medical_record_no: Optional[str] = None
    application_order_no: Optional[str] = None
    patient_name: str
    patient_gender: Optional[str] = None
    patient_age: Optional[int] = None
    exam_status: str
    exam_source: str
    exam_item: str
    exam_description: Optional[str] = None
    order_datetime: datetime
    check_in_datetime: Optional[datetime] = None
    report_certification_datetime: Optional[datetime] = None
    certified_physician: Optional[str] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }


class FilterOptions(BaseModel):
    """Available filter options for searches.

    MUST match ../docs/api/API_CONTRACT.md filters specification.
    All values from database, sorted, no duplicates.
    """
    exam_statuses: List[str]
    exam_sources: List[str]
    equipment_types: List[str]
    exam_rooms: List[str]  # Examination room options
    exam_equipments: List[str]  # Specific equipment options
    exam_descriptions: List[str]  # Exam description options (limited to common values)


class StudySearchResponse(BaseModel):
    """Search response with pagination using Django Ninja paginate decorator.
    
    CRITICAL: Structure must match FastAPI exactly:
    - "items" array of studies (Django Ninja standard)
    - "count" total count (Django Ninja standard)
    - "filters" with available options (custom extension)
    
    Note: When using @paginate(StudyPagination), the output will be
    automatically serialized to this format.
    """
    items: List[StudyListItem]
    count: int
    filters: FilterOptions
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }


class StudySearchRequest(BaseModel):
    """Search request parameters.
    
    Maps to query parameters in GET /api/v1/studies/search
    """
    q: Optional[str] = Field(None, max_length=200, description='Text search query')
    exam_status: Optional[str] = Field(None, description='Filter by exam status')
    exam_source: Optional[str] = Field(None, description='Filter by exam source')
    exam_item: Optional[str] = Field(None, description='Filter by exam item')
    start_date: Optional[str] = Field(None, description='Start date ISO 8601')
    end_date: Optional[str] = Field(None, description='End date ISO 8601')
    page: int = Field(1, ge=1, description='Page number')
    page_size: int = Field(20, ge=1, le=100, description='Items per page')
    sort: str = Field('order_datetime_desc', description='Sort order')


# ============================================================================
# Authentication Schemas
# ============================================================================

class LoginRequest(BaseModel):
    """Login request schema.

    Used for POST /api/v1/auth/login endpoint.
    """
    username: str = Field(..., min_length=1, max_length=150, description='Username')
    password: str = Field(..., min_length=1, description='Password')


class UserInfo(BaseModel):
    """User information schema.

    Returned after successful authentication or when fetching current user.
    """
    id: int
    username: str
    email: str
    first_name: str = ""
    last_name: str = ""


class AuthResponse(BaseModel):
    """Authentication response with user information.

    Used for login endpoint responses.
    """
    status: str  # "success" | "error"
    message: str
    user: Optional[UserInfo] = None


class UserResponse(BaseModel):
    """Current user information response.

    Used for /auth/me endpoint.
    """
    status: str  # "success" | "error"
    user: Optional[UserInfo] = None
    message: Optional[str] = None


class StatusResponse(BaseModel):
    """Simple status response.

    Used for logout and other status-only endpoints.
    """
    status: str  # "success" | "error"
    message: str
