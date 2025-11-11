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
    def search_reports(query: str, limit: int = 50) -> List[Report]:
        """
        Search reports by title and content.

        Future: Could use full-text search (FTS5) or PostgreSQL if needed.
        Current: Using simple icontains query.

        Args:
            query: Search query
            limit: Maximum results

        Returns:
            List of matching reports
        """
        from django.db.models import Q

        return Report.objects.filter(
            Q(title__icontains=query) |
            Q(content_processed__icontains=query),
            is_latest=True
        ).order_by('-verified_at')[:limit]

    @staticmethod
    def get_report_history(report_id: str) -> List[ReportVersion]:
        """Get all versions of a report."""
        try:
            report = Report.objects.get(pk=report_id)
            return report.versions.all().order_by('-version_number')
        except Report.DoesNotExist:
            return []

    @staticmethod
    @transaction.atomic
    def migrate_from_legacy_db(legacy_db_path: str) -> Dict[str, int]:
        """
        Migrate reports from legacy SQLite database (one_page_text_report).

        This function reads from the legacy data.db and imports into new schema.

        Args:
            legacy_db_path: Path to legacy data.db file

        Returns:
            Migration statistics {created, updated, duplicates}
        """
        import sqlite3
        from pathlib import Path

        if not Path(legacy_db_path).exists():
            raise FileNotFoundError(f"Legacy database not found: {legacy_db_path}")

        conn = sqlite3.connect(legacy_db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT uid, id, title, content, date, v_date, mod, chr_no FROM one_page_text_report")
        rows = cursor.fetchall()

        stats = {'created': 0, 'updated': 0, 'duplicated': 0}

        for row in rows:
            uid, report_id, title, content, date_str, v_date_str, mod, chr_no = row

            # Parse dates
            try:
                verified_at = datetime.fromisoformat(v_date_str) if v_date_str else None
            except:
                verified_at = None

            report, is_new, action = ReportService.import_or_update_report(
                uid=uid,
                report_id=report_id or uid,
                title=title or 'Untitled',
                content=content or '',
                report_type='legacy',
                source_url='',
                verified_at=verified_at,
                mod=mod,
                chr_no=chr_no,
                report_date=date_str,
            )

            if is_new:
                stats['created'] += 1
            elif 'deduplicate' in action:
                stats['duplicated'] += 1
            else:
                stats['updated'] += 1

        conn.close()
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
