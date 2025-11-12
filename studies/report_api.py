"""
Report API Endpoints for import, search, and retrieval.

PRAGMATIC DESIGN: Simple endpoints matching actual use cases.
"""

from typing import List, Optional
from ninja import Router, Query
from django.utils import timezone
from .models import Report, ReportVersion
from .report_service import ReportService
from pydantic import BaseModel
import logging

logger = logging.getLogger(__name__)

# Create router
report_router = Router()


# Pydantic schemas for request/response
class ReportImportRequest(BaseModel):
    """Request schema for importing a report."""

    uid: str
    title: str
    content: str
    report_type: str  # PDF, HTML, TXT, etc.
    source_url: str
    report_id: Optional[str] = None
    chr_no: Optional[str] = None
    mod: Optional[str] = None
    report_date: Optional[str] = None
    verified_at: Optional[str] = None


class ReportResponse(BaseModel):
    """Response schema for report retrieval."""

    uid: str
    report_id: Optional[str] = None  # Can be NULL in database
    title: str
    report_type: str
    version_number: int
    is_latest: bool
    created_at: str
    verified_at: Optional[str] = None
    content_preview: str  # First 500 chars


class ReportDetailResponse(ReportResponse):
    """Extended response with full content."""

    content_raw: str
    source_url: str


class ReportVersionResponse(BaseModel):
    """Response schema for report versions."""

    version_number: int
    changed_at: str
    verified_at: Optional[str]
    change_type: str
    change_description: str


class ReportFilterOptionsResponse(BaseModel):
    """Response schema for filter options."""

    report_types: List[str]


class ImportResponse(BaseModel):
    """Response for import operation."""

    uid: str
    report_id: str
    is_new: bool
    action: str
    version_number: int


class PaginatedReportResponse(BaseModel):
    """Paginated response for report search results."""

    items: List[ReportResponse]
    total: int
    limit: int
    offset: int
    page: int
    pages: int


class ReportPagination:
    """
    Pagination handler for report search results.
    
    Supports limit/offset pagination with metadata.
    Works with Django QuerySets for efficient database queries.
    """

    def __init__(self, queryset, limit: int = 50, offset: int = 0):
        """
        Initialize pagination.
        
        Args:
            queryset: Django QuerySet to paginate
            limit: Number of items per page (max 500, default 50)
            offset: Number of items to skip (default 0)
        """
        self.queryset = queryset
        self.limit = min(limit, 500) if limit > 0 else 50
        self.offset = max(offset, 0)
        
        # Get total count (do this once)
        self.total = self.queryset.count()
        
    def get_page_number(self) -> int:
        """Calculate current page number (1-indexed)."""
        if self.limit <= 0:
            return 1
        return (self.offset // self.limit) + 1
    
    def get_total_pages(self) -> int:
        """Calculate total number of pages."""
        if self.limit <= 0:
            return 1
        return (self.total + self.limit - 1) // self.limit
    
    def get_items(self):
        """Get paginated items from queryset."""
        start = self.offset
        end = self.offset + self.limit
        return self.queryset[start:end]
    
    def get_response_data(self, items: List) -> dict:
        """Get pagination response data."""
        return {
            'items': items,
            'total': self.total,
            'limit': self.limit,
            'offset': self.offset,
            'page': self.get_page_number(),
            'pages': self.get_total_pages(),
        }


# Endpoints
@report_router.post('/import', response=ImportResponse)
def import_report(request, payload: ReportImportRequest):
    """
    Import or update a report.

    The endpoint intelligently handles:
    - New reports: Creates new record
    - Same content: Deduplicates (keeps latest by verified_at)
    - Different content: Creates new version

    This is the main entry point for report ingestion from scrapers.
    """
    try:
        report, is_new, action = ReportService.import_or_update_report(
            uid=payload.uid,
            title=payload.title,
            content=payload.content,
            report_type=payload.report_type,
            source_url=payload.source_url,
            report_id=payload.report_id,
            chr_no=payload.chr_no,
            mod=payload.mod,
            report_date=payload.report_date,
            verified_at=None,  # Will default to now
        )

        return ImportResponse(
            uid=report.uid,
            report_id=report.report_id,
            is_new=is_new,
            action=action,
            version_number=report.version_number,
        )

    except Exception as e:
        logger.error(f'Report import failed: {str(e)}')
        raise


@report_router.get('/search', response=List[ReportResponse])
def search_reports(
    request,
    q: str = Query('', description='Search query'),
    limit: int = Query(50, description='Result limit (legacy, use offset/limit for pagination)'),
    report_type: Optional[str] = Query(None, description='Filter by report type'),
    report_status: Optional[str] = Query(None, description='Filter by report status'),
    report_format: Optional[str] = Query(None, description='Filter by report format (comma-separated)'),
    date_from: Optional[str] = Query(None, description='Filter by date from (ISO format)'),
    date_to: Optional[str] = Query(None, description='Filter by date to (ISO format)'),
    sort: str = Query('verified_at_desc', description='Sort order: verified_at_desc, created_at_desc, title_asc'),
):
    """
    Advanced search for reports with multiple filters.

    Supports:
    - Full-text search across 6 fields (report_id, uid, title, chr_no, mod, content_processed)
    - Single-select filters (report_type, report_status)
    - Multi-select filters (report_format as comma-separated values)
    - Date range filtering (date_from, date_to)
    - Flexible sorting options

    Example: /api/v1/reports/search?q=covid&report_type=PDF&limit=20&sort=verified_at_desc
    """
    try:
        if limit > 500:
            limit = 500
        if limit < 1:
            limit = 1

        # Parse report_format if provided as comma-separated string
        report_formats = []
        if report_format:
            report_formats = [f.strip() for f in report_format.split(',') if f.strip()]

        # Get filtered queryset
        queryset = ReportService.get_reports_queryset(
            q=q if q else None,
            report_type=report_type,
            report_status=report_status,
            report_format=report_formats if report_formats else None,
            date_from=date_from,
            date_to=date_to,
            sort=sort,
        )

        # Apply limit
        results = queryset[:limit]

        return [
            ReportResponse(
                uid=r.uid,
                report_id=r.report_id,
                title=r.title,
                report_type=r.report_type,
                version_number=r.version_number,
                is_latest=r.is_latest,
                created_at=r.created_at.isoformat(),
                verified_at=r.verified_at.isoformat() if r.verified_at else None,
                content_preview=ReportService.safe_truncate(r.content_raw, 500),
            )
            for r in results
        ]

    except Exception as e:
        logger.error(f'Search failed: {str(e)}')
        raise


@report_router.get('/search/paginated', response=PaginatedReportResponse)
def search_reports_paginated(
    request,
    q: str = Query('', description='Search query'),
    offset: int = Query(0, description='Number of items to skip (default 0)'),
    limit: int = Query(50, description='Number of items per page (max 500)'),
    report_type: Optional[str] = Query(None, description='Filter by report type'),
    report_status: Optional[str] = Query(None, description='Filter by report status'),
    report_format: Optional[str] = Query(None, description='Filter by report format (comma-separated)'),
    date_from: Optional[str] = Query(None, description='Filter by date from (ISO format)'),
    date_to: Optional[str] = Query(None, description='Filter by date to (ISO format)'),
    sort: str = Query('verified_at_desc', description='Sort order: verified_at_desc, created_at_desc, title_asc'),
):
    """
    Advanced search for reports with proper pagination support.

    Uses offset/limit pagination for efficient handling of large result sets.

    Supports:
    - Full-text search across 6 fields
    - Single-select and multi-select filters
    - Date range filtering
    - Flexible sorting
    - Pagination metadata (page number, total pages, etc.)

    Example: /api/v1/reports/search/paginated?q=covid&offset=0&limit=20
    """
    try:
        # Validate pagination parameters
        offset = max(offset, 0)
        limit = max(min(limit, 500), 1)

        # Parse report_format if provided
        report_formats = []
        if report_format:
            report_formats = [f.strip() for f in report_format.split(',') if f.strip()]

        # Get filtered queryset
        queryset = ReportService.get_reports_queryset(
            q=q if q else None,
            report_type=report_type,
            report_status=report_status,
            report_format=report_formats if report_formats else None,
            date_from=date_from,
            date_to=date_to,
            sort=sort,
        )

        # Apply pagination
        paginator = ReportPagination(queryset, limit=limit, offset=offset)
        items = paginator.get_items()

        # Convert to response objects
        report_items = [
            ReportResponse(
                uid=r.uid,
                report_id=r.report_id,
                title=r.title,
                report_type=r.report_type,
                version_number=r.version_number,
                is_latest=r.is_latest,
                created_at=r.created_at.isoformat(),
                verified_at=r.verified_at.isoformat() if r.verified_at else None,
                content_preview=ReportService.safe_truncate(r.content_raw, 500),
            )
            for r in items
        ]

        # Get pagination metadata
        page_data = paginator.get_response_data(report_items)

        return PaginatedReportResponse(**page_data)

    except Exception as e:
        logger.error(f'Paginated search failed: {str(e)}')
        raise


@report_router.get('/latest', response=List[ReportResponse])
def get_latest_reports(
    request,
    limit: int = Query(20, description='Result limit'),
):
    """
    Get latest versions of reports.

    Sorted by verification date (most recent first).
    Useful for feeds and dashboards.
    """
    try:
        if limit > 500:
            limit = 500

        results = ReportService.get_latest_reports(limit)

        return [
            ReportResponse(
                uid=r.uid,
                report_id=r.report_id,
                title=r.title,
                report_type=r.report_type,
                version_number=r.version_number,
                is_latest=r.is_latest,
                created_at=r.created_at.isoformat(),
                verified_at=r.verified_at.isoformat() if r.verified_at else None,
                content_preview=ReportService.safe_truncate(r.content_raw, 500),
            )
            for r in results
        ]

    except Exception as e:
        logger.error(f'Fetch failed: {str(e)}')
        raise


@report_router.get('/{report_id}', response=ReportDetailResponse)
def get_report_detail(request, report_id: str):
    """
    Get full report details including complete content.

    Retrieves the latest version of the report.
    """
    try:
        report = Report.objects.get(pk=report_id, is_latest=True)

        return ReportDetailResponse(
            uid=report.uid,
            report_id=report.report_id,
            title=report.title,
            report_type=report.report_type,
            version_number=report.version_number,
            is_latest=report.is_latest,
            created_at=report.created_at.isoformat(),
            verified_at=report.verified_at.isoformat() if report.verified_at else None,
            content_preview=report.content_raw[:500],
            content_raw=report.content_raw,
            source_url=report.source_url,
        )

    except Report.DoesNotExist:
        raise Exception(f'Report not found: {report_id}')
    except Exception as e:
        logger.error(f'Fetch detail failed: {str(e)}')
        raise


@report_router.get('/{report_id}/versions', response=List[ReportVersionResponse])
def get_report_versions(request, report_id: str):
    """
    Get all versions of a report with change history.

    Shows the complete audit trail of changes to the report.
    Useful for tracking updates and understanding evolution.
    """
    try:
        versions = ReportService.get_report_history(report_id)

        return [
            ReportVersionResponse(
                version_number=v.version_number,
                changed_at=v.changed_at.isoformat(),
                verified_at=v.verified_at.isoformat() if v.verified_at else None,
                change_type=v.change_type,
                change_description=v.change_description,
            )
            for v in versions
        ]

    except Exception as e:
        logger.error(f'Versions fetch failed: {str(e)}')
        raise


@report_router.get('/options/filters', response=ReportFilterOptionsResponse)
def get_filter_options(request):
    """
    Get available filter options for report search.

    Returns distinct report types from the database with Redis caching.
    Used by frontend to populate filter dropdowns.

    Example: /api/v1/reports/options/filters
    """
    try:
        # Call service method which handles caching
        filter_options = ReportService.get_filter_options()

        return ReportFilterOptionsResponse(
            report_types=filter_options.get('report_types', [])
        )

    except Exception as e:
        logger.error(f'Fetch filter options failed: {str(e)}')
        raise
