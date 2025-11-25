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

