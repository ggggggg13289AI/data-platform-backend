"""
Report Service - Handle import, deduplication, and version control.

PRAGMATIC DESIGN: Direct functions without over-engineering.
Focuses on actual user scenarios: report import, deduplication, retrieval.
"""

import csv
import hashlib
import io
import logging
import zipfile
from datetime import datetime
from typing import Any

from django.contrib.postgres.search import SearchQuery
from django.db import transaction
from django.db.models import Max, Min, Q, QuerySet
from django.utils import timezone

from common.base_pagination import BasePaginationHelper
from report.models import Report, ReportVersion
from report.schemas import AdvancedSearchRequest
from report.services import AdvancedQueryBuilder, AdvancedQueryValidationError

logger = logging.getLogger(__name__)


class ReportService:
    """Service for managing report lifecycle: import, deduplication, versioning."""

    # Data structure for sort options (Linus rule: eliminate special cases/if-else chains)
    # Tuples guarantee deterministic ordering so Postgres can sort BEFORE LIMIT/OFFSET.
    SORT_MAPPING = {
        "created_at_desc": ("-created_at", "-verified_at", "uid"),
        "title_asc": ("title", "uid"),
        "verified_at_asc": ("verified_at", "created_at", "uid"),
        "verified_at_desc": ("-verified_at", "-created_at", "uid"),
    }
    DEFAULT_SORT_KEY = "verified_at_desc"
    EXPORT_FIELDNAMES = [
        "report_id",
        "uid",
        "title",
        "report_type",
        "version_number",
        "verified_at",
        "created_at",
        "physician",
        "exam_id",
        "patient_name",
        "patient_age",
        "patient_gender",
        "exam_source",
        "exam_item",
        "exam_status",
        "order_datetime",
        "source_url",
        "content_raw",
    ]

    @staticmethod
    def _serialize_report(
        report: Report, study_map: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """
        Convert Report model to API-friendly dictionary.

        Args:
            report: Report instance
            study_map: Pre-fetched mapping of report_id -> study_info dict (for batch optimization)

        Returns:
            Dictionary representation of report with optional study info
        """
        result: dict[str, Any] = {
            "uid": report.uid,
            "report_id": report.report_id,
            "title": report.title,
            "report_type": report.report_type,
            "version_number": report.version_number,
            "is_latest": report.is_latest,
            "created_at": report.created_at.isoformat() if report.created_at else None,
            "verified_at": report.verified_at.isoformat() if report.verified_at else None,
            "content_preview": ReportService.safe_truncate(report.content_raw, 500),
            "content_raw": report.content_raw,
            "source_url": report.source_url,
        }

        # Use pre-fetched study data if available
        if study_map is not None and report.report_id:
            study_info = study_map.get(report.report_id)
            if study_info:
                # Attach study info and expose exam_id on the top-level for frontend batch actions
                result["study"] = study_info
                exam_id = study_info.get("exam_id")
                if exam_id:
                    result["exam_id"] = exam_id

        return result

    @staticmethod
    def _serialize_study(study: Any) -> dict[str, Any]:
        """
        Convert Study model to dictionary for embedding in Report response.

        Args:
            study: Study model instance

        Returns:
            Dictionary with study information
        """
        return {
            "exam_id": study.exam_id,
            "patient_name": study.patient_name,
            "patient_age": study.patient_age,
            "patient_gender": study.patient_gender,
            "exam_source": study.exam_source,
            "exam_item": study.exam_item,
            "exam_status": study.exam_status,
            "equipment_type": study.equipment_type,
            "order_datetime": study.order_datetime.isoformat() if study.order_datetime else None,
            "check_in_datetime": study.check_in_datetime.isoformat()
            if study.check_in_datetime
            else None,
            "report_certification_datetime": study.report_certification_datetime.isoformat()
            if study.report_certification_datetime
            else None,
        }

    @staticmethod
    def _batch_load_studies(report_ids: list[str]) -> dict[str, dict[str, Any]]:
        """
        Batch load Study information for multiple report_ids.

        Solves N+1 query problem by fetching all required studies in a single query.

        Args:
            report_ids: List of report IDs to fetch studies for

        Returns:
            Dictionary mapping report_id -> study_info dict
        """
        if not report_ids:
            return {}

        from study.models import Study

        try:
            # Single query to fetch all required studies
            studies = Study.objects.filter(exam_id__in=report_ids)

            # Build mapping: report_id -> study_info
            study_map = {study.exam_id: ReportService._serialize_study(study) for study in studies}

            logger.debug(f"Batch loaded {len(study_map)} studies for {len(report_ids)} reports")
            return study_map

        except Exception as exc:
            logger.warning(f"Error batch loading studies: {exc}")
            return {}

    @classmethod
    def _resolve_sort_fields(cls, sort_key: str | None) -> tuple[str, ...]:
        """Map sort key to deterministic ordering tuple."""
        if not sort_key:
            sort_key = cls.DEFAULT_SORT_KEY

        sort_fields = cls.SORT_MAPPING.get(sort_key)
        if not sort_fields:
            logger.warning(
                "Unsupported report sort '%s', falling back to '%s'",
                sort_key,
                cls.DEFAULT_SORT_KEY,
            )
            sort_fields = cls.SORT_MAPPING[cls.DEFAULT_SORT_KEY]

        if isinstance(sort_fields, str):
            return (sort_fields,)
        return tuple(sort_fields)

    # Filter configuration - data structure driven (Linus principle: eliminate special cases)
    FILTER_HANDLERS = {
        "report_type": lambda qs, val: qs.filter(report_type=val),
        "report_status": lambda qs, val: qs.filter(metadata__status=val),
        "physician": lambda qs, val: qs.filter(metadata__physician__icontains=val),
    }

    @staticmethod
    def _apply_basic_filters(queryset: QuerySet, filters: dict[str, Any]) -> QuerySet:
        """
        Apply filters using data-driven approach (Good Taste).

        No special cases, no nested ifs - just iterate filter config.
        """
        if not filters:
            return queryset

        # Simple filters: direct field mapping
        for filter_key, handler in ReportService.FILTER_HANDLERS.items():
            value = filters.get(filter_key)
            if value:
                queryset = handler(queryset, value)

        # List filters: normalize to list and use IN clause
        report_format = filters.get("report_format")
        if report_format:
            if isinstance(report_format, str):
                report_format = [report_format]
            queryset = queryset.filter(report_type__in=report_format)

        # ID filters: support multiple field names
        report_id = filters.get("report_id") or filters.get("exam_id")
        if report_id:
            queryset = queryset.filter(report_id__icontains=report_id)

        # Date range filters
        date_from = filters.get("date_from")
        if date_from:
            start_dt = ReportService._parse_datetime(date_from)
            if start_dt:
                queryset = queryset.filter(verified_at__gte=start_dt)

        date_to = filters.get("date_to")
        if date_to:
            end_dt = ReportService._parse_datetime(date_to)
            if end_dt:
                queryset = queryset.filter(verified_at__lte=end_dt)

        return queryset

    @staticmethod
    def advanced_search(payload: AdvancedSearchRequest) -> dict[str, Any]:
        """
        Execute advanced report search combining DSL payload, filters, and pagination.

        Optimized with batch Study loading to avoid N+1 queries.
        """
        queryset = Report.objects.filter(is_latest=True)
        filters = payload.filters.dict(exclude_none=True) if payload.filters else {}
        queryset = ReportService._apply_basic_filters(queryset, filters)

        extra_search_query: SearchQuery | None = None

        if payload.mode == "multi":
            if not payload.tree:
                raise AdvancedQueryValidationError(
                    "Multi-condition payload is required when using multi mode"
                )
            builder_payload = payload.tree.dict(exclude_none=True)
            builder = AdvancedQueryBuilder(builder_payload)
            result = builder.build()
            if result.filters:
                queryset = queryset.filter(result.filters)
            extra_search_query = result.search_query
        else:
            text = payload.basic.text.strip() if payload.basic and payload.basic.text else ""
            if text:
                queryset = queryset.filter(
                    Q(report_id__icontains=text)
                    | Q(uid__icontains=text)
                    | Q(title__icontains=text)
                    | Q(content_processed__icontains=text)
                )
                extra_search_query = SearchQuery(text, config=AdvancedQueryBuilder.SEARCH_CONFIG)

        if extra_search_query is not None:
            queryset = queryset.filter(search_vector=extra_search_query)

        sort_fields = ReportService._resolve_sort_fields(payload.sort)
        queryset = queryset.order_by(*sort_fields)

        page, page_size, total_count, _, paginated_items = (
            BasePaginationHelper.validate_and_paginate(
                queryset,
                payload.page,
                payload.page_size,
            )
        )

        # Batch load Study info to avoid N+1 queries (1-2 queries total)
        # Query 1: Load reports (already done above)
        # Query 2: Load all related studies in single batch query
        report_ids = [report.report_id for report in paginated_items if report.report_id]
        study_map = ReportService._batch_load_studies(report_ids) if report_ids else {}

        # Serialize reports with pre-fetched study data
        items = [
            ReportService._serialize_report(report, study_map=study_map)
            for report in paginated_items
        ]

        total_pages = BasePaginationHelper.calculate_total_pages(total_count, page_size)
        filter_options = ReportService.get_filter_options()

        return {
            "items": items,
            "total": total_count,
            "page": page,
            "page_size": page_size,
            "pages": total_pages,
            "filters": filter_options,
        }

    @staticmethod
    def calculate_content_hash(content: str) -> str:
        """
        Calculate SHA256 hash of content for deduplication.

        Args:
            content: Report content

        Returns:
            Hex digest of SHA256 hash
        """
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    @staticmethod
    def process_content(content: str) -> str:
        """
        Process raw content for full-text search.

        Currently: Just normalize whitespace.
        Future: Could add NLP processing, extraction, etc.

        Args:
            content: Raw report content

        Returns:
            Processed content for search
        """
        # Normalize whitespace
        processed = " ".join(content.split())

        # Could add more processing here:
        # - Remove HTML tags if HTML content
        # - Extract text from PDF
        # - Tokenization
        # - Stemming

        return processed

    @staticmethod
    @transaction.atomic
    def import_or_update_report(
        uid: str,
        title: str,
        content: str,
        report_type: str,
        source_url: str,
        verified_at: datetime | None = None,
        report_id: str | None = None,
        chr_no: str | None = None,
        mod: str | None = None,
        report_date: str | None = None,
        metadata: dict | None = None,
    ) -> tuple[Report, bool, str]:
        """
        Import or update a report with intelligent version control and deduplication.

        DEDUPLICATION LOGIC:
        1. Check if report with same UID exists
        2. If exists:
           - Compare content hash
           - If content same: Keep latest (by verified_at or created_at)
           - If content different: Create new version
        3. If not exists: Create new report

        Args:
            uid: Unique identifier from scraper
            title: Report title
            content: Report content (full text)
            report_type: Format type (PDF, HTML, TXT, etc.)
            source_url: Source URL
            verified_at: Verification timestamp (defaults to now)
            report_id: Internal ID (optional)
            chr_no: Character code (optional)
            mod: Type/Mode (optional)
            report_date: Report date (optional)
            metadata: Dynamic metadata (optional)

        Returns:
            Tuple of (Report object, is_new, action_taken)
            - Report: The report object
            - is_new: Whether this is a new report or update
            - action_taken: Description of action (create/update/deduplicate)
        """

        if verified_at is None:
            verified_at = timezone.now()

        content_hash = ReportService.calculate_content_hash(content)
        processed_content = ReportService.process_content(content)

        # Check if report with this UID exists
        try:
            existing_report = Report.objects.get(pk=uid)
        except Report.DoesNotExist:
            # NEW REPORT - Create it
            report = Report.objects.create(
                uid=uid,
                report_id=report_id or uid,
                title=title,
                report_type=report_type,
                content_raw=content,
                content_processed=processed_content,
                content_hash=content_hash,
                source_url=source_url,
                verified_at=verified_at,
                chr_no=chr_no,
                mod=mod,
                report_date=report_date,
                metadata=metadata or {},
                version_number=1,
                is_latest=True,
            )

            # Create initial version record
            ReportVersion.objects.create(
                report=report,
                version_number=1,
                content_hash=content_hash,
                content_raw=content,
                verified_at=verified_at,
                change_type="create",
                change_description="Initial import",
            )

            return report, True, "create"

        # EXISTING REPORT - Check for update
        if existing_report.content_hash == content_hash:
            # SAME CONTENT - Deduplication
            # Keep the one with latest verified_at, or created_at if verified_at is None

            new_timestamp = verified_at or timezone.now()
            existing_timestamp = existing_report.verified_at or existing_report.created_at

            if new_timestamp > existing_timestamp:
                # New version is more recent, update the existing report
                existing_report.verified_at = new_timestamp
                existing_report.updated_at = timezone.now()
                existing_report.save(update_fields=["verified_at", "updated_at"])

                return existing_report, False, "deduplicate (updated timestamp)"
            else:
                # Existing version is more recent, keep it
                return existing_report, False, "deduplicate (kept existing)"

        # DIFFERENT CONTENT - Create new version
        new_version_number = existing_report.version_number + 1

        # Mark old version as not latest
        existing_report.is_latest = False
        existing_report.save(update_fields=["is_latest"])

        # Update main report with new content
        existing_report.title = title
        existing_report.content_raw = content
        existing_report.content_processed = processed_content
        existing_report.content_hash = content_hash
        existing_report.version_number = new_version_number
        existing_report.is_latest = True
        existing_report.verified_at = verified_at
        existing_report.updated_at = timezone.now()
        existing_report.metadata = metadata or existing_report.metadata

        # Update optional fields if provided
        if chr_no:
            existing_report.chr_no = chr_no
        if mod:
            existing_report.mod = mod
        if report_date:
            existing_report.report_date = report_date

        existing_report.save()

        # Create version record
        ReportVersion.objects.create(
            report=existing_report,
            version_number=new_version_number,
            content_hash=content_hash,
            content_raw=content,
            verified_at=verified_at,
            change_type="update",
            change_description="Content updated",
        )

        return existing_report, False, f"update (version {new_version_number})"

    @staticmethod
    def get_latest_reports(limit: int = 100) -> list[Report]:
        """Get latest versions of all reports."""
        queryset = Report.objects.filter(is_latest=True).order_by("-verified_at")[:limit]
        return list(queryset)

    @staticmethod
    def safe_truncate(text: str, max_length: int = 500, encoding: str = "utf-8") -> str:
        """
        Safely truncate text at character boundaries (Good Taste).

        Prevents cutting multi-byte characters like Chinese.
        Early return strategy - no nested complexity.
        """
        if not text or len(text) <= max_length:
            return text

        # Simple approach: truncate and validate
        for length in range(max_length, max(0, max_length - 4), -1):
            truncated = text[:length]
            try:
                truncated.encode(encoding)
                return truncated
            except UnicodeEncodeError:
                continue

        # Fallback: return empty if all attempts fail
        return ""

    @staticmethod
    def search_reports(query: str, limit: int = 50) -> list[Report]:
        """
        Search reports by multiple fields: report_id, uid, title, chr_no, mod, content_processed, metadata.

        Expanded search supports:
        - Identifier search: report_id, uid, chr_no, mod
        - Content search: title, content_processed
        - Flexible metadata search

        Args:
            query: Search query
            limit: Maximum results

        Returns:
            List of matching reports
        """
        from django.db.models import Q

        queryset = Report.objects.filter(
            Q(report_id__icontains=query)
            | Q(uid__icontains=query)
            | Q(title__icontains=query)
            | Q(chr_no__icontains=query)
            | Q(mod__icontains=query)
            | Q(content_processed__icontains=query),
            is_latest=True,
        ).order_by("-verified_at")[:limit]
        return list(queryset)

    @staticmethod
    def get_reports_queryset(
        q: str | None = None,
        report_type: str | None = None,
        report_status: str | None = None,
        report_format: list[str] | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        sort: str = "verified_at_desc",
    ) -> "QuerySet":
        """
        Get filtered queryset for reports - OPTIMIZED with Raw SQL.

        OPTIMIZATION: Uses raw SQL with proper parameterization instead of ORM
        to leverage database query planner and support complex filtering.

        Args:
            q: Text search across 6 fields (report_id, uid, title, chr_no, mod, content_processed)
            report_type: Filter by type (PDF, HTML, TXT, etc.)
            report_status: Filter by status (pending, completed, archived, etc.)
            report_format: Filter by format (multi-select array, uses IN clause)
            date_from: Created date from (YYYY-MM-DD format)
            date_to: Created date to (YYYY-MM-DD format)
            sort: Sort order (verified_at_desc, created_at_desc, title_asc)

        Returns:
            Filtered and sorted QuerySet of Report objects
        """
        from django.db.models import Q

        # Build base queryset
        queryset = Report.objects.filter(is_latest=True)

        # TEXT SEARCH: Comprehensive 6-field search with OR logic
        # Covers all identifier and content fields for flexible searching
        if q and q.strip():
            queryset = queryset.filter(
                Q(report_id__icontains=q)
                | Q(uid__icontains=q)
                | Q(title__icontains=q)
                | Q(chr_no__icontains=q)
                | Q(mod__icontains=q)
                | Q(content_processed__icontains=q)
            ).exclude(report_type="system_data")

        # SINGLE-SELECT FILTERS: Exact match for single-value parameters
        if report_type:
            queryset = queryset.filter(report_type=report_type)

        if report_status:
            # Note: Will need to add status field to Report model if used
            queryset = queryset.filter(metadata__status=report_status)

        # MULTI-SELECT FILTERS: IN clause for array parameters
        # Frontend sends arrays like: report_format=['PDF', 'HTML']
        if report_format and len(report_format) > 0:
            queryset = queryset.filter(report_type__in=report_format)

        # DATE RANGE FILTERING: Use existing parser (DRY principle)
        if date_from:
            start_dt = ReportService._parse_datetime(date_from)
            if start_dt:
                queryset = queryset.filter(verified_at__gte=start_dt)

        if date_to:
            end_dt = ReportService._parse_datetime(date_to)
            if end_dt:
                queryset = queryset.filter(verified_at__lte=end_dt)

        # SORT ORDER DETERMINATION
        # Data structure driven sorting (Linus rule: eliminate special cases)
        # Default: verified_at_desc (Most recent first, deterministic tie-breakers)
        sort_fields = ReportService._resolve_sort_fields(sort)
        queryset = queryset.order_by(*sort_fields)

        return queryset

    @staticmethod
    def get_filter_options() -> dict[str, Any]:
        """
        Get available filter options for reports - with Redis caching.

        Returns distinct report types for frontend filter dropdowns.
        Caches results for 24 hours to reduce database queries.

        Cache Strategy:
        - TRY: Get from Redis cache with key 'report:filter_options'
        - FALLBACK: Query database if cache miss or unavailable
        - SET: Cache result with 24-hour TTL

        Returns:
            Dictionary with filter options:
            {
                'report_types': ['PDF', 'HTML', 'TXT', 'XRay', 'MRI', ...]
            }
        """
        import logging

        from django.core.cache import cache

        logger = logging.getLogger(__name__)
        cache_key = "report:filter_options"
        cache_ttl = 24 * 60 * 60  # 24 hours in seconds

        try:
            # TRY CACHE FIRST
            cached_options = cache.get(cache_key)
            if cached_options is not None:
                logger.debug("Report filter options retrieved from cache")
                # Type narrowing: cache.get returns Any
                assert isinstance(cached_options, dict), "Cached filter options must be dict"
                return cached_options
        except Exception as e:
            logger.warning(f"Cache retrieval failed: {str(e)}, falling back to database")

        try:
            # FALLBACK TO DATABASE
            # Get distinct report types, ordered for consistency
            report_types = list(
                Report.objects.exclude(report_type__isnull=True)
                .exclude(report_type="")
                .values_list("report_type", flat=True)
                .distinct()
                .order_by("report_type")
            )

            report_statuses = list(
                Report.objects.exclude(metadata__status__isnull=True)
                .exclude(metadata__status="")
                .values_list("metadata__status", flat=True)
                .distinct()
                .order_by("metadata__status")
            )

            mods = list(
                Report.objects.exclude(mod__isnull=True)
                .exclude(mod="")
                .values_list("mod", flat=True)
                .distinct()
                .order_by("mod")
            )

            date_range = Report.objects.aggregate(
                min_verified_at=Min("verified_at"),
                max_verified_at=Max("verified_at"),
            )

            filter_options = {
                "report_types": report_types,
                "report_statuses": report_statuses,
                "mods": mods,
                "verified_date_range": {
                    "start": date_range["min_verified_at"].isoformat()
                    if date_range["min_verified_at"]
                    else None,
                    "end": date_range["max_verified_at"].isoformat()
                    if date_range["max_verified_at"]
                    else None,
                },
            }

            # TRY TO CACHE RESULT
            try:
                cache.set(cache_key, filter_options, cache_ttl)
                logger.debug(f"Report filter options cached for {cache_ttl}s")
            except Exception as e:
                logger.warning(f"Cache setting failed: {str(e)}, continuing without cache")

            return filter_options

        except Exception as e:
            logger.error(f"Error fetching filter options: {str(e)}")
            # Return empty fallback to prevent API failure
            return {
                "report_types": [],
                "report_statuses": [],
                "mods": [],
                "verified_date_range": {"start": None, "end": None},
            }

    # Date format patterns - data structure driven (Good Taste)
    DATE_FORMATS = [
        "%Y-%m-%dT%H:%M:%S.%fZ",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
        "%Y%m%d",
    ]

    @staticmethod
    def _parse_datetime(date_str: str) -> datetime | None:
        """
        Parse datetime - data structure driven (Good Taste).

        No nested try-except, just iterate through format list.
        """
        if not date_str:
            return None

        # Try ISO format first (most common)
        try:
            return datetime.fromisoformat(date_str)
        except (ValueError, TypeError):
            pass

        # Try other formats
        for fmt in ReportService.DATE_FORMATS:
            try:
                return datetime.strptime(date_str, fmt)
            except (ValueError, TypeError):
                continue

        return None

    # Report type classification - data structure driven (Good Taste)
    IMAGING_TYPES = {
        "MR": "MRI",
        "CR": "XRay",
        "CT": "CT",
        "US": "Ultrasound",
        "MG": "Mammography",
        "OT": "Other",
        "RF": "Fluoroscopy",
    }

    NON_IMAGING_PATTERNS = {
        "pt.get": "patient_info",
        "allergy": "allergy",
        "lab": "laboratory",
        "vital": "vitals",
        "hcheckup": "health_checkup",
    }

    @staticmethod
    def _determine_report_type(mod: str, record_id: str) -> str:
        """
        Determine report type - data structure driven (Good Taste).

        No if-elif chains, just lookup tables.
        """
        mod = (mod or "").strip().upper()

        # Try exact match first (imaging types)
        if mod in ReportService.IMAGING_TYPES:
            return ReportService.IMAGING_TYPES[mod]

        # Try pattern match (non-imaging types)
        mod_lower = mod.lower()
        for pattern, report_type in ReportService.NON_IMAGING_PATTERNS.items():
            if pattern in mod_lower:
                return report_type

        # Default fallback
        return "legacy" if record_id == "unknown" else "imaging"

    @staticmethod
    @transaction.atomic
    def migrate_from_legacy_db(
        legacy_db_path: str, batch_size: int = 500, skip_patient_info: bool = False
    ) -> dict[str, Any]:
        """
        Migrate reports from legacy SQLite database (one_page_text_report).

        Intelligently handles:
        - Image reports (id != 'unknown'): pt.get_resource API results
        - System records (id = 'unknown'): Various API results (pt.get, allergy, lab, etc.)

        Args:
            legacy_db_path: Path to legacy data.db file
            batch_size: Number of records to process per batch
            skip_patient_info: Whether to skip pt.get patient info records

        Returns:
            Migration statistics and details
        """
        import logging
        import sqlite3
        from pathlib import Path

        logger = logging.getLogger(__name__)

        if not Path(legacy_db_path).exists():
            raise FileNotFoundError(f"Legacy database not found: {legacy_db_path}")

        conn = sqlite3.connect(legacy_db_path)
        cursor = conn.cursor()

        # Get total count for progress tracking
        cursor.execute("SELECT COUNT(*) FROM one_page_text_report")
        total_count = cursor.fetchone()[0]

        cursor.execute(
            "SELECT uid, id, title, content, date, v_date, mod, chr_no FROM one_page_text_report"
        )
        rows = cursor.fetchall()

        stats = {
            "total": total_count,
            "created": 0,
            "updated": 0,
            "duplicated": 0,
            "skipped": 0,
            "errors": 0,
            "by_type": {},
        }

        processed = 0
        for row in rows:
            try:
                uid, record_id, title, content, date_str, v_date_str, mod, chr_no = row

                # Skip patient info records if requested
                if skip_patient_info and record_id == "unknown" and (mod or "").strip() == "pt.get":
                    stats["skipped"] += 1
                    continue

                # Determine report type
                report_type = ReportService._determine_report_type(mod, record_id)

                # Parse dates
                report_date = ReportService._parse_datetime(date_str)
                verified_at = ReportService._parse_datetime(v_date_str)

                # For unknown records without explicit dates, use current time
                if not verified_at:
                    verified_at = timezone.now()

                # Generate meaningful title if missing
                if not title or title.strip() == "pt.get":
                    title = (
                        f"{report_type.upper()} Report"
                        if record_id != "unknown"
                        else f"{mod or 'Unknown'}"
                    )

                # Import report
                report, is_new, action = ReportService.import_or_update_report(
                    uid=uid,
                    report_id=record_id if record_id != "unknown" else uid[:32],
                    title=title[:500],
                    content=content or "",
                    report_type=report_type,
                    source_url="",
                    verified_at=verified_at,
                    mod=mod,
                    chr_no=chr_no,
                    report_date=str(report_date.date()) if report_date else None,
                    metadata={
                        "legacy_id": record_id,
                        "legacy_uid": uid,
                        "legacy_import": True,
                    },
                )

                # Update statistics
                if is_new:
                    stats["created"] += 1
                elif "deduplicate" in action:
                    stats["duplicated"] += 1
                else:
                    stats["updated"] += 1

                # Track by type
                if report_type not in stats["by_type"]:
                    stats["by_type"][report_type] = {"created": 0, "updated": 0, "duplicated": 0}

                if is_new:
                    stats["by_type"][report_type]["created"] += 1
                elif "deduplicate" in action:
                    stats["by_type"][report_type]["duplicated"] += 1
                else:
                    stats["by_type"][report_type]["updated"] += 1

                processed += 1
                if processed % batch_size == 0:
                    logger.info(f"Migrated {processed}/{total_count} records")

            except Exception as e:
                stats["errors"] += 1
                logger.error(f"Error migrating record: {str(e)}")
                continue

        conn.close()

        # Add summary
        stats["summary"] = {
            "success_rate": f"{(100 * (processed - stats['errors']) / total_count):.1f}%"
            if total_count > 0
            else "0%",
            "total_processed": processed,
        }

        return stats

    @classmethod
    def _build_export_rows(cls, reports: list[Report]) -> list[dict[str, str]]:
        """Build export rows with report + study metadata."""
        if not reports:
            return []

        study_map = cls._batch_load_studies([r.report_id for r in reports if r.report_id])
        rows: list[dict[str, str]] = []

        for report in reports:
            metadata = report.metadata if isinstance(report.metadata, dict) else {}
            study_info = study_map.get(report.report_id, {}) if report.report_id else {}

            rows.append(
                {
                    "report_id": report.report_id or "",
                    "uid": report.uid,
                    "title": report.title,
                    "report_type": report.report_type,
                    "version_number": str(report.version_number),
                    "verified_at": report.verified_at.isoformat() if report.verified_at else "",
                    "created_at": report.created_at.isoformat() if report.created_at else "",
                    "physician": metadata.get("physician", "")
                    if isinstance(metadata, dict)
                    else "",
                    "exam_id": study_info.get("exam_id", ""),
                    "patient_name": study_info.get("patient_name", ""),
                    "patient_age": str(study_info.get("patient_age", ""))
                    if study_info.get("patient_age") is not None
                    else "",
                    "patient_gender": study_info.get("patient_gender", ""),
                    "exam_source": study_info.get("exam_source", ""),
                    "exam_item": study_info.get("exam_item", ""),
                    "exam_status": study_info.get("exam_status", ""),
                    "order_datetime": study_info.get("order_datetime", ""),
                    "source_url": report.source_url or "",
                    "content_raw": report.content_raw or "",
                }
            )

        return rows

    @classmethod
    def _rows_to_csv(cls, rows: list[dict[str, str]]) -> bytes:
        """Serialize rows to CSV bytes with UTF-8 BOM for Excel compatibility."""
        buffer = io.StringIO()
        writer = csv.DictWriter(buffer, fieldnames=cls.EXPORT_FIELDNAMES)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
        return buffer.getvalue().encode("utf-8-sig")

    @classmethod
    def export_reports(
        cls,
        report_ids: list[str],
        export_format: str | None = "zip",
        filename: str | None = None,
    ) -> tuple[bytes, str, str]:
        """
        Generate export payload (CSV or ZIP) for selected reports.
        """
        normalized_ids = [rid for rid in dict.fromkeys(report_ids or []) if rid]
        if not normalized_ids:
            raise ValueError("report_ids is required")

        reports = list(
            Report.objects.filter(report_id__in=normalized_ids, is_latest=True).order_by(
                "report_id"
            )
        )
        if not reports:
            raise ValueError("找不到對應的報告")

        rows = cls._build_export_rows(reports)
        csv_bytes = cls._rows_to_csv(rows)

        export_format = (export_format or "zip").lower()
        timestamp = timezone.now().strftime("%Y%m%d-%H%M%S")
        base_filename = filename or f"reports_export_{timestamp}"

        if export_format == "csv":
            final_name = (
                base_filename if base_filename.lower().endswith(".csv") else f"{base_filename}.csv"
            )
            return csv_bytes, "text/csv", final_name

        if export_format == "zip":
            final_name = (
                base_filename if base_filename.lower().endswith(".zip") else f"{base_filename}.zip"
            )
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, "w", compression=zipfile.ZIP_DEFLATED) as zip_file:
                zip_file.writestr("reports.csv", csv_bytes)
            return zip_buffer.getvalue(), "application/zip", final_name

        raise ValueError("Unsupported export format")


class ReportImportConfig:
    """Configuration for report import operations."""

    # Import limits
    MAX_IMPORT_BATCH_SIZE: int = 1000
    """Maximum records per import batch"""

    # Content limits
    MAX_CONTENT_SIZE: int = 10 * 1024 * 1024  # 10MB
    """Maximum content size (bytes)"""

    # Search configuration
    DEFAULT_SEARCH_LIMIT: int = 50
    """Default search result limit"""

    MAX_SEARCH_LIMIT: int = 500
    """Maximum search result limit"""
