"""
Test cases for caching behavior.

Tests cache hit/miss scenarios, graceful degradation, TTL behavior,
and cache key management. Total: 10 test cases.

Test coverage:
- Cache hit/miss scenarios
- Cache failure graceful degradation
- TTL (Time To Live) behavior
- Cache key validation
- Cache data integrity
- Cache warming and invalidation

CRITICAL: Cache failures should NOT break the service - graceful degradation required.
"""

from unittest.mock import patch

from django.core.cache import cache
from django.test import TestCase

from common.config import ServiceConfig
from study.models import Study
from study.services import StudyService
from tests.fixtures.test_data import (
    CacheTestHelper,
    MockDataGenerator,
)


class CacheHitMissTests(TestCase):
    """Test cache hit and miss scenarios for filter options."""

    def setUp(self):
        """Clear cache and create test data before each test."""
        cache.clear()
        # Create minimal test data
        for study_data in MockDataGenerator.studies_for_filter_testing()[:3]:
            Study.objects.create(**study_data)

    def tearDown(self):
        """Clear cache after each test."""
        cache.clear()

    def test_cache_miss_on_first_call(self):
        """Test that first call results in cache miss and database query."""
        # Arrange - Cache is empty
        cache_key = ServiceConfig.FILTER_OPTIONS_CACHE_KEY
        self.assertIsNone(cache.get(cache_key))

        # Act
        with patch("studies.services.StudyService._get_filter_options_from_db") as mock_db:
            mock_db.return_value = CacheTestHelper.mock_filter_options()
            result = StudyService.get_filter_options()

        # Assert - Database should be called on cache miss
        mock_db.assert_called_once()
        self.assertIsNotNone(result)

    def test_cache_hit_on_second_call(self):
        """Test that second call results in cache hit without database query."""
        # Arrange - Prime the cache
        first_result = StudyService.get_filter_options()
        cache_key = ServiceConfig.FILTER_OPTIONS_CACHE_KEY
        self.assertIsNotNone(cache.get(cache_key))

        # Act - Second call should hit cache
        with patch("studies.services.StudyService._get_filter_options_from_db") as mock_db:
            second_result = StudyService.get_filter_options()

        # Assert - Database should NOT be called on cache hit
        mock_db.assert_not_called()
        self.assertEqual(first_result, second_result)

    def test_cache_stores_correct_data_structure(self):
        """Test that cache stores correct FilterOptions data structure."""
        # Act
        StudyService.get_filter_options()

        # Assert
        cache_key = ServiceConfig.FILTER_OPTIONS_CACHE_KEY
        cached_data = cache.get(cache_key)
        self.assertIsNotNone(cached_data)
        self.assertIn("exam_statuses", cached_data)
        self.assertIn("exam_sources", cached_data)
        self.assertIn("exam_items", cached_data)
        self.assertIn("equipment_types", cached_data)


class CacheGracefulDegradationTests(TestCase):
    """Test graceful degradation when cache operations fail."""

    def setUp(self):
        """Create test data."""
        for study_data in MockDataGenerator.studies_for_filter_testing()[:3]:
            Study.objects.create(**study_data)

    def tearDown(self):
        """Clear cache after each test."""
        cache.clear()

    @patch("django.core.cache.cache.get")
    def test_cache_get_failure_falls_back_to_database(self, mock_get):
        """Test that cache.get() failure results in database fallback."""
        # Arrange - Simulate cache.get() failure
        mock_get.side_effect = Exception("Redis connection failed")

        # Act - Should not raise exception
        result = StudyService.get_filter_options()

        # Assert - Should return valid data from database
        self.assertIsNotNone(result)
        self.assertIn("exam_statuses", result)
        self.assertIn("exam_sources", result)

    @patch("django.core.cache.cache.set")
    @patch("django.core.cache.cache.get")
    def test_cache_set_failure_still_returns_data(self, mock_get, mock_set):
        """Test that cache.set() failure doesn't prevent data return."""
        # Arrange - Simulate cache operations failure
        mock_get.return_value = None  # Cache miss
        mock_set.side_effect = Exception("Cache write failed")

        # Act - Should not raise exception
        result = StudyService.get_filter_options()

        # Assert - Should still return valid data from database
        self.assertIsNotNone(result)
        self.assertIn("exam_statuses", result)

    @patch("django.core.cache.cache.get")
    @patch("django.core.cache.cache.set")
    def test_complete_cache_unavailability_still_works(self, mock_set, mock_get):
        """Test that complete cache unavailability results in database-only operation."""
        # Arrange - Simulate complete cache failure
        mock_get.side_effect = Exception("Cache completely unavailable")
        mock_set.side_effect = Exception("Cache completely unavailable")

        # Act - Should not raise exception
        result = StudyService.get_filter_options()

        # Assert - Should still return valid data
        self.assertIsNotNone(result)
        # Verify we got real data from database
        self.assertIsInstance(result["exam_statuses"], list)
        self.assertGreater(len(result["exam_statuses"]), 0)


class CacheTTLTests(TestCase):
    """Test cache Time-To-Live (TTL) behavior."""

    def setUp(self):
        """Clear cache before each test."""
        cache.clear()
        # Create test data
        for study_data in MockDataGenerator.studies_for_filter_testing()[:3]:
            Study.objects.create(**study_data)

    def tearDown(self):
        """Clear cache after each test."""
        cache.clear()

    def test_cache_uses_correct_ttl_from_config(self):
        """Test that cache is set with correct TTL from ServiceConfig."""
        # Act
        with patch("django.core.cache.cache.set") as mock_set:
            StudyService.get_filter_options()

        # Assert - Verify TTL is from config
        mock_set.assert_called_once()
        call_args = mock_set.call_args[0]
        ttl = call_args[2]
        self.assertEqual(ttl, ServiceConfig.FILTER_OPTIONS_CACHE_TTL)
        self.assertEqual(ttl, 24 * 60 * 60)  # 24 hours

    def test_cache_key_matches_config(self):
        """Test that cache uses correct key from ServiceConfig."""
        # Act
        StudyService.get_filter_options()

        # Assert
        cache_key = ServiceConfig.FILTER_OPTIONS_CACHE_KEY
        self.assertEqual(cache_key, "study_filter_options")
        cached_value = cache.get(cache_key)
        self.assertIsNotNone(cached_value)


class CacheInvalidationTests(TestCase):
    """Test cache invalidation and refresh scenarios."""

    def setUp(self):
        """Clear cache and create initial test data."""
        cache.clear()
        # Create initial data
        for study_data in MockDataGenerator.studies_for_filter_testing()[:3]:
            Study.objects.create(**study_data)

    def tearDown(self):
        """Clear cache after each test."""
        cache.clear()

    def test_manual_cache_clear_forces_database_query(self):
        """Test that manually clearing cache forces database query on next call."""
        # Arrange - Prime cache
        StudyService.get_filter_options()
        cache_key = ServiceConfig.FILTER_OPTIONS_CACHE_KEY
        self.assertIsNotNone(cache.get(cache_key))

        # Act - Manually clear cache
        cache.clear()
        self.assertIsNone(cache.get(cache_key))

        # Second call should query database
        with patch("studies.services.StudyService._get_filter_options_from_db") as mock_db:
            mock_db.return_value = CacheTestHelper.mock_filter_options()
            StudyService.get_filter_options()

        # Assert - Database should be called after cache clear
        mock_db.assert_called_once()

    def test_cache_refreshes_after_new_data_added(self):
        """Test that cache can be refreshed to include new data."""
        # Arrange - Get initial filter options (will be cached)
        StudyService.get_filter_options()

        # Act - Clear cache and add new study with different source
        cache.clear()
        Study.objects.create(**MockDataGenerator.study_with_source("PET", "NEWPET001"))

        # Get fresh data (should include new source)
        refreshed_result = StudyService.get_filter_options()
        refreshed_sources = refreshed_result["exam_sources"]

        # Assert - Should include the new source
        self.assertIn("PET", refreshed_sources)
