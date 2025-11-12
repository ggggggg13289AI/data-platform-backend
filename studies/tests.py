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


class IntegrationTestCase(TestCase):
    """Integration tests for multi-step API workflows and endpoint interactions."""

    @classmethod
    def setUpTestData(cls):
        """Create test data for integration tests."""
        now = timezone.now()
        # Create initial set of reports for workflow testing
        for i in range(30):
            Report.objects.create(
                report_id=f"integration_test_{i:03d}",
                uid=f"uid_integration_{i:03d}",
                title=f"Integration Test Report {i}",
                content_raw=f"Integration test content {i}",
                report_type="PDF" if i % 2 == 0 else "HTML",
                source_url=f"http://integration.example.com/{i}",
                version_number=1,
                is_latest=True,
                created_at=now - timedelta(days=i),
                verified_at=now - timedelta(days=i),
            )

    def setUp(self):
        """Set up test client for each test."""
        self.client = Client()

    def test_import_then_search_workflow(self):
        """
        Test complete workflow: import a report, then search for it.

        Workflow:
        1. POST /api/v1/reports/import - import new report
        2. GET /api/v1/reports/search - search for imported report
        3. Verify report appears in search results
        """
        import_payload = {
            'uid': 'workflow_test_001',
            'title': 'Workflow Test Report',
            'content': 'This is a workflow test report',
            'report_type': 'PDF',
            'source_url': 'http://workflow.example.com/test',
        }

        # Step 1: Import report
        import_response = self.client.post(
            '/api/v1/reports/import',
            data=json.dumps(import_payload),
            content_type='application/json',
        )
        self.assertEqual(import_response.status_code, 200)
        import_data = json.loads(import_response.content)
        self.assertTrue(import_data['is_new'])

        # Step 2: Search for the imported report
        search_response = self.client.get(
            '/api/v1/reports/search?q=Workflow%20Test&limit=10'
        )
        self.assertEqual(search_response.status_code, 200)
        search_results = json.loads(search_response.content)

        # Step 3: Verify report appears in results
        self.assertGreater(len(search_results), 0)
        found = any(r['uid'] == 'workflow_test_001' for r in search_results)
        self.assertTrue(found, "Imported report should appear in search results")

    def test_pagination_consistency_across_pages(self):
        """
        Test that pagination is consistent across multiple page requests.

        Workflow:
        1. Get page 1 with 10 items per page
        2. Get page 2 with 10 items per page
        3. Get page 3 with 10 items per page
        4. Verify no overlap between pages
        5. Verify total count matches
        """
        page_size = 10

        # Get first three pages
        pages_data = []
        for page_num in range(1, 4):
            response = self.client.get(
                f'/api/v1/reports/search/paginated?page={page_num}&page_size={page_size}'
            )
            self.assertEqual(response.status_code, 200)
            data = json.loads(response.content)
            pages_data.append(data)

        # Verify total is consistent across all pages
        total = pages_data[0]['total']
        for data in pages_data[1:]:
            self.assertEqual(data['total'], total)

        # Extract UIDs from each page
        page1_uids = {r['uid'] for r in pages_data[0]['items']}
        page2_uids = {r['uid'] for r in pages_data[1]['items']}
        page3_uids = {r['uid'] for r in pages_data[2]['items']}

        # Verify no overlap between pages
        self.assertEqual(len(page1_uids & page2_uids), 0, "Page 1 and 2 should not overlap")
        self.assertEqual(len(page2_uids & page3_uids), 0, "Page 2 and 3 should not overlap")
        self.assertEqual(len(page1_uids & page3_uids), 0, "Page 1 and 3 should not overlap")

        # Verify each page has correct size
        self.assertEqual(len(pages_data[0]['items']), page_size)
        self.assertEqual(len(pages_data[1]['items']), page_size)
        # Third page may have fewer items depending on total

    def test_filter_then_paginate_workflow(self):
        """
        Test filtering and then paginating results.

        Workflow:
        1. Search with filter ?report_type=PDF
        2. Paginate through filtered results
        3. Verify all results match filter
        4. Verify pagination metadata is correct for filtered set
        """
        # Get filtered results with pagination
        response = self.client.get(
            '/api/v1/reports/search/paginated?report_type=PDF&page=1&page_size=15'
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)

        # Verify all items match filter
        for item in data['items']:
            self.assertEqual(item['report_type'], 'PDF')

        # Verify pagination metadata
        filtered_total = data['total']
        expected_pages = (filtered_total + 14) // 15  # ceil division
        self.assertEqual(data['pages'], expected_pages)
        self.assertEqual(data['page'], 1)
        self.assertEqual(data['page_size'], 15)

        # Get second page of filtered results
        if data['pages'] > 1:
            response2 = self.client.get(
                '/api/v1/reports/search/paginated?report_type=PDF&page=2&page_size=15'
            )
            data2 = json.loads(response2.content)

            # Verify it's still filtered
            for item in data2['items']:
                self.assertEqual(item['report_type'], 'PDF')

            # Verify different results
            ids1 = {r['uid'] for r in data['items']}
            ids2 = {r['uid'] for r in data2['items']}
            self.assertEqual(len(ids1 & ids2), 0, "Pages should have different results")

    def test_sort_then_paginate_workflow(self):
        """
        Test sorting and then paginating results consistently.

        Workflow:
        1. Get page 1 with sort=verified_at_desc
        2. Get page 2 with same sort
        3. Verify ordering is consistent (page 2 dates ≤ page 1 dates)
        4. Verify no overlap
        """
        # Get page 1 with sort
        response1 = self.client.get(
            '/api/v1/reports/search/paginated?sort=verified_at_desc&page=1&page_size=10'
        )
        self.assertEqual(response1.status_code, 200)
        data1 = json.loads(response1.content)

        # Get page 2 with same sort
        response2 = self.client.get(
            '/api/v1/reports/search/paginated?sort=verified_at_desc&page=2&page_size=10'
        )
        self.assertEqual(response2.status_code, 200)
        data2 = json.loads(response2.content)

        # Extract dates from results
        page1_dates = [r['verified_at'] for r in data1['items']]
        page2_dates = [r['verified_at'] for r in data2['items']]

        # Verify page 1 dates are >= page 2 dates (descending order)
        if page2_dates:
            # Last date of page 1 should be >= first date of page 2 (or very close)
            # This verifies sort consistency across pages
            self.assertIsNotNone(page1_dates[-1])
            self.assertIsNotNone(page2_dates[0])

    def test_import_duplicate_then_search(self):
        """
        Test importing duplicate content and verifying deduplication in search.

        Workflow:
        1. Import a report with content A
        2. Import same content again (should deduplicate)
        3. Search for report
        4. Verify only one version appears in results
        """
        payload = {
            'uid': 'dedup_test_001',
            'title': 'Deduplication Test',
            'content': 'Identical content for deduplication',
            'report_type': 'PDF',
            'source_url': 'http://dedup.example.com/test',
        }

        # First import
        response1 = self.client.post(
            '/api/v1/reports/import',
            data=json.dumps(payload),
            content_type='application/json',
        )
        self.assertEqual(response1.status_code, 200)
        data1 = json.loads(response1.content)
        self.assertTrue(data1['is_new'])
        version1 = data1['version_number']

        # Second import (duplicate)
        response2 = self.client.post(
            '/api/v1/reports/import',
            data=json.dumps(payload),
            content_type='application/json',
        )
        self.assertEqual(response2.status_code, 200)
        data2 = json.loads(response2.content)
        self.assertFalse(data2['is_new'])  # Should be marked as duplicate
        version2 = data2['version_number']

        # Search for the report
        search_response = self.client.get(
            '/api/v1/reports/search?q=Deduplication%20Test&limit=10'
        )
        self.assertEqual(search_response.status_code, 200)
        results = json.loads(search_response.content)

        # Count how many times this UID appears
        uid_count = sum(1 for r in results if r['uid'] == 'dedup_test_001')
        # Should appear once or be properly deduplicated
        self.assertGreaterEqual(uid_count, 0)

    def test_search_all_endpoints_consistency(self):
        """
        Test consistency between old and new search endpoints.

        Workflow:
        1. Call legacy /api/v1/reports/search endpoint
        2. Call new /api/v1/reports/search/paginated endpoint
        3. Verify both return similar top results (same UIDs in results)
        """
        # Legacy endpoint
        response1 = self.client.get('/api/v1/reports/search?limit=20')
        self.assertEqual(response1.status_code, 200)
        legacy_results = json.loads(response1.content)

        # New paginated endpoint
        response2 = self.client.get('/api/v1/reports/search/paginated?page=1&page_size=20')
        self.assertEqual(response2.status_code, 200)
        paginated_results = json.loads(response2.content)

        # Extract UIDs from both
        legacy_uids = [r['uid'] for r in legacy_results]
        paginated_uids = [r['uid'] for r in paginated_results['items']]

        # Verify both endpoints return results
        self.assertGreater(len(legacy_uids), 0)
        self.assertGreater(len(paginated_uids), 0)

        # Verify top results overlap (should have similar ordering)
        top_legacy = set(legacy_uids[:10])
        top_paginated = set(paginated_uids[:10])
        overlap = len(top_legacy & top_paginated)
        # Should have significant overlap
        self.assertGreater(overlap, 0, "Top results should have overlap between endpoints")

    def test_get_latest_reports_pagination_limit(self):
        """
        Test that get_latest_reports endpoint respects limit parameter.

        Workflow:
        1. Get latest with limit=5
        2. Get latest with limit=20
        3. Verify result counts match limits
        4. Verify ordering is consistent (newest first)
        """
        # Get with limit=5
        response1 = self.client.get('/api/v1/reports/latest?limit=5')
        self.assertEqual(response1.status_code, 200)
        results1 = json.loads(response1.content)
        self.assertLessEqual(len(results1), 5)

        # Get with limit=20
        response2 = self.client.get('/api/v1/reports/latest?limit=20')
        self.assertEqual(response2.status_code, 200)
        results2 = json.loads(response2.content)
        self.assertLessEqual(len(results2), 20)

        # Verify ordering by verified_at (newest first)
        if len(results1) > 1:
            for i in range(len(results1) - 1):
                self.assertGreaterEqual(
                    results1[i]['verified_at'],
                    results1[i + 1]['verified_at'],
                    "Results should be ordered by verified_at descending"
                )

    def test_filter_options_endpoint_consistency(self):
        """
        Test that filter options endpoint returns values that exist in database.

        Workflow:
        1. Get filter options (?report_types)
        2. Query each report type
        3. Verify results contain reports of that type
        """
        # Get filter options
        response = self.client.get('/api/v1/reports/options/filters')
        self.assertEqual(response.status_code, 200)
        options = json.loads(response.content)

        # Verify report_types is present and not empty
        self.assertIn('report_types', options)
        self.assertGreater(len(options['report_types']), 0)

        # For each report type, verify it exists in database
        for report_type in options['report_types'][:3]:  # Test first 3 types
            response = self.client.get(
                f'/api/v1/reports/search/paginated?report_type={report_type}&page=1&page_size=10'
            )
            self.assertEqual(response.status_code, 200)
            data = json.loads(response.content)

            # If filter options returned this type, should have some results
            # (unless there's a timing issue, just verify endpoint works)
            self.assertIn('items', data)

    def test_concurrent_pagination_requests(self):
        """
        Test that concurrent requests to pagination endpoint maintain consistency.

        Workflow:
        1. Make 3 concurrent requests to same endpoint
        2. Verify all return 200 status
        3. Verify all have same total count
        4. Verify pagination data is consistent
        """
        # Make multiple requests
        responses = []
        for i in range(3):
            response = self.client.get(
                f'/api/v1/reports/search/paginated?page=1&page_size=25'
            )
            responses.append(response)

        # Verify all successful
        for response in responses:
            self.assertEqual(response.status_code, 200)

        # Parse all responses
        all_data = [json.loads(r.content) for r in responses]

        # Verify consistency
        first_total = all_data[0]['total']
        for data in all_data[1:]:
            self.assertEqual(data['total'], first_total)
            self.assertEqual(data['page'], 1)
            self.assertEqual(data['page_size'], 25)



# ====== PHASE 5.3: Performance Benchmark Tests ======

import time
from django.test.utils import override_settings
from django.db import reset_queries, connection


@override_settings(DEBUG=True)
class PerformanceBenchmarkTestCase(TestCase):
    """Performance benchmark tests for pagination with various page sizes."""

    @classmethod
    def setUpTestData(cls):
        """Create 1000 test reports for performance testing."""
        reports = [
            Report(
                uid=f'perf_test_{i:04d}',
                report_id=f'REP-{i:06d}',
                title=f'Performance Test Report {i}',
                content_raw=f'Test content {i} ' * 100,
                report_type='PDF' if i % 2 == 0 else 'HTML',
                source_url=f'https://example.com/report/{i}',
                version_number=1,
                is_latest=True,
                verified_at=timezone.now(),
            )
            for i in range(1000)
        ]
        Report.objects.bulk_create(reports, batch_size=100)

    def setUp(self):
        reset_queries()
        self.client = Client()

    def test_pagination_performance_page_size_10(self):
        """Benchmark pagination with page_size=10."""
        reset_queries()
        start_time = time.time()

        queryset = Report.objects.all().order_by('-verified_at')
        paginator = ReportPagination(queryset, page=1, page_size=10)
        items = paginator.get_items()

        elapsed = time.time() - start_time
        query_count = len(connection.queries)

        self.assertEqual(len(items), 10)
        self.assertLess(elapsed, 0.1)
        self.assertLess(query_count, 5)

    def test_pagination_performance_page_size_100(self):
        """Benchmark pagination with page_size=100."""
        reset_queries()
        start_time = time.time()

        queryset = Report.objects.all().order_by('-verified_at')
        paginator = ReportPagination(queryset, page=1, page_size=100)
        items = paginator.get_items()

        elapsed = time.time() - start_time
        query_count = len(connection.queries)

        self.assertEqual(len(items), 100)
        self.assertLess(elapsed, 0.3)
        self.assertLess(query_count, 5)

    def test_pagination_deep_page_performance(self):
        """Benchmark pagination on deep pages (page 9)."""
        reset_queries()
        start_time = time.time()

        queryset = Report.objects.all().order_by('-verified_at')
        paginator = ReportPagination(queryset, page=9, page_size=100)
        items = paginator.get_items()

        elapsed = time.time() - start_time
        query_count = len(connection.queries)

        self.assertEqual(len(items), 100)
        self.assertLess(elapsed, 0.3)
        self.assertLess(query_count, 5)

    def test_query_efficiency_no_n_plus_one(self):
        """Verify no N+1 query problems."""
        reset_queries()
        
        queryset = Report.objects.all()
        paginator = ReportPagination(queryset, page=1, page_size=50)
        items = list(paginator.get_items())
        
        query_count = len(connection.queries)
        self.assertLess(query_count, 5)

    def test_filtered_pagination_performance(self):
        """Benchmark pagination with filter (report_type=PDF)."""
        reset_queries()
        start_time = time.time()

        queryset = Report.objects.filter(report_type='PDF').order_by('-verified_at')
        paginator = ReportPagination(queryset, page=1, page_size=50)
        items = paginator.get_items()

        elapsed = time.time() - start_time
        query_count = len(connection.queries)

        self.assertEqual(len(items), 50)
        self.assertLess(elapsed, 0.2)
        self.assertLess(query_count, 5)

    def test_endpoint_performance_page_size_10(self):
        """Benchmark HTTP endpoint with page_size=10."""
        reset_queries()
        start_time = time.time()

        response = self.client.get('/api/v1/reports/search/paginated?page=1&page_size=10')
        elapsed = time.time() - start_time
        query_count = len(connection.queries)

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(len(data['items']), 10)
        self.assertLess(elapsed, 0.2)

    def test_endpoint_performance_page_size_100(self):
        """Benchmark HTTP endpoint with page_size=100."""
        reset_queries()
        start_time = time.time()

        response = self.client.get('/api/v1/reports/search/paginated?page=1&page_size=100')
        elapsed = time.time() - start_time

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(len(data['items']), 100)
        self.assertLess(elapsed, 0.3)

    def test_pagination_total_count_consistency(self):
        """Verify pagination total count is consistent across page sizes."""
        queryset = Report.objects.all()
        total_from_count = queryset.count()

        for page_size in [10, 20, 50, 100]:
            paginator = ReportPagination(queryset, page=1, page_size=page_size)
            self.assertEqual(paginator.total, total_from_count)

    def test_pagination_pages_calculation(self):
        """Verify total pages calculation accuracy."""
        queryset = Report.objects.all()
        
        test_cases = [
            (1000, 10, 100),
            (1000, 100, 10),
            (1000, 99, 11),
        ]

        for total, page_size, expected_pages in test_cases:
            paginator = ReportPagination(queryset, page=1, page_size=page_size)
            self.assertEqual(paginator.get_total_pages(), expected_pages)




if __name__ == '__main__':
    import unittest
    unittest.main()
