from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from report.models import Report
from report.service import ReportService


class ReportServiceSortingTests(TestCase):
    """Test sorting functionality for ReportService."""

    @classmethod
    def setUpTestData(cls):
        """Create test data with different verified_at values."""
        base_time = timezone.now()

        # Create 3 reports with different verified_at times
        cls.r1 = Report.objects.create(
            uid="R1",
            report_id="REP001",
            title="Report 1",
            report_type="PDF",
            content_raw="Content 1",
            verified_at=base_time - timedelta(days=2),  # Oldest
            is_latest=True,
            version_number=1,
        )

        cls.r2 = Report.objects.create(
            uid="R2",
            report_id="REP002",
            title="Report 2",
            report_type="PDF",
            content_raw="Content 2",
            verified_at=base_time - timedelta(days=1),  # Middle
            is_latest=True,
            version_number=1,
        )

        cls.r3 = Report.objects.create(
            uid="R3",
            report_id="REP003",
            title="Report 3",
            report_type="PDF",
            content_raw="Content 3",
            verified_at=base_time,  # Newest
            is_latest=True,
            version_number=1,
        )

    def test_sort_by_verified_at_desc_default(self):
        """Test sorting by verified_at descending (default)."""
        # Act
        queryset = ReportService.get_reports_queryset(sort="verified_at_desc")

        # Assert
        reports = list(queryset)
        self.assertEqual(len(reports), 3)
        self.assertEqual(reports[0].uid, "R3")  # Newest first
        self.assertEqual(reports[1].uid, "R2")
        self.assertEqual(reports[2].uid, "R1")  # Oldest last

    def test_sort_by_verified_at_asc(self):
        """Test sorting by verified_at ascending (oldest first)."""
        # Act
        queryset = ReportService.get_reports_queryset(sort="verified_at_asc")

        # Assert
        reports = list(queryset)
        self.assertEqual(len(reports), 3)
        self.assertEqual(reports[0].uid, "R1")  # Oldest first
        self.assertEqual(reports[1].uid, "R2")
        self.assertEqual(reports[2].uid, "R3")  # Newest last

    def test_sort_by_title_asc(self):
        """Test sorting by title ascending."""
        # Act
        queryset = ReportService.get_reports_queryset(sort="title_asc")

        # Assert
        reports = list(queryset)
        self.assertEqual(len(reports), 3)
        self.assertEqual(reports[0].title, "Report 1")
        self.assertEqual(reports[1].title, "Report 2")
        self.assertEqual(reports[2].title, "Report 3")
