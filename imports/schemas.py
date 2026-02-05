"""
Request/Response schemas for import API endpoints.

Uses Ninja Schema (Pydantic-based) for type validation and serialization.
"""

from datetime import datetime
from typing import Any

from ninja import Schema

# ============ Column Mapping ============


class ColumnMappingItem(Schema):
    """Single column mapping configuration."""

    source_column: str  # CSV/Excel column header
    target_field: str  # Model field name
    transform: str | None = None  # Optional: 'date', 'number', 'trim'


# ============ Upload Response ============


class UploadTaskData(Schema):
    """Task data returned after file upload."""

    task_id: str
    filename: str
    status: str
    progress: int
    message: str


class UploadResponse(Schema):
    """Response for file upload endpoint."""

    code: int = 200
    message: str = "Success"
    data: UploadTaskData


# ============ Preview Request/Response ============


class PreviewRequest(Schema):
    """Request for file preview."""

    task_id: str
    sheet_name: str | None = None  # For Excel files


class ColumnInfo(Schema):
    """Information about a detected column."""

    name: str
    detected_type: str  # 'string', 'number', 'date', 'boolean'
    sample_values: list[str]
    suggested_field: str | None = None


class PreviewData(Schema):
    """Preview data with headers and sample rows."""

    columns: list[ColumnInfo]
    preview_rows: list[dict[str, Any]]
    total_rows: int
    sheet_names: list[str] | None = None  # For Excel files
    target_fields: dict[str, list[str]]  # Available fields per target type


class PreviewResponse(Schema):
    """Response for preview endpoint."""

    code: int = 200
    message: str = "Success"
    data: PreviewData


# ============ Execute Request/Response ============


class ExecuteRequest(Schema):
    """Request for executing import."""

    task_id: str
    target_type: str  # 'report' or 'study'
    column_mapping: list[ColumnMappingItem]


class ExecuteData(Schema):
    """Data returned after starting import execution."""

    task_id: str
    status: str
    progress: int
    total_rows: int
    message: str


class ExecuteResponse(Schema):
    """Response for execute endpoint."""

    code: int = 200
    message: str = "Success"
    data: ExecuteData


# ============ Task Status Response ============


class ErrorDetail(Schema):
    """Detail about a single import error."""

    row_number: int
    field: str | None = None
    error: str
    value: str | None = None


class TaskStatusData(Schema):
    """Detailed task status data."""

    task_id: str
    filename: str
    target_type: str
    status: str
    progress: int
    total_rows: int
    imported_rows: int
    error_rows: int
    error_message: str | None = None
    error_details: list[ErrorDetail] | None = None
    created_at: datetime
    updated_at: datetime


class TaskStatusResponse(Schema):
    """Response for task status endpoint."""

    code: int = 200
    message: str = "Success"
    data: TaskStatusData


# ============ Task List Response ============


class TaskListItem(Schema):
    """Summary item for task list."""

    task_id: str
    filename: str
    target_type: str
    status: str
    progress: int
    imported_rows: int
    error_rows: int
    created_at: datetime


class TaskListData(Schema):
    """Task list with pagination."""

    tasks: list[TaskListItem]
    total: int
    page: int
    page_size: int


class TaskListResponse(Schema):
    """Response for task list endpoint."""

    code: int = 200
    message: str = "Success"
    data: TaskListData


# ============ Error Response ============


class ErrorResponse(Schema):
    """Standard error response."""

    code: int
    message: str
    detail: str | None = None
