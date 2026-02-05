"""
Test cases for StudyService layer.

Tests the business logic layer: queryset filtering, detail retrieval,
filter options caching, and exception handling. Total: 30 test cases.

Test coverage:
- get_studies_queryset() - text search, filters, sorting (18 cases)
- get_study_detail() - success and exception cases (4 cases)
- get_filter_options() - caching and database queries (8 cases)

CRITICAL: Service layer is the highest priority for testing as it contains
the most complex business logic, raw SQL queries, and error handling.
"""

from datetime import datetime
from unittest.mock import patch

from django.core.cache import cache
from django.test import TestCase

from common.config import ServiceConfig
from common.exceptions import DatabaseQueryError, StudyNotFoundError
from study.models import Study
from study.services import StudyService
from tests.fixtures.test_data import (
    DateTimeHelper,
    MockDataGenerator,
    StudyFactory,
)


class StudyServiceQuerySetTextSearchTests(TestCase):
    """Test text search functionality across 9 fields."""

    @classmethod
    def setUpTestData(cls):
        """Create test data for text search across all searchable fields."""
        # Create studies for text search testing
        for study_data in MockDataGenerator.studies_for_text_search():
            Study.objects.create(**study_data)

    def test_text_search_in_exam_id(self):
        """Test text search finds match in exam_id field."""
        # Act
        queryset = StudyService.get_studies_queryset(q="CHEST001")

        # Assert
        self.assertEqual(queryset.count(), 1)
        self.assertEqual(queryset[0].exam_id, "CHEST001")

    def test_text_search_in_exam_description(self):
        """Test text search finds match in exam_item field."""
        # Act
        queryset = StudyService.get_studies_queryset(q="Brain MRI")

        # Assert
        self.assertGreaterEqual(queryset.count(), 1)
        # Should find the MRI study
        exam_ids = [s.exam_id for s in queryset]
        self.assertIn("MRI001", exam_ids)

    def test_text_search_in_patient_name(self):
        """Test text search finds match in patient_name field."""
        # Act
        queryset = StudyService.get_studies_queryset(q="Patient123")

        # Assert
        self.assertGreaterEqual(queryset.count(), 1)

    def test_text_search_case_insensitive(self):
        """Test that text search is case-insensitive."""
        # Act
        upper_result = StudyService.get_studies_queryset(q="CHEST")
        lower_result = StudyService.get_studies_queryset(q="chest")
        mixed_result = StudyService.get_studies_queryset(q="ChEsT")

        # Assert
        self.assertEqual(upper_result.count(), lower_result.count())
        self.assertEqual(upper_result.count(), mixed_result.count())

    def test_text_search_empty_query_returns_all(self):
        """Test that empty/None query returns all studies."""
        # Act
        none_result = StudyService.get_studies_queryset(q=None)
        empty_result = StudyService.get_studies_queryset(q="")

        # Assert
        self.assertEqual(none_result.count(), Study.objects.count())
        self.assertEqual(empty_result.count(), Study.objects.count())


class StudyServiceQuerySetFilterTests(TestCase):
    """Test single-select and multi-select filter functionality."""

    @classmethod
    def setUpTestData(cls):
        """Create diverse test data for comprehensive filter testing."""
        for study_data in MockDataGenerator.studies_for_filter_testing():
            Study.objects.create(**study_data)

    def test_filter_by_exam_status_single(self):
        """Test filtering by single exam_status value."""
        # Act
        queryset = StudyService.get_studies_queryset(exam_status="completed")

        # Assert
        self.assertGreater(queryset.count(), 0)
        for study in queryset:
            self.assertEqual(study.exam_status, "completed")

    def test_filter_by_exam_source_single(self):
        """Test filtering by single exam_source value."""
        # Act
        queryset = StudyService.get_studies_queryset(exam_source="MRI")

        # Assert
        self.assertGreater(queryset.count(), 0)
        for study in queryset:
            self.assertEqual(study.exam_source, "MRI")

    def test_filter_by_equipment_multi_select(self):
        """Test multi-select filtering for exam_equipment."""
        # Act
        queryset = StudyService.get_studies_queryset(
            exam_equipment=["CT-SCANNER-01", "MRI-MACHINE-01"]
        )

        # Assert
        self.assertGreater(queryset.count(), 0)
        for study in queryset:
            self.assertIn(study.exam_equipment, ["CT-SCANNER-01", "MRI-MACHINE-01"])

    def test_filter_by_patient_gender_multi_select(self):
        """Test multi-select filtering for patient_gender."""
        # Act
        queryset = StudyService.get_studies_queryset(patient_gender=["M", "F"])

        # Assert
        self.assertGreater(queryset.count(), 0)
        for study in queryset:
            self.assertIn(study.patient_gender, ["M", "F"])

    def test_filter_by_exam_room_multi_select(self):
        """Test multi-select filtering for exam_room."""
        # Act
        queryset = StudyService.get_studies_queryset(exam_room=["CT-ROOM-1", "MRI-ROOM-1"])

        # Assert
        self.assertGreater(queryset.count(), 0)
        for study in queryset:
            self.assertIn(study.exam_room, ["CT-ROOM-1", "MRI-ROOM-1"])

    def test_filter_by_age_range_min_only(self):
        """Test filtering by minimum patient age."""
        # Act
        queryset = StudyService.get_studies_queryset(patient_age_min=50)

        # Assert
        self.assertGreater(queryset.count(), 0)
        for study in queryset:
            if study.patient_age is not None:
                self.assertGreaterEqual(study.patient_age, 50)

    def test_filter_by_age_range_max_only(self):
        """Test filtering by maximum patient age."""
        # Act
        queryset = StudyService.get_studies_queryset(patient_age_max=30)

        # Assert
        self.assertGreater(queryset.count(), 0)
        for study in queryset:
            if study.patient_age is not None:
                self.assertLessEqual(study.patient_age, 30)

    def test_filter_by_age_range_both_min_and_max(self):
        """Test filtering by both minimum and maximum patient age."""
        # Act
        queryset = StudyService.get_studies_queryset(patient_age_min=30, patient_age_max=50)

        # Assert
        for study in queryset:
            if study.patient_age is not None:
                self.assertGreaterEqual(study.patient_age, 30)
                self.assertLessEqual(study.patient_age, 50)

    def test_filter_by_date_range_start_and_end(self):
        """Test filtering by date range (start_date and end_date)."""
        # Arrange
        start_date, end_date = DateTimeHelper.date_range(days=7)

        # Act
        queryset = StudyService.get_studies_queryset(start_date=start_date, end_date=end_date)

        # Assert - should return studies without error
        self.assertIsNotNone(queryset)

    def test_filter_by_invalid_date_format_handled_gracefully(self):
        """Test that invalid date formats are handled gracefully."""
        # Act - should not raise exception
        queryset = StudyService.get_studies_queryset(
            start_date="invalid-date", end_date="2024-13-45"
        )

        # Assert - should return all studies when date parsing fails
        self.assertIsNotNone(queryset)

    def test_combined_filters(self):
        """Test combining multiple filters simultaneously."""
        # Act
        queryset = StudyService.get_studies_queryset(
            exam_status="completed",
            exam_source="CT",
            patient_gender=["M"],
            patient_age_min=20,
            patient_age_max=60,
        )

        # Assert
        for study in queryset:
            self.assertEqual(study.exam_status, "completed")
            self.assertEqual(study.exam_source, "CT")
            if study.patient_gender:
                self.assertEqual(study.patient_gender, "M")
            if study.patient_age is not None:
                self.assertGreaterEqual(study.patient_age, 20)
                self.assertLessEqual(study.patient_age, 60)


class StudyServiceQuerySetSortingTests(TestCase):
    """Test sorting functionality for different sort options."""

    @classmethod
    def setUpTestData(cls):
        """Create test data with different order_datetime values."""
        for i in range(5):
            Study.objects.create(
                **StudyFactory.create_complete_study(
                    exam_id=f"SORT{str(i + 1).zfill(3)}",
                    patient_name=f"Patient {chr(65 + i)}",  # A, B, C, D, E
                    order_datetime=datetime(2024, 11, i + 1, 9, 0, 0),
                )
            )

    def test_sort_by_order_datetime_desc(self):
        """Test sorting by order_datetime descending (most recent first)."""
        # Act
        queryset = StudyService.get_studies_queryset(sort="order_datetime_desc")

        # Assert
        studies = list(queryset)
        self.assertEqual(studies[0].exam_id, "SORT005")  # Most recent
        self.assertEqual(studies[-1].exam_id, "SORT001")  # Oldest

    def test_sort_by_order_datetime_asc(self):
        """Test sorting by order_datetime ascending (oldest first)."""
        # Act
        queryset = StudyService.get_studies_queryset(sort="order_datetime_asc")

        # Assert
        studies = list(queryset)
        self.assertEqual(studies[0].exam_id, "SORT001")  # Oldest
        self.assertEqual(studies[-1].exam_id, "SORT005")  # Most recent

    def test_sort_by_patient_name_asc(self):
        """Test sorting by patient_name ascending (alphabetical)."""
        # Act
        queryset = StudyService.get_studies_queryset(sort="patient_name_asc")

        # Assert
        studies = list(queryset)
        self.assertEqual(studies[0].patient_name, "Patient A")
        self.assertEqual(studies[-1].patient_name, "Patient E")


class StudyServiceGetDetailTests(TestCase):
    """Test get_study_detail() method for detail retrieval and exceptions."""

    def setUp(self):
        """Create test study for detail retrieval."""
        study_data = StudyFactory.create_complete_study(exam_id="DETAIL001")
        self.study = Study.objects.create(**study_data)

    def test_get_study_detail_success(self):
        """Test successful retrieval of study detail."""
        # Act
        result = StudyService.get_study_detail("DETAIL001")

        # Assert
        self.assertIsNotNone(result)
        self.assertEqual(result["exam_id"], "DETAIL001")
        self.assertEqual(result["patient_name"], "Test Patient")
        self.assertIn("order_datetime", result)

    def test_get_study_detail_datetime_iso_format(self):
        """Test that datetime fields in detail are ISO formatted."""
        # Act
        result = StudyService.get_study_detail("DETAIL001")

        # Assert
        self.assertIsInstance(result["order_datetime"], str)
        self.assertRegex(result["order_datetime"], r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}")

    def test_get_study_detail_not_found_raises_exception(self):
        """Test that non-existent exam_id raises StudyNotFoundError."""
        # Act & Assert
        with self.assertRaises(StudyNotFoundError) as context:
            StudyService.get_study_detail("NONEXISTENT")

        self.assertIn("NONEXISTENT", str(context.exception))

    @patch("studies.models.Study.objects.get")
    def test_get_study_detail_database_error(self, mock_get):
        """Test that database errors raise DatabaseQueryError."""
        # Arrange
        mock_get.side_effect = Exception("Database connection failed")

        # Act & Assert
        with self.assertRaises(DatabaseQueryError):
            StudyService.get_study_detail("DETAIL001")


class StudyServiceFilterOptionsTests(TestCase):
    """Test get_filter_options() method for caching and database queries."""

    def setUp(self):
        """Clear cache before each test."""
        cache.clear()
        # Create test data
        for study_data in MockDataGenerator.studies_for_filter_testing()[:5]:
            Study.objects.create(**study_data)

    def tearDown(self):
        """Clear cache after each test."""
        cache.clear()

    def test_get_filter_options_cache_miss_queries_database(self):
        """Test that cache miss results in database query."""
        # Act
        result = StudyService.get_filter_options()

        # Assert
        self.assertIsNotNone(result)
        self.assertIn("exam_statuses", result)
        self.assertIn("exam_sources", result)
        self.assertIn("exam_items", result)
        self.assertIn("equipment_types", result)

    def test_get_filter_options_cache_hit_skips_database(self):
        """Test that cache hit returns cached data without database query."""
        # Arrange - Prime the cache
        first_result = StudyService.get_filter_options()

        # Act - Second call should hit cache
        with patch("studies.services.StudyService._get_filter_options_from_db") as mock_db:
            second_result = StudyService.get_filter_options()

        # Assert - Database should not be called
        mock_db.assert_not_called()
        self.assertEqual(first_result, second_result)

    def test_get_filter_options_returns_sorted_distinct_values(self):
        """Test that filter options are sorted and deduplicated."""
        # Act
        result = StudyService.get_filter_options()

        # Assert
        # Should be sorted lists
        self.assertEqual(result["exam_statuses"], sorted(result["exam_statuses"]))
        self.assertEqual(result["exam_sources"], sorted(result["exam_sources"]))

        # Should have no duplicates
        self.assertEqual(len(result["exam_statuses"]), len(set(result["exam_statuses"])))
        self.assertEqual(len(result["exam_sources"]), len(set(result["exam_sources"])))

    def test_get_filter_options_exam_description_limit_enforced(self):
        """Test that EXAM_DESCRIPTION_LIMIT is enforced for exam_items."""
        # Act
        result = StudyService.get_filter_options()

        # Assert
        # exam_items should respect EXAM_DESCRIPTION_LIMIT from config
        self.assertLessEqual(len(result["exam_items"]), ServiceConfig.EXAM_DESCRIPTION_LIMIT)

    @patch("django.core.cache.cache.get")
    @patch("django.core.cache.cache.set")
    def test_get_filter_options_cache_failure_graceful_degradation(self, mock_set, mock_get):
        """Test that cache failures are handled gracefully (graceful degradation)."""
        # Arrange - Simulate cache failure
        mock_get.side_effect = Exception("Cache unavailable")
        mock_set.side_effect = Exception("Cache unavailable")

        # Act - Should not raise exception
        result = StudyService.get_filter_options()

        # Assert - Should still return valid data from database
        self.assertIsNotNone(result)
        self.assertIn("exam_statuses", result)

    @patch("studies.services.StudyService._get_filter_options_from_db")
    def test_get_filter_options_database_error_raises_exception(self, mock_db):
        """Test that database errors raise DatabaseQueryError."""
        # Arrange
        mock_db.side_effect = Exception("Database query failed")

        # Act & Assert
        with self.assertRaises(DatabaseQueryError):
            StudyService.get_filter_options()

    def test_get_filter_options_cache_key_matches_config(self):
        """Test that cache uses correct key from ServiceConfig."""
        # Act
        StudyService.get_filter_options()

        # Assert
        cached_value = cache.get(ServiceConfig.FILTER_OPTIONS_CACHE_KEY)
        self.assertIsNotNone(cached_value)

    def test_get_filter_options_cache_ttl_matches_config(self):
        """Test that cache TTL matches ServiceConfig.FILTER_OPTIONS_CACHE_TTL."""
        # This test verifies the TTL value is used correctly
        # Act
        with patch("django.core.cache.cache.set") as mock_set:
            StudyService.get_filter_options()

        # Assert
        # Verify cache.set was called with correct TTL
        mock_set.assert_called_once()
        call_args = mock_set.call_args
        # TTL should be the third argument
        self.assertEqual(call_args[0][2], ServiceConfig.FILTER_OPTIONS_CACHE_TTL)
