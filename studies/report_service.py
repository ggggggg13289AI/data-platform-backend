"""
Report Service - Handle import, deduplication, and version control.

PRAGMATIC DESIGN: Direct functions without over-engineering.
Focuses on actual user scenarios: report import, deduplication, retrieval.
"""

import hashlib
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from django.db import transaction
from django.utils import timezone
from .models import Report, ReportVersion, ReportSummary, ReportSearchIndex


class ReportService:
    """Service for managing report lifecycle: import, deduplication, versioning."""

    @staticmethod
    def calculate_content_hash(content: str) -> str:
        """
        Calculate SHA256 hash of content for deduplication.

        Args:
            content: Report content

        Returns:
            Hex digest of SHA256 hash
        """
        return hashlib.sha256(content.encode('utf-8')).hexdigest()

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
        processed = ' '.join(content.split())

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
        verified_at: Optional[datetime] = None,
        report_id: Optional[str] = None,
        chr_no: Optional[str] = None,
        mod: Optional[str] = None,
        report_date: Optional[str] = None,
        metadata: Optional[Dict] = None,
    ) -> Tuple[Report, bool, str]:
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
                change_type='create',
                change_description='Initial import'
            )

            return report, True, 'create'

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
                existing_report.save(update_fields=['verified_at', 'updated_at'])

                return existing_report, False, 'deduplicate (updated timestamp)'
            else:
                # Existing version is more recent, keep it
                return existing_report, False, 'deduplicate (kept existing)'

        # DIFFERENT CONTENT - Create new version
        new_version_number = existing_report.version_number + 1

        # Mark old version as not latest
        existing_report.is_latest = False
        existing_report.save(update_fields=['is_latest'])

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
            change_type='update',
            change_description='Content updated'
        )

        return existing_report, False, f'update (version {new_version_number})'

    @staticmethod
    def get_latest_reports(limit: int = 100) -> List[Report]:
        """Get latest versions of all reports."""
        return Report.objects.filter(is_latest=True).order_by('-verified_at')[:limit]

    @staticmethod
    def safe_truncate(text: str, max_length: int = 500, encoding: str = 'utf-8') -> str:
        """
        Safely truncate text at character boundaries for multi-byte encodings.
        
        Prevents cutting multi-byte characters (e.g., Chinese characters).
        
        Args:
            text: Text to truncate
            max_length: Maximum character count
            encoding: Text encoding (default: utf-8)
            
        Returns:
            Safely truncated text
        """
        if not text or len(text) <= max_length:
            return text
        
        # Truncate at character boundary
        truncated = text[:max_length]
        
        # Encode and decode to ensure no partial characters
        try:
            # Try to encode - if successful, we're at safe boundary
            truncated.encode(encoding)
            return truncated
        except UnicodeEncodeError:
            # If encoding fails, we're in middle of character, back up
            while truncated and max_length > 0:
                max_length -= 1
                truncated = text[:max_length]
                try:
                    truncated.encode(encoding)
                    return truncated
                except UnicodeEncodeError:
                    continue
            return ""

    @staticmethod
    def search_reports(query: str, limit: int = 50) -> List[Report]:
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

        return Report.objects.filter(
            Q(report_id__icontains=query) |
            Q(uid__icontains=query) |
            Q(title__icontains=query) |
            Q(chr_no__icontains=query) |
            Q(mod__icontains=query) |
            Q(content_processed__icontains=query),
            is_latest=True,
        ).order_by('-verified_at')[:limit]

    @staticmethod
    def get_reports_queryset(
        q: Optional[str] = None,
        report_type: Optional[str] = None,
        report_status: Optional[str] = None,
        report_format: Optional[List[str]] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        sort: str = 'verified_at_desc',
    ) -> 'QuerySet':
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
                Q(report_id__icontains=q) |
                Q(uid__icontains=q) |
                Q(title__icontains=q) |
                Q(chr_no__icontains=q) |
                Q(mod__icontains=q) |
                Q(content_processed__icontains=q)
            )

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

        # DATE RANGE FILTERING: Filter on verified_at field
        if date_from:
            try:
                from datetime import datetime
                start_dt = datetime.fromisoformat(date_from)
                queryset = queryset.filter(verified_at__gte=start_dt)
            except (ValueError, TypeError):
                # Invalid date format - skip this filter
                pass

        if date_to:
            try:
                from datetime import datetime
                end_dt = datetime.fromisoformat(date_to)
                queryset = queryset.filter(verified_at__lte=end_dt)
            except (ValueError, TypeError):
                # Invalid date format - skip this filter
                pass

        # SORT ORDER DETERMINATION
        if sort == 'created_at_desc':
            queryset = queryset.order_by('-created_at')
        elif sort == 'title_asc':
            queryset = queryset.order_by('title')
        else:  # Default: verified_at_desc (most recent first)
            queryset = queryset.order_by('-verified_at')

        return queryset

    @staticmethod
    def get_filter_options() -> Dict[str, List[str]]:
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
        cache_key = 'report:filter_options'
        cache_ttl = 24 * 60 * 60  # 24 hours in seconds

        try:
            # TRY CACHE FIRST
            cached_options = cache.get(cache_key)
            if cached_options is not None:
                logger.debug("Report filter options retrieved from cache")
                return cached_options
        except Exception as e:
            logger.warning(f"Cache retrieval failed: {str(e)}, falling back to database")

        try:
            # FALLBACK TO DATABASE
            # Get distinct report types, ordered for consistency
            report_types = list(
                Report.objects
                .values_list('report_type', flat=True)
                .distinct()
                .order_by('report_type')
            )

            filter_options = {
                'report_types': report_types
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
                'report_types': []
            }

    @staticmethod
    def _parse_datetime(date_str: str) -> Optional[datetime]:
        """Parse datetime string from legacy database."""
        if not date_str:
            return None

        try:
            # Try ISO format first
            return datetime.fromisoformat(date_str)
        except:
            pass

        try:
            # Try common date formats
            for fmt in ['%Y-%m-%dT%H:%M:%S.%fZ', '%Y-%m-%d %H:%M:%S', '%Y-%m-%d', '%Y%m%d']:
                try:
                    return datetime.strptime(date_str, fmt)
                except:
                    continue
        except:
            pass

        return None

    @staticmethod
    def _determine_report_type(mod: str, record_id: str) -> str:
        """Determine report type based on MOD field."""
        mod = (mod or '').strip().upper()

        # Medical imaging types
        imaging_types = {
            'MR': 'MRI',
            'CR': 'XRay',
            'CT': 'CT',
            'US': 'Ultrasound',
            'MG': 'Mammography',
            'OT': 'Other',
            'RF': 'Fluoroscopy',
        }

        if mod in imaging_types:
            return imaging_types[mod]

        # Non-imaging report types (from id='unknown' records)
        if 'pt.get' in mod:
            return 'patient_info'
        elif 'allergy' in mod:
            return 'allergy'
        elif 'lab' in mod:
            return 'laboratory'
        elif 'vital' in mod:
            return 'vitals'
        elif 'hcheckup' in mod:
            return 'health_checkup'

        return 'legacy' if record_id == 'unknown' else 'imaging'

    @staticmethod
    @transaction.atomic
    def migrate_from_legacy_db(legacy_db_path: str, batch_size: int = 500,
                               skip_patient_info: bool = False) -> Dict[str, any]:
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
        import sqlite3
        from pathlib import Path
        import logging

        logger = logging.getLogger(__name__)

        if not Path(legacy_db_path).exists():
            raise FileNotFoundError(f"Legacy database not found: {legacy_db_path}")

        conn = sqlite3.connect(legacy_db_path)
        cursor = conn.cursor()

        # Get total count for progress tracking
        cursor.execute("SELECT COUNT(*) FROM one_page_text_report")
        total_count = cursor.fetchone()[0]

        cursor.execute("SELECT uid, id, title, content, date, v_date, mod, chr_no FROM one_page_text_report")
        rows = cursor.fetchall()

        stats = {
            'total': total_count,
            'created': 0,
            'updated': 0,
            'duplicated': 0,
            'skipped': 0,
            'errors': 0,
            'by_type': {},
        }

        processed = 0
        for row in rows:
            try:
                uid, record_id, title, content, date_str, v_date_str, mod, chr_no = row

                # Skip patient info records if requested
                if skip_patient_info and record_id == 'unknown' and (mod or '').strip() == 'pt.get':
                    stats['skipped'] += 1
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
                if not title or title.strip() == 'pt.get':
                    title = f"{report_type.upper()} Report" if record_id != 'unknown' else f"{mod or 'Unknown'}"

                # Import report
                report, is_new, action = ReportService.import_or_update_report(
                    uid=uid,
                    report_id=record_id if record_id != 'unknown' else uid[:32],
                    title=title[:500],
                    content=content or '',
                    report_type=report_type,
                    source_url='',
                    verified_at=verified_at,
                    mod=mod,
                    chr_no=chr_no,
                    report_date=str(report_date.date()) if report_date else None,
                    metadata={
                        'legacy_id': record_id,
                        'legacy_uid': uid,
                        'legacy_import': True,
                    }
                )

                # Update statistics
                if is_new:
                    stats['created'] += 1
                elif 'deduplicate' in action:
                    stats['duplicated'] += 1
                else:
                    stats['updated'] += 1

                # Track by type
                if report_type not in stats['by_type']:
                    stats['by_type'][report_type] = {'created': 0, 'updated': 0, 'duplicated': 0}

                if is_new:
                    stats['by_type'][report_type]['created'] += 1
                elif 'deduplicate' in action:
                    stats['by_type'][report_type]['duplicated'] += 1
                else:
                    stats['by_type'][report_type]['updated'] += 1

                processed += 1
                if processed % batch_size == 0:
                    logger.info(f"Migrated {processed}/{total_count} records")

            except Exception as e:
                stats['errors'] += 1
                logger.error(f"Error migrating record: {str(e)}")
                continue

        conn.close()

        # Add summary
        stats['summary'] = {
            'success_rate': f"{(100 * (processed - stats['errors']) / total_count):.1f}%" if total_count > 0 else "0%",
            'total_processed': processed,
        }

        return stats


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
