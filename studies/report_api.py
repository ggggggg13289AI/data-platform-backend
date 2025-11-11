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
    report_id: str
    title: str
    report_type: str
    version_number: int
    is_latest: bool
    created_at: str
    verified_at: Optional[str]
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


@report_router.get('/search', response=List[ReportResponse])
def search_reports(
    request,
    q: str = Query('', description='Search query'),
    limit: int = Query(50, description='Result limit'),
):
    """
    Search reports by title and content.

    Supports:
    - Full-text search on title and processed content
    - Efficient ranking by verification date

    Example: /api/v1/reports/search?q=covid&limit=20
    """
    try:
        if limit > 500:
            limit = 500

        results = ReportService.search_reports(q, limit)

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
                content_preview=r.content_raw[:500],
            )
            for r in results
        ]

    except Exception as e:
        logger.error(f'Search failed: {str(e)}')
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
                content_preview=r.content_raw[:500],
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
