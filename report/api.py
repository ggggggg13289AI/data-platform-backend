"""
Report API Endpoints for import, search, and retrieval.

PRAGMATIC DESIGN: Simple endpoints matching actual use cases.
"""

import logging

from django.http import Http404, HttpResponse
from ninja import Query, Router
from ninja.pagination import paginate
from ninja.errors import HttpError

from common.pagination import ReportPagination
from report.models import Report
from report.schemas import (
    AIAnnotationResponse,
    ImportResponse,
    AdvancedSearchRequest,
    AdvancedSearchResponse,
    ReportExportRequest,
    ReportDetailResponse,
    ReportFilterOptionsResponse,
    ReportImportRequest,
    ReportResponse,
    ReportVersionResponse,
)
from report.service import ReportService
from report.services import AdvancedQueryValidationError

logger = logging.getLogger(__name__)

# Create router
report_router = Router()


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
        report_type: str | None,
        report_status: str | None,
        report_format: str | None,
        date_from: str | None,
        date_to: str | None,
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


@report_router.get('/search', response=list[ReportDetailResponse])
def search_reports(
        request,
        q: str = Query('', description='Search query'),
        limit: int = Query(50, description='Result limit (legacy endpoint - use /search/paginated instead)'),
        offset: int = Query(0, description='Result offset (legacy endpoint)'),
        report_type: str | None = Query(None, description='Filter by report type'),
        report_status: str | None = Query(None, description='Filter by report status'),
        report_format: str | None = Query(None, description='Filter by report format (comma-separated)'),
        date_from: str | None = Query(None, description='Filter by date from (ISO format)'),
        date_to: str | None = Query(None, description='Filter by date to (ISO format)'),
        sort: str = Query('verified_at_desc', description='Sort order: verified_at_desc, verified_at_asc, created_at_desc, title_asc'),
):
    """
    Advanced search for reports with multiple filters.

    ⚠️ DEPRECATED: This endpoint uses legacy limit/offset pagination.
    Please use /search/paginated with page/page_size model instead.

    Legacy support maintained for frontend compatibility.
    Uses shared queryset logic with /search/paginated endpoint.

    Database-level pagination: Uses Django ORM slicing which translates
    to SQL LIMIT/OFFSET. Only requested rows are fetched from database.

    Example SQL generated:
        SELECT * FROM reports
        WHERE is_latest = TRUE AND [filters...]
        ORDER BY verified_at DESC
        LIMIT 20 OFFSET 0

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
    # QuerySet is lazy - SQL not executed yet
    queryset = _get_report_search_queryset(
        q, report_type, report_status, report_format,
        date_from, date_to, sort
    )

    # Apply database-level pagination via Django ORM slicing
    # Django translates queryset[offset:offset+limit] to SQL LIMIT/OFFSET
    # Database returns only requested rows - NOT all records
    results = queryset[offset:offset + limit]

    # Convert to response objects (legacy format - just List[ReportResponse])
    # List comprehension triggers SQL execution here
    return [
        ReportDetailResponse(
            uid=r.uid,
            report_id=r.report_id,
            title=r.title,
            report_type=r.report_type,
            version_number=r.version_number,
            is_latest=r.is_latest,
            created_at=r.created_at.isoformat(),
            verified_at=r.verified_at.isoformat() if r.verified_at else None,
            content_preview=ReportService.safe_truncate(r.content_raw, 500),
            content_raw=r.content_raw,
            source_url=r.source_url,
        )
        for r in results
    ]


@report_router.get('/search/paginated', response=list[ReportDetailResponse])
@paginate(ReportPagination)
def search_reports_paginated(
        request,
        q: str = Query('', description='Search query'),
        report_type: str | None = Query(None, description='Filter by report type'),
        report_status: str | None = Query(None, description='Filter by report status'),
        report_format: str | None = Query(None, description='Filter by report format (comma-separated)'),
        date_from: str | None = Query(None, description='Filter by date from (ISO format)'),
        date_to: str | None = Query(None, description='Filter by date to (ISO format)'),
        sort: str = Query('verified_at_desc', description='Sort order: verified_at_desc, verified_at_asc, created_at_desc, title_asc'),
):
    """
    Advanced search for reports with proper pagination support.

    Uses page/page_size pagination for consistent API experience.
    Compatible with Studies和Projects API pagination model.

    Supports:
    - Full-text search across 6 fields
    - Single-select and multi-select filters
    - Date range filtering
    - Flexible sorting
    - Pagination metadata (page number, total pages, etc.)
    - Embedded filter options (filters key) for dropdown population

    Example: /api/v1/reports/search/paginated?q=covid&page=1&page_size=20
    """
    # Get filtered queryset (shared logic with /search) - @paginate will handle pagination
    return _get_report_search_queryset(
        q, report_type, report_status, report_format,
        date_from, date_to, sort
    )


@report_router.post('/search/advanced', response=AdvancedSearchResponse)
def advanced_search_reports(request, payload: AdvancedSearchRequest):
    """
    Advanced search endpoint that accepts JSON DSL payloads and multi-condition queries.
    
    Returns reports with optional Study information when querying Study fields.
    """
    try:
        return ReportService.advanced_search(payload)
    except AdvancedQueryValidationError as exc:
        raise HttpError(400, str(exc)) from exc


@report_router.post('/export')
def export_reports_endpoint(request, payload: ReportExportRequest):
    """
    Export selected reports as CSV or ZIP blob.
    """
    try:
        data, content_type, filename = ReportService.export_reports(
            report_ids=payload.report_ids,
            export_format=payload.format,
            filename=payload.filename,
        )
    except ValueError as exc:
        raise HttpError(400, str(exc)) from exc

    response = HttpResponse(data, content_type=content_type)
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


@report_router.get('/latest', response=list[ReportResponse])
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
        raise Http404(f'Report not found: {uid}') from None
    except Exception as e:
        logger.error(f'Fetch detail failed: {str(e)}')
        raise


@report_router.get('/study/{exam_id}', response=ReportDetailResponse)
def get_study_report_detail(request, exam_id: str):
    """
    Get full report details including complete content.

    Retrieves the latest version of the report.
    """
    try:
        report = Report.objects.get(report_id=exam_id, is_latest=True)

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
        raise Http404(f'Report not found: {exam_id}') from None
    except Exception as e:
        logger.error(f'Fetch detail failed: {str(e)}')
        raise


@report_router.get('/{report_id}/versions', response=list[ReportVersionResponse])
def get_report_versions(request, report_id: str):
    """
    Get all versions of a report with change history.

    Shows the complete audit trail of changes to the report.
    Useful for tracking updates and understanding evolution.
    """
    try:
        from report.models import ReportVersion
        versions = ReportVersion.objects.filter(report__report_id=report_id).order_by('-version_number')

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


@report_router.get('/filters/options', response=ReportFilterOptionsResponse, operation_id='report_get_filter_options')
@report_router.get('/options/filters', response=ReportFilterOptionsResponse, operation_id='report_get_filter_options_legacy')
def get_filter_options(request):
    """
    Get available filter options for report search.

    Returns distinct values with caching so frontend dropdowns can mirror studies endpoint behavior.

    Example: /api/v1/reports/filters/options
    """
    try:
        if request.path.endswith('/options/filters'):
            logger.warning(
                'DEPRECATED: /api/v1/reports/options/filters will be removed in v2.0.0. '
                'Use /api/v1/reports/filters/options instead.'
            )

        filter_options = ReportService.get_filter_options()
        return ReportFilterOptionsResponse(**filter_options)

    except Exception as e:
        logger.error(f'Fetch filter options failed: {str(e)}')
        raise


@report_router.get('/{uid}/annotations', response=list[AIAnnotationResponse])
def get_report_annotations(request, uid: str):
    """
    Get AI annotations for a specific report.
    """
    try:
        # Check if report exists
        try:
            report = Report.objects.get(pk=uid)
        except Report.DoesNotExist:
            raise Http404(f'Report not found: {uid}') from None

        annotations = report.annotations.all()  # type: ignore[attr-defined]

        return [
            AIAnnotationResponse(
                id=str(a.id),
                report_id=report.uid,
                annotation_type=a.annotation_type,
                content=a.content,
                created_at=a.created_at.isoformat(),
                updated_at=a.updated_at.isoformat() if a.updated_at else None,
                created_by=a.created_by.get_full_name() if a.created_by else None,
                metadata=a.metadata
            )
            for a in annotations
        ]
    except Http404:
        raise
    except Exception as e:
        logger.error(f'Fetch annotations failed: {str(e)}')
        raise
