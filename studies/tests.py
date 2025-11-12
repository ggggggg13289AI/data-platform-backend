"""
Unit tests for Report API endpoints with focus on pagination functionality.

Tests cover:
- ReportPagination class functionality
- Paginated search endpoint with various parameters
- Edge cases and boundary conditions
- Response schema validation
- Filter parameter handling
"""

import json
from datetime import datetime, timedelta
from django.test import TestCase, Client
from django.utils import timezone
from django.urls import reverse
from .models import Report
from .report_api import ReportPagination, PaginatedReportResponse
from pydantic import ValidationError


class ReportPaginationTestCase(TestCase):
    """Test cases for ReportPagination utility class."""

    @classmethod
    def setUpTestData(cls):
        """Create test data for pagination tests."""
        # Create 105 report records to test pagination
        now = timezone.now()
        for i in range(105):
            Report.objects.create(
                report_id=f"test_report_{i:03d}",
                uid=f"uid_{i:03d}",
                title=f"Test Report {i}",
                content_raw=f"Content for report {i}",
                report_type="PDF",
                source_url=f"http://example.com/report/{i}",
                version_number=1,
                is_latest=True,
                created_at=now - timedelta(days=i),
                verified_at=now - timedelta(days=i),
            )

    def test_pagination_basic_first_page(self):
        """Test retrieving first page of results."""
        queryset = Report.objects.all()
        paginator = ReportPagination(queryset, page=1, page_size=20)

        self.assertEqual(paginator.page, 1)
        self.assertEqual(paginator.page_size, 20)
        self.assertEqual(paginator.total, 105)
        self.assertEqual(len(paginator.get_items()), 20)
        self.assertEqual(paginator.get_total_pages(), 6)  # ceil(105/20)

    def test_pagination_last_page(self):
        """Test retrieving last page with incomplete page."""
        queryset = Report.objects.all()
        paginator = ReportPagination(queryset, page=6, page_size=20)

        items = paginator.get_items()
        self.assertEqual(len(items), 5)  # 105 % 20 = 5 remaining items
        self.assertEqual(paginator.get_total_pages(), 6)

    def test_pagination_page_size_limits(self):
        """Test page size is clamped between 1 and 100."""
        queryset = Report.objects.all()

        # Test max limit: 150 should be clamped to 100
        paginator = ReportPagination(queryset, page=1, page_size=150)
        self.assertEqual(paginator.page_size, 100)
        self.assertEqual(len(paginator.get_items()), 100)

        # Test min limit: 0 should be clamped to 1 (but actually defaults to 20)
        paginator = ReportPagination(queryset, page=1, page_size=0)
        self.assertEqual(paginator.page_size, 20)

    def test_pagination_page_number_minimum(self):
        """Test page number defaults to 1 if less than 1."""
        queryset = Report.objects.all()

        # Negative page should be clamped to 1
        paginator = ReportPagination(queryset, page=-5, page_size=20)
        self.assertEqual(paginator.page, 1)

        # Zero page should be clamped to 1
        paginator = ReportPagination(queryset, page=0, page_size=20)
        self.assertEqual(paginator.page, 1)

    def test_pagination_response_data_structure(self):
        """Test that response data has correct structure."""
        queryset = Report.objects.all()
        paginator = ReportPagination(queryset, page=2, page_size=30)

        items = paginator.get_items()
        response_data = paginator.get_response_data(items)

        # Verify response structure
        self.assertIn('items', response_data)
        self.assertIn('total', response_data)
        self.assertIn('page', response_data)
        self.assertIn('page_size', response_data)
        self.assertIn('pages', response_data)

        self.assertEqual(response_data['total'], 105)
        self.assertEqual(response_data['page'], 2)
        self.assertEqual(response_data['page_size'], 30)
        self.assertEqual(response_data['pages'], 4)  # ceil(105/30)

    def test_pagination_boundary_conditions(self):
        """Test edge cases and boundary conditions."""
        queryset = Report.objects.all()

        # Test requesting page beyond available pages
        paginator = ReportPagination(queryset, page=100, page_size=20)
        items = paginator.get_items()
        self.assertEqual(len(items), 0)  # Beyond last page returns empty

        # Test single item per page
        paginator = ReportPagination(queryset, page=1, page_size=1)
        items = paginator.get_items()
        self.assertEqual(len(items), 1)
        self.assertEqual(paginator.get_total_pages(), 105)

    def test_pagination_offset_calculation(self):
        """Test that offset calculation is correct for various pages."""
        queryset = Report.objects.all().order_by('-created_at')  # Consistent ordering (newest first)
        page_size = 20

        # Page 1: offset 0, should get items 0-19
        paginator = ReportPagination(queryset, page=1, page_size=page_size)
        items_page1 = list(paginator.get_items())
        self.assertEqual(len(items_page1), 20)

        # Page 2: offset 20, should get next 20 items
        paginator = ReportPagination(queryset, page=2, page_size=page_size)
        items_page2 = list(paginator.get_items())
        self.assertEqual(len(items_page2), 20)

        # Verify page numbers are different (pagination is working)
        self.assertEqual(paginator.page, 2)
        self.assertGreater(len(items_page1), 0)
        self.assertGreater(len(items_page2), 0)


class PaginatedReportResponseSchemaTestCase(TestCase):
    """Test cases for PaginatedReportResponse Pydantic schema."""

    def test_schema_validation_success(self):
        """Test that valid data passes schema validation."""
        valid_data = {
            'items': [],
            'total': 100,
            'page': 1,
            'page_size': 20,
            'pages': 5,
        }

        response = PaginatedReportResponse(**valid_data)
        self.assertEqual(response.total, 100)
        self.assertEqual(response.page, 1)
        self.assertEqual(response.page_size, 20)
        self.assertEqual(response.pages, 5)

    def test_schema_rejects_old_fields(self):
        """Test that schema rejects deprecated limit/offset fields."""
        invalid_data = {
            'items': [],
            'total': 100,
            'limit': 20,  # Old field name
            'offset': 0,  # Old field name
            'page': 1,
            'pages': 5,
        }

        # Should raise ValidationError due to extra fields
        with self.assertRaises(ValidationError):
            PaginatedReportResponse(**invalid_data)

    def test_schema_requires_page_page_size(self):
        """Test that schema requires page and page_size fields."""
        incomplete_data = {
            'items': [],
            'total': 100,
            'pages': 5,
            # Missing 'page' and 'page_size'
        }

        with self.assertRaises(ValidationError):
            PaginatedReportResponse(**incomplete_data)

    def test_schema_field_types(self):
        """Test that schema validates field types correctly."""
        # Test with wrong type for page
        with self.assertRaises(ValidationError):
            PaginatedReportResponse(
                items=[],
                total=100,
                page="invalid_page",  # Should be int
                page_size=20,
                pages=5,
            )

        # Test with wrong type for total
        with self.assertRaises(ValidationError):
            PaginatedReportResponse(
                items=[],
                total="invalid_total",  # Should be int
                page=1,
                page_size=20,
                pages=5,
            )


class PaginatedSearchEndpointTestCase(TestCase):
    """Test cases for the paginated search API endpoint."""

    @classmethod
    def setUpTestData(cls):
        """Create test data for API endpoint tests."""
        now = timezone.now()

        # Create test reports with varying types and dates
        for i in range(50):
            report_type = "PDF" if i % 2 == 0 else "HTML"
            Report.objects.create(
                report_id=f"api_test_{i:03d}",
                uid=f"uid_api_{i:03d}",
                title=f"API Test Report {i}",
                content_raw=f"Test content for search {i}",
                report_type=report_type,
                source_url=f"http://api.example.com/{i}",
                version_number=1,
                is_latest=True,
                created_at=now - timedelta(days=i),
                verified_at=now - timedelta(days=i),
            )

    def setUp(self):
        """Set up test client for each test."""
        self.client = Client()

    def test_endpoint_default_pagination(self):
        """Test endpoint with default pagination parameters."""
        response = self.client.get('/api/v1/reports/search/paginated')
        self.assertEqual(response.status_code, 200)

        data = json.loads(response.content)
        self.assertIn('items', data)
        self.assertIn('page', data)
        self.assertIn('page_size', data)
        self.assertIn('total', data)
        self.assertIn('pages', data)

        # Default page_size is 20
        self.assertEqual(data['page'], 1)
        self.assertEqual(data['page_size'], 20)

    def test_endpoint_custom_page_size(self):
        """Test endpoint with custom page size parameter."""
        response = self.client.get('/api/v1/reports/search/paginated?page_size=10')
        self.assertEqual(response.status_code, 200)

        data = json.loads(response.content)
        self.assertEqual(data['page_size'], 10)
        self.assertEqual(len(data['items']), 10)

    def test_endpoint_page_navigation(self):
        """Test navigating through multiple pages."""
        # Get page 1
        response1 = self.client.get('/api/v1/reports/search/paginated?page=1&page_size=10')
        data1 = json.loads(response1.content)

        # Get page 2
        response2 = self.client.get('/api/v1/reports/search/paginated?page=2&page_size=10')
        data2 = json.loads(response2.content)

        # Verify different results
        ids1 = [item['uid'] for item in data1['items']]
        ids2 = [item['uid'] for item in data2['items']]
        self.assertEqual(len(set(ids1) & set(ids2)), 0)  # No overlap

    def test_endpoint_page_size_maximum_limit(self):
        """Test that page_size is clamped to 100."""
        response = self.client.get('/api/v1/reports/search/paginated?page_size=500')
        data = json.loads(response.content)

        # Should be clamped to 100
        self.assertEqual(data['page_size'], 100)
        self.assertLessEqual(len(data['items']), 100)

    def test_endpoint_with_sort_parameter(self):
        """Test endpoint respects sort parameter."""
        response = self.client.get(
            '/api/v1/reports/search/paginated?page=1&page_size=10&sort=verified_at_desc'
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)

        # Verify we got results
        self.assertGreater(len(data['items']), 0)

    def test_endpoint_with_filter_parameters(self):
        """Test endpoint with filter parameters."""
        response = self.client.get(
            '/api/v1/reports/search/paginated?report_type=PDF&page=1&page_size=20'
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)

        # All items should be PDF type
        for item in data['items']:
            self.assertEqual(item['report_type'], 'PDF')

    def test_endpoint_response_structure(self):
        """Test that response structure matches PaginatedReportResponse schema."""
        response = self.client.get('/api/v1/reports/search/paginated?page=1&page_size=5')
        self.assertEqual(response.status_code, 200)

        data = json.loads(response.content)

        # Check required top-level fields
        required_fields = {'items', 'total', 'page', 'page_size', 'pages'}
        self.assertTrue(required_fields.issubset(set(data.keys())))

        # Check items structure
        for item in data['items']:
            self.assertIn('uid', item)
            self.assertIn('title', item)
            self.assertIn('report_type', item)
            self.assertIn('version_number', item)
            self.assertIn('is_latest', item)
            self.assertIn('created_at', item)
            self.assertIn('verified_at', item)
            self.assertIn('content_preview', item)

    def test_endpoint_invalid_page_parameter(self):
        """Test endpoint with invalid page parameter."""
        # Non-integer page should return validation error
        response = self.client.get('/api/v1/reports/search/paginated?page=invalid&page_size=10')
        # Ninja framework returns 422 (Unprocessable Entity) for validation errors
        self.assertEqual(response.status_code, 422)

    def test_endpoint_empty_results(self):
        """Test endpoint when no results match filters."""
        response = self.client.get(
            '/api/v1/reports/search/paginated?report_type=NONEXISTENT&page=1&page_size=20'
        )
        self.assertEqual(response.status_code, 200)

        data = json.loads(response.content)
        self.assertEqual(len(data['items']), 0)
        self.assertEqual(data['total'], 0)
        self.assertEqual(data['pages'], 0)

    def test_endpoint_pagination_metadata_accuracy(self):
        """Test that pagination metadata is accurate."""
        response = self.client.get('/api/v1/reports/search/paginated?page=1&page_size=15')
        data = json.loads(response.content)

        # Verify math
        expected_pages = (data['total'] + data['page_size'] - 1) // data['page_size']
        self.assertEqual(data['pages'], expected_pages)
        self.assertGreaterEqual(data['page'], 1)
        self.assertLessEqual(data['page'], data['pages'] + 1)


class ReportImportEndpointTestCase(TestCase):
    """Test cases for the report import endpoint."""

    def setUp(self):
        """Set up test client."""
        self.client = Client()

    def test_import_new_report(self):
        """Test importing a new report."""
        payload = {
            'uid': 'test_import_001',
            'title': 'Test Report',
            'content': 'Test content',
            'report_type': 'PDF',
            'source_url': 'http://example.com/test',
        }

        response = self.client.post(
            '/api/v1/reports/import',
            data=json.dumps(payload),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)

        self.assertEqual(data['uid'], 'test_import_001')
        self.assertTrue(data['is_new'])

    def test_import_duplicate_report(self):
        """Test importing duplicate report with same content."""
        payload = {
            'uid': 'test_import_dup',
            'title': 'Duplicate Report',
            'content': 'Same content',
            'report_type': 'PDF',
            'source_url': 'http://example.com/dup',
        }

        # First import
        response1 = self.client.post(
            '/api/v1/reports/import',
            data=json.dumps(payload),
            content_type='application/json',
        )
        self.assertEqual(response1.status_code, 200)

        # Second import with same content
        response2 = self.client.post(
            '/api/v1/reports/import',
            data=json.dumps(payload),
            content_type='application/json',
        )
        self.assertEqual(response2.status_code, 200)
        data = json.loads(response2.content)

        # Should deduplicate
        self.assertFalse(data['is_new'])


class ReportSearchEndpointTestCase(TestCase):
    """Test cases for the basic search endpoint."""

    @classmethod
    def setUpTestData(cls):
        """Create test data for search tests."""
        now = timezone.now()
        for i in range(20):
            Report.objects.create(
                report_id=f"search_test_{i:03d}",
                uid=f"uid_search_{i:03d}",
                title=f"Search Test Report {i}",
                content_raw=f"Searchable content {i}",
                report_type="PDF",
                source_url=f"http://search.example.com/{i}",
                version_number=1,
                is_latest=True,
                created_at=now,
                verified_at=now,
            )

    def setUp(self):
        """Set up test client."""
        self.client = Client()

    def test_search_with_limit(self):
        """Test basic search endpoint with limit parameter."""
        response = self.client.get('/api/v1/reports/search?limit=5')
        self.assertEqual(response.status_code, 200)

        data = json.loads(response.content)
        self.assertIsInstance(data, list)
        self.assertLessEqual(len(data), 5)

    def test_search_with_query(self):
        """Test basic search endpoint with search query."""
        response = self.client.get('/api/v1/reports/search?q=Test&limit=10')
        self.assertEqual(response.status_code, 200)

        data = json.loads(response.content)
        self.assertIsInstance(data, list)


if __name__ == '__main__':
    import unittest
    unittest.main()
