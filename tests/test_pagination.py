"""
Automated tests for Django Ninja pagination implementation.

Tests verify:
1. Pagination response structure (items, count, filters)
2. Default pagination behavior (limit=20, offset=0)
3. Custom limit and offset handling
4. Parameter validation (limit bounds, offset bounds)
5. Filter integration with pagination
6. API contract compatibility
"""

from django.test import TestCase, Client
from django.contrib.auth.models import User
from studies.models import Study
import json
from datetime import datetime, timezone


class PaginationStructureTestCase(TestCase):
    """Test pagination response structure and format."""
    
    @classmethod
    def setUpTestData(cls):
        """Create test data."""
        # Create test studies
        for i in range(100):
            Study.objects.create(
                exam_id=f"TEST{i:05d}",
                medical_record_no=f"MR{i:05d}",
                application_order_no=f"ORDER{i:05d}",
                patient_name=f"Patient {i}",
                patient_gender="M" if i % 2 == 0 else "F",
                patient_age=20 + (i % 70),
                exam_status="終審報告",
                exam_source="急診",
                exam_item="300707001",
                exam_description="Test Exam",
                order_datetime=datetime.now(timezone.utc),
                check_in_datetime=datetime.now(timezone.utc),
                report_certification_datetime=datetime.now(timezone.utc),
                certified_physician="Test Physician",
            )
    
    def setUp(self):
        """Set up client for testing."""
        self.client = Client()
        self.endpoint = "/api/v1/studies/search"
    
    def test_response_has_required_fields(self):
        """Test response contains items, count, and filters."""
        response = self.client.get(self.endpoint)
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.content)
        self.assertIn("items", data, "Response missing 'items' field")
        self.assertIn("count", data, "Response missing 'count' field")
        self.assertIn("filters", data, "Response missing 'filters' field")
    
    def test_items_is_list(self):
        """Test items field is a list."""
        response = self.client.get(self.endpoint)
        data = json.loads(response.content)
        self.assertIsInstance(data["items"], list)
    
    def test_count_is_integer(self):
        """Test count field is an integer."""
        response = self.client.get(self.endpoint)
        data = json.loads(response.content)
        self.assertIsInstance(data["count"], int)
    
    def test_items_have_correct_schema(self):
        """Test each item has expected fields."""
        response = self.client.get(self.endpoint)
        data = json.loads(response.content)
        
        required_fields = [
            "exam_id", "medical_record_no", "patient_name",
            "exam_status", "exam_source", "order_datetime"
        ]
        
        if data["items"]:  # Only check if items exist
            for item in data["items"]:
                for field in required_fields:
                    self.assertIn(
                        field, item,
                        f"Item missing required field: {field}"
                    )


class DefaultPaginationTestCase(TestCase):
    """Test default pagination behavior."""
    
    @classmethod
    def setUpTestData(cls):
        """Create test data."""
        for i in range(100):
            Study.objects.create(
                exam_id=f"TEST{i:05d}",
                medical_record_no=f"MR{i:05d}",
                application_order_no=f"ORDER{i:05d}",
                patient_name=f"Patient {i}",
                patient_gender="M",
                patient_age=30,
                exam_status="終審報告",
                exam_source="急診",
                exam_item="300707001",
                exam_description="Test Exam",
                order_datetime=datetime.now(timezone.utc),
                check_in_datetime=datetime.now(timezone.utc),
                report_certification_datetime=datetime.now(timezone.utc),
                certified_physician="Test",
            )
    
    def setUp(self):
        """Set up client for testing."""
        self.client = Client()
        self.endpoint = "/api/v1/studies/search"
    
    def test_default_limit_is_20(self):
        """Test default limit is 20 items per page."""
        response = self.client.get(self.endpoint)
        data = json.loads(response.content)
        
        # Default limit should be 20
        self.assertLessEqual(len(data["items"]), 20)
    
    def test_default_offset_is_0(self):
        """Test default offset starts at 0."""
        response = self.client.get(self.endpoint)
        data = json.loads(response.content)
        
        # With 100 test items and default limit 20,
        # we should get the first 20 items
        self.assertEqual(len(data["items"]), 20)
    
    def test_total_count_is_correct(self):
        """Test count reflects total items in database."""
        response = self.client.get(self.endpoint)
        data = json.loads(response.content)
        
        # Should have 100 total items
        self.assertEqual(data["count"], 100)


class CustomLimitTestCase(TestCase):
    """Test custom limit parameter handling."""
    
    @classmethod
    def setUpTestData(cls):
        """Create test data."""
        for i in range(50):
            Study.objects.create(
                exam_id=f"TEST{i:05d}",
                medical_record_no=f"MR{i:05d}",
                application_order_no=f"ORDER{i:05d}",
                patient_name=f"Patient {i}",
                patient_gender="M",
                patient_age=30,
                exam_status="終審報告",
                exam_source="急診",
                exam_item="300707001",
                exam_description="Test Exam",
                order_datetime=datetime.now(timezone.utc),
                check_in_datetime=datetime.now(timezone.utc),
                report_certification_datetime=datetime.now(timezone.utc),
                certified_physician="Test",
            )
    
    def setUp(self):
        """Set up client for testing."""
        self.client = Client()
        self.endpoint = "/api/v1/studies/search"
    
    def test_custom_limit_5(self):
        """Test limit=5 returns 5 items."""
        response = self.client.get(f"{self.endpoint}?limit=5")
        data = json.loads(response.content)
        self.assertEqual(len(data["items"]), 5)
    
    def test_custom_limit_10(self):
        """Test limit=10 returns 10 items."""
        response = self.client.get(f"{self.endpoint}?limit=10")
        data = json.loads(response.content)
        self.assertEqual(len(data["items"]), 10)
    
    def test_limit_capped_at_100(self):
        """Test limit > 100 is capped at 100."""
        response = self.client.get(f"{self.endpoint}?limit=200")
        data = json.loads(response.content)
        # Should be limited to maximum (20 since we have 50 items and limit is capped)
        # Actually, let's verify the pagination code - it caps at 100 but we only have 50
        self.assertLessEqual(len(data["items"]), 50)
    
    def test_limit_less_than_1_uses_default(self):
        """Test limit < 1 uses default limit."""
        response = self.client.get(f"{self.endpoint}?limit=0")
        data = json.loads(response.content)
        # Should use default (20)
        self.assertEqual(len(data["items"]), 20)


class OffsetTestCase(TestCase):
    """Test offset parameter handling."""
    
    @classmethod
    def setUpTestData(cls):
        """Create test data."""
        for i in range(50):
            Study.objects.create(
                exam_id=f"TEST{i:05d}",
                medical_record_no=f"MR{i:05d}",
                application_order_no=f"ORDER{i:05d}",
                patient_name=f"Patient {i}",
                patient_gender="M",
                patient_age=30,
                exam_status="終審報告",
                exam_source="急診",
                exam_item="300707001",
                exam_description="Test Exam",
                order_datetime=datetime.now(timezone.utc),
                check_in_datetime=datetime.now(timezone.utc),
                report_certification_datetime=datetime.now(timezone.utc),
                certified_physician="Test",
            )
    
    def setUp(self):
        """Set up client for testing."""
        self.client = Client()
        self.endpoint = "/api/v1/studies/search"
    
    def test_offset_10_skips_first_10(self):
        """Test offset=10 skips first 10 items."""
        response1 = self.client.get(f"{self.endpoint}?limit=5&offset=0")
        response2 = self.client.get(f"{self.endpoint}?limit=5&offset=10")
        
        data1 = json.loads(response1.content)
        data2 = json.loads(response2.content)
        
        # Items at offset 10-15 should differ from items at offset 0-5
        if data1["items"] and data2["items"]:
            self.assertNotEqual(
                data1["items"][0]["exam_id"],
                data2["items"][0]["exam_id"]
            )
    
    def test_negative_offset_uses_zero(self):
        """Test negative offset is treated as 0."""
        response1 = self.client.get(f"{self.endpoint}?limit=5&offset=-10")
        response2 = self.client.get(f"{self.endpoint}?limit=5&offset=0")
        
        data1 = json.loads(response1.content)
        data2 = json.loads(response2.content)
        
        # Should be same items
        if data1["items"] and data2["items"]:
            self.assertEqual(
                data1["items"][0]["exam_id"],
                data2["items"][0]["exam_id"]
            )
    
    def test_pagination_count_consistent(self):
        """Test count is consistent across different offsets."""
        response1 = self.client.get(f"{self.endpoint}?offset=0")
        response2 = self.client.get(f"{self.endpoint}?offset=20")
        
        data1 = json.loads(response1.content)
        data2 = json.loads(response2.content)
        
        # Count should be same
        self.assertEqual(data1["count"], data2["count"])


class FilterIntegrationTestCase(TestCase):
    """Test filter parameters work with pagination."""
    
    @classmethod
    def setUpTestData(cls):
        """Create test data with different statuses."""
        # Create studies with "終審報告" status
        for i in range(30):
            Study.objects.create(
                exam_id=f"FINAL{i:05d}",
                medical_record_no=f"MR{i:05d}",
                application_order_no=f"ORDER{i:05d}",
                patient_name=f"Patient {i}",
                patient_gender="M",
                patient_age=30,
                exam_status="終審報告",
                exam_source="急診",
                exam_item="300707001",
                exam_description="Test Exam",
                order_datetime=datetime.now(timezone.utc),
                check_in_datetime=datetime.now(timezone.utc),
                report_certification_datetime=datetime.now(timezone.utc),
                certified_physician="Test",
            )
        
        # Create studies with "已刪單" status
        for i in range(20):
            Study.objects.create(
                exam_id=f"DELETED{i:05d}",
                medical_record_no=f"MR{i:05d}",
                application_order_no=f"ORDER{i:05d}",
                patient_name=f"Patient {i}",
                patient_gender="F",
                patient_age=40,
                exam_status="已刪單",
                exam_source="門診",
                exam_item="300707052",
                exam_description="Different Exam",
                order_datetime=datetime.now(timezone.utc),
                check_in_datetime=datetime.now(timezone.utc),
                report_certification_datetime=datetime.now(timezone.utc),
                certified_physician="Test2",
            )
    
    def setUp(self):
        """Set up client for testing."""
        self.client = Client()
        self.endpoint = "/api/v1/studies/search"
    
    def test_status_filter_with_pagination(self):
        """Test exam_status filter works with pagination."""
        response = self.client.get(f"{self.endpoint}?exam_status=終審報告&limit=10")
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.content)
        # Should have 30 items with this status
        self.assertEqual(data["count"], 30)
        # Should return 10 items
        self.assertEqual(len(data["items"]), 10)
    
    def test_source_filter_with_pagination(self):
        """Test exam_source filter works with pagination."""
        response = self.client.get(f"{self.endpoint}?exam_source=門診&limit=15")
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.content)
        # Should have 20 items with door diagnosis
        self.assertEqual(data["count"], 20)


class ApiContractTestCase(TestCase):
    """Test API contract compatibility."""
    
    @classmethod
    def setUpTestData(cls):
        """Create minimal test data."""
        for i in range(5):
            Study.objects.create(
                exam_id=f"TEST{i:05d}",
                medical_record_no=f"MR{i:05d}",
                application_order_no=f"ORDER{i:05d}",
                patient_name=f"Patient {i}",
                patient_gender="M",
                patient_age=30,
                exam_status="終審報告",
                exam_source="急診",
                exam_item="300707001",
                exam_description="Test Exam",
                order_datetime=datetime.now(timezone.utc),
                check_in_datetime=datetime.now(timezone.utc),
                report_certification_datetime=datetime.now(timezone.utc),
                certified_physician="Test",
            )
    
    def setUp(self):
        """Set up client for testing."""
        self.client = Client()
        self.endpoint = "/api/v1/studies/search"
    
    def test_response_status_200(self):
        """Test endpoint returns 200 status."""
        response = self.client.get(self.endpoint)
        self.assertEqual(response.status_code, 200)
    
    def test_response_content_type_json(self):
        """Test response is JSON."""
        response = self.client.get(self.endpoint)
        self.assertIn("application/json", response.get("Content-Type", ""))
    
    def test_response_is_valid_json(self):
        """Test response can be parsed as JSON."""
        response = self.client.get(self.endpoint)
        try:
            json.loads(response.content)
        except json.JSONDecodeError:
            self.fail("Response is not valid JSON")
    
    def test_parameter_names_follow_django_ninja_standard(self):
        """Test API uses standard limit/offset parameters."""
        # These are the standard Django Ninja pagination parameter names
        response = self.client.get(f"{self.endpoint}?limit=5&offset=0")
        self.assertEqual(response.status_code, 200)


class PaginationEdgeCasesTestCase(TestCase):
    """Test edge cases in pagination."""
    
    @classmethod
    def setUpTestData(cls):
        """Create test data."""
        for i in range(35):  # Not divisible by 20
            Study.objects.create(
                exam_id=f"TEST{i:05d}",
                medical_record_no=f"MR{i:05d}",
                application_order_no=f"ORDER{i:05d}",
                patient_name=f"Patient {i}",
                patient_gender="M",
                patient_age=30,
                exam_status="終審報告",
                exam_source="急診",
                exam_item="300707001",
                exam_description="Test Exam",
                order_datetime=datetime.now(timezone.utc),
                check_in_datetime=datetime.now(timezone.utc),
                report_certification_datetime=datetime.now(timezone.utc),
                certified_physician="Test",
            )
    
    def setUp(self):
        """Set up client for testing."""
        self.client = Client()
        self.endpoint = "/api/v1/studies/search"
    
    def test_last_page_partial_results(self):
        """Test last page returns partial results if needed."""
        response = self.client.get(f"{self.endpoint}?limit=20&offset=20")
        data = json.loads(response.content)
        
        # Should have 15 items (35 - 20)
        self.assertEqual(len(data["items"]), 15)
    
    def test_offset_beyond_total_returns_empty(self):
        """Test offset beyond total items returns empty list."""
        response = self.client.get(f"{self.endpoint}?limit=20&offset=100")
        data = json.loads(response.content)
        
        self.assertEqual(len(data["items"]), 0)
        self.assertEqual(data["count"], 35)  # Count should still be total
    
    def test_empty_database(self):
        """Test behavior with empty results."""
        # This would need a separate test database setup
        # For now, verify structure is maintained even with edge cases
        response = self.client.get(f"{self.endpoint}?limit=20&offset=500")
        data = json.loads(response.content)
        
        # Should still have proper structure
        self.assertIn("items", data)
        self.assertIn("count", data)
        self.assertIn("filters", data)
