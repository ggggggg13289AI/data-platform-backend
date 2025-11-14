"""
Report API Endpoints for import, search, and retrieval.

PRAGMATIC DESIGN: Simple endpoints matching actual use cases.
"""

from typing import List, Optional
from ninja import Router, Query
from ninja.pagination import paginate
from django.utils import timezone
from .models import Report, ReportVersion
from .report_service import ReportService
from .pagination import ReportPagination
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


def _get_report_search_queryset(
    q: str,
    report_type: Optional[str],
    report_status: Optional[str],
    report_format: Optional[str],
    date_from: Optional[str],
    date_to: Optional[str],
    sort: str,
):
    """
    Internal helper to get filtered report queryset.
    Shared by both /search and /search/paginated endpoints.
    """
    # Parse report_format if provided as comma-separated string
    report_formats = []
    if report_format:
        report_formats = [f.strip() for f in report_format.split(',') if f.strip()]

    # Get filtered queryset
    return ReportService.get_reports_queryset(
        q=q if q else None,
        report_type=report_type,
        report_status=report_status,
        report_format=report_formats if report_formats else None,
        date_from=date_from,
        date_to=date_to,
        sort=sort,
    )


@report_router.get('/search', response=List[ReportResponse])
def search_reports(
    request,
    q: str = Query('', description='Search query'),
    limit: int = Query(50, description='Result limit (legacy endpoint - use /search/paginated instead)'),
    offset: int = Query(0, description='Result offset (legacy endpoint)'),
    report_type: Optional[str] = Query(None, description='Filter by report type'),
    report_status: Optional[str] = Query(None, description='Filter by report status'),
    report_format: Optional[str] = Query(None, description='Filter by report format (comma-separated)'),
    date_from: Optional[str] = Query(None, description='Filter by date from (ISO format)'),
    date_to: Optional[str] = Query(None, description='Filter by date to (ISO format)'),
    sort: str = Query('verified_at_desc', description='Sort order: verified_at_desc, created_at_desc, title_asc'),
):
    """
    Advanced search for reports with multiple filters.

    ⚠️ DEPRECATED: This endpoint uses legacy limit/offset pagination.
    Please use /search/paginated with page/page_size model instead.

    Legacy support maintained for frontend compatibility.
    Uses shared queryset logic with /search/paginated endpoint.

    Migration guide: See CLIENT_MIGRATION_GUIDE.md for details.
    Legacy support will be removed in v2.0.0.

    Supports:
    - Full-text search across 6 fields (report_id, uid, title, chr_no, mod, content_processed)
    - Single-select filters (report_type, report_status)
    - Multi-select filters (report_format as comma-separated values)
    - Date range filtering (date_from, date_to)
    - Flexible sorting options

    Example: /api/v1/reports/search?q=covid&report_type=PDF&limit=20&offset=0&sort=verified_at_desc
    """
    # Log deprecation warning
    logger.warning(
        'DEPRECATED: /api/v1/reports/search endpoint is legacy. '
        'Use /api/v1/reports/search/paginated with page/page_size model instead. '
        'Legacy endpoint will be removed in v2.0.0. '
        'See CLIENT_MIGRATION_GUIDE.md for migration details.'
    )

    # Validate legacy parameters
    limit = max(min(limit, 500), 1)
    offset = max(offset, 0)

    # Get filtered queryset (shared logic with /search/paginated)
    queryset = _get_report_search_queryset(
        q, report_type, report_status, report_format,
        date_from, date_to, sort
    )

    # Apply legacy limit/offset pagination
    results = queryset[offset:offset + limit]

    # Convert to response objects (legacy format - just List[ReportResponse])
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


@report_router.get('/search/paginated', response=List[ReportResponse])
@paginate(ReportPagination)
def search_reports_paginated(
    request,
    q: str = Query('', description='Search query'),
    report_type: Optional[str] = Query(None, description='Filter by report type'),
    report_status: Optional[str] = Query(None, description='Filter by report status'),
    report_format: Optional[str] = Query(None, description='Filter by report format (comma-separated)'),
    date_from: Optional[str] = Query(None, description='Filter by date from (ISO format)'),
    date_to: Optional[str] = Query(None, description='Filter by date to (ISO format)'),
    sort: str = Query('verified_at_desc', description='Sort order: verified_at_desc, created_at_desc, title_asc'),
):
    """
    Advanced search for reports with proper pagination support.

    Uses page/page_size pagination for consistent API experience.
    Compatible with Studies and Projects API pagination model.

    Supports:
    - Full-text search across 6 fields
    - Single-select and multi-select filters
    - Date range filtering
    - Flexible sorting
    - Pagination metadata (page number, total pages, etc.)

    Example: /api/v1/reports/search/paginated?q=covid&page=1&page_size=20
    """
    # Get filtered queryset (shared logic with /search) - @paginate will handle pagination
    return _get_report_search_queryset(
        q, report_type, report_status, report_format,
        date_from, date_to, sort
    )


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


@report_router.get('/{uid}', response=ReportDetailResponse)
def get_report_detail(request, uid: str):
    """
    Get full report details including complete content.

    Retrieves the latest version of the report.
    """
    try:
        report = Report.objects.get(pk=uid, is_latest=True)

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
