from __future__ import annotations

from typing import Any, Literal

from ninja import Schema


class ReportImportRequest(Schema):
    """Request schema for importing a report."""

    uid: str
    title: str
    content: str
    report_type: str  # PDF, HTML, TXT, etc.
    source_url: str
    report_id: str | None = None
    chr_no: str | None = None
    mod: str | None = None
    report_date: str | None = None
    verified_at: str | None = None


class StudyInfoResponse(Schema):
    """Study information embedded in Report response."""

    patient_name: str | None = None
    patient_age: int | None = None
    patient_gender: str | None = None
    exam_source: str | None = None
    exam_item: str | None = None
    exam_status: str | None = None
    equipment_type: str | None = None
    order_datetime: str | None = None
    check_in_datetime: str | None = None
    report_certification_datetime: str | None = None


class ReportResponse(Schema):
    """Response schema for report retrieval."""

    uid: str
    report_id: str | None = None  # Can be NULL in database
    title: str
    report_type: str
    version_number: int
    is_latest: bool
    created_at: str
    verified_at: str | None = None
    content_preview: str  # First 500 chars
    content_raw: str | None = None  # Optional full content for unified views
    study: StudyInfoResponse | None = None  # Study info for advanced search

    class Config:
        orm_mode = True


class ReportDetailResponse(ReportResponse):
    """Extended response with full content."""

    content_raw: str
    source_url: str


class ReportVersionResponse(Schema):
    """Response schema for report versions."""

    version_number: int
    changed_at: str
    verified_at: str | None
    change_type: str
    change_description: str


class AIAnnotationResponse(Schema):
    """Response schema for AI annotations."""

    id: str
    report_id: str
    annotation_type: str
    content: str
    created_at: str
    updated_at: str | None = None
    created_by: str | None = None
    metadata: dict | None = None


class DateRange(Schema):
    """Reusable date range metadata."""

    start: str | None = None
    end: str | None = None


class ReportFilterOptionsResponse(Schema):
    """Response schema for filter options."""

    report_types: list[str]
    report_statuses: list[str]
    mods: list[str]
    verified_date_range: DateRange


class ImportResponse(Schema):
    """Response for import operation."""

    uid: str
    report_id: str
    is_new: bool
    action: str
    version_number: int


class AdvancedSearchFilters(Schema):
    """Additional filters applied alongside the DSL."""

    report_type: str | None = None
    report_status: str | None = None
    report_format: list[str] | None = None
    physician: str | None = None
    report_id: str | None = None
    exam_id: str | None = None
    date_from: str | None = None
    date_to: str | None = None


class BasicAdvancedQuery(Schema):
    """Payload for the simple advanced-search mode."""

    text: str


class AdvancedSearchNode(Schema):
    """Recursive node definition for the JSON DSL."""

    operator: str | None = None
    field: str | None = None
    value: Any = None
    conditions: list['AdvancedSearchNode'] | None = None


class AdvancedSearchRequest(Schema):
    """Request payload for POST /reports/search/advanced."""

    mode: Literal['basic', 'multi'] = 'basic'
    basic: BasicAdvancedQuery | None = None
    tree: AdvancedSearchNode | None = None
    filters: AdvancedSearchFilters | None = None
    sort: str | None = None
    page: int = 1
    page_size: int = 20


class AdvancedSearchResponse(Schema):
    """Response payload for POST /reports/search/advanced."""

    items: list[ReportResponse]
    total: int
    page: int
    page_size: int
    pages: int
    filters: ReportFilterOptionsResponse

