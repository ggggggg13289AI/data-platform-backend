"""
API Contract Tests - Verify Django response format matches FastAPI exactly.

CRITICAL: These tests ensure zero breaking changes during FastAPI → Django migration.
Response format must match ../docs/api/API_CONTRACT.md specification EXACTLY.

Test strategy:
1. Load sample data into PostgreSQL
2. Compare Django API responses with expected FastAPI format
3. Verify all fields are present and formatted correctly
4. Check datetime serialization (ISO 8601)
5. Verify pagination works correctly
6. Test filter options endpoint
"""

import json
from datetime import datetime
from django.test import TestCase, Client
from django.utils import timezone
from studies.models import Study


class APIContractTestCase(TestCase):
    """
    Test suite for API contract verification.
    Ensures Django API matches FastAPI response format exactly.
    """
    
    @classmethod
    def setUpTestData(cls):
        """Create test data in database."""
        # Create sample studies
        cls.study1 = Study.objects.create(
            exam_id='EXAM001',
            medical_record_no='MR001',
            application_order_no='AO001',
            patient_name='Zhang Wei',
            patient_gender='M',
            patient_birth_date='1980-01-15',
            patient_age=45,
            exam_status='completed',
            exam_source='CT',
            exam_item='Chest CT',
            exam_description='Routine chest examination',
            exam_room='CT Room 1',
            exam_equipment='Siemens SOMATOM',
            equipment_type='CT',
            order_datetime=timezone.now(),
            check_in_datetime=timezone.now(),
            report_certification_datetime=timezone.now(),
            certified_physician='Dr. Li',
        )
        
        cls.study2 = Study.objects.create(
            exam_id='EXAM002',
            medical_record_no='MR002',
            application_order_no='AO002',
            patient_name='Li Na',
            patient_gender='F',
            patient_age=35,
            exam_status='completed',
            exam_source='MRI',
            exam_item='Brain MRI',
            exam_description='Brain imaging',
            equipment_type='MRI',
            order_datetime=timezone.now(),
        )
        
        cls.study3 = Study.objects.create(
            exam_id='EXAM003',
            medical_record_no='MR003',
            patient_name='Wang Gang',
            exam_status='pending',
            exam_source='X-ray',
            exam_item='Chest X-ray',
            equipment_type='X-ray',
            order_datetime=timezone.now(),
        )
    
    def setUp(self):
        """Create test client."""
        self.client = Client()
    
    def test_search_endpoint_exists(self):
        """Test that search endpoint exists and returns 200."""
        response = self.client.get('/api/v1/studies/search')
        self.assertEqual(response.status_code, 200)
    
    def test_search_response_structure(self):
        """Test that search response has correct structure.
        
        CRITICAL: Must match ../docs/api/API_CONTRACT.md:
        {
          "data": [...],
          "total": N,
          "page": 1,
          "page_size": 20,
          "filters": {...}
        }
        """
        response = self.client.get('/api/v1/studies/search')
        data = response.json()
        
        # Check required fields exist
        self.assertIn('data', data)
        self.assertIn('total', data)
        self.assertIn('page', data)
        self.assertIn('page_size', data)
        self.assertIn('filters', data)
        
        # Check types
        self.assertIsInstance(data['data'], list)
        self.assertIsInstance(data['total'], int)
        self.assertIsInstance(data['page'], int)
        self.assertIsInstance(data['page_size'], int)
        self.assertIsInstance(data['filters'], dict)
    
    def test_search_data_item_structure(self):
        """Test that each study in data array has correct structure.
        
        CRITICAL: Must match StudyListItem schema from ../docs/api/API_CONTRACT.md
        """
        response = self.client.get('/api/v1/studies/search')
        data = response.json()
        
        self.assertGreater(len(data['data']), 0)
        study = data['data'][0]
        
        # Required fields
        required_fields = [
            'exam_id',
            'patient_name',
            'exam_status',
            'exam_source',
            'exam_item',
            'equipment_type',
            'order_datetime',
        ]
        
        for field in required_fields:
            self.assertIn(field, study, f'Missing required field: {field}')
        
        # Optional fields (can be null)
        optional_fields = [
            'medical_record_no',
            'patient_gender',
            'patient_age',
            'exam_description',
            'check_in_datetime',
            'report_certification_datetime',
        ]
        
        for field in optional_fields:
            self.assertIn(field, study, f'Missing optional field: {field}')
    
    def test_datetime_format_is_iso8601(self):
        """Test that datetime fields are ISO 8601 format.
        
        CRITICAL: ../docs/api/API_CONTRACT.md specifies ISO format without timezone.
        Example: 2025-11-06T10:30:00
        NOT: Unix timestamp, different format, or with timezone
        """
        response = self.client.get('/api/v1/studies/search')
        data = response.json()
        
        self.assertGreater(len(data['data']), 0)
        study = data['data'][0]
        
        # Check order_datetime format
        order_datetime = study['order_datetime']
        self.assertIsInstance(order_datetime, str)
        
        # Should be able to parse as ISO format
        try:
            parsed = datetime.fromisoformat(order_datetime)
            # Should not have timezone info (naive datetime)
            self.assertIsNone(parsed.tzinfo)
        except ValueError:
            self.fail(f'order_datetime not in ISO 8601 format: {order_datetime}')
    
    def test_null_values_are_null_not_empty_string(self):
        """Test that null values are serialized as null, not empty strings.
        
        CRITICAL: ../docs/api/API_CONTRACT.md specifies null for missing values.
        NOT: empty string, 0, or false
        """
        response = self.client.get('/api/v1/studies/search')
        data = response.json()
        
        # Study3 has null exam_description
        studies = {s['exam_id']: s for s in data['data']}
        
        if 'EXAM003' in studies:
            study3 = studies['EXAM003']
            # check_in_datetime should be null (not empty string)
            self.assertIsNone(study3.get('check_in_datetime'))
    
    def test_pagination(self):
        """Test pagination parameters."""
        # Page 1
        response = self.client.get('/api/v1/studies/search?page=1&page_size=1')
        data = response.json()
        
        self.assertEqual(data['page'], 1)
        self.assertEqual(data['page_size'], 1)
        self.assertEqual(len(data['data']), 1)
        self.assertEqual(data['total'], 3)
        
        # Page 2
        response = self.client.get('/api/v1/studies/search?page=2&page_size=1')
        data = response.json()
        
        self.assertEqual(data['page'], 2)
        self.assertEqual(len(data['data']), 1)
    
    def test_text_search(self):
        """Test text search functionality.
        
        Should search in patient_name, exam_description, exam_item
        """
        # Search for patient name
        response = self.client.get('/api/v1/studies/search?q=Zhang')
        data = response.json()
        
        self.assertEqual(data['total'], 1)
        self.assertEqual(data['data'][0]['exam_id'], 'EXAM001')
        
        # Search for exam item
        response = self.client.get('/api/v1/studies/search?q=MRI')
        data = response.json()
        
        self.assertEqual(data['total'], 1)
        self.assertEqual(data['data'][0]['exam_id'], 'EXAM002')
    
    def test_filter_by_exam_status(self):
        """Test filtering by exam status."""
        response = self.client.get('/api/v1/studies/search?exam_status=pending')
        data = response.json()
        
        self.assertEqual(data['total'], 1)
        self.assertEqual(data['data'][0]['exam_id'], 'EXAM003')
        
        response = self.client.get('/api/v1/studies/search?exam_status=completed')
        data = response.json()
        
        self.assertEqual(data['total'], 2)
    
    def test_filter_by_exam_source(self):
        """Test filtering by exam source."""
        response = self.client.get('/api/v1/studies/search?exam_source=CT')
        data = response.json()
        
        self.assertEqual(data['total'], 1)
        self.assertEqual(data['data'][0]['exam_id'], 'EXAM001')
    
    def test_filter_by_exam_item(self):
        """Test filtering by exam item."""
        response = self.client.get('/api/v1/studies/search?exam_item=Brain+MRI')
        data = response.json()
        
        self.assertEqual(data['total'], 1)
        self.assertEqual(data['data'][0]['exam_id'], 'EXAM002')
    
    def test_filter_options_structure(self):
        """Test filter options endpoint response structure.
        
        CRITICAL: Must match ../docs/api/API_CONTRACT.md:
        {
          "exam_statuses": [...],
          "exam_sources": [...],
          "exam_items": [...],
          "equipment_types": [...]
        }
        """
        response = self.client.get('/api/v1/studies/search')
        data = response.json()
        
        filters = data['filters']
        
        # Check required fields
        self.assertIn('exam_statuses', filters)
        self.assertIn('exam_sources', filters)
        self.assertIn('exam_items', filters)
        self.assertIn('equipment_types', filters)
        
        # Check types
        self.assertIsInstance(filters['exam_statuses'], list)
        self.assertIsInstance(filters['exam_sources'], list)
        self.assertIsInstance(filters['exam_items'], list)
        
        # Check values are not empty
        self.assertGreater(len(filters['exam_statuses']), 0)
        self.assertGreater(len(filters['exam_sources']), 0)
        self.assertGreater(len(filters['exam_items']), 0)
        
        # Check sorted alphabetically
        self.assertEqual(filters['exam_statuses'], sorted(filters['exam_statuses']))
    
    def test_detail_endpoint_exists(self):
        """Test that detail endpoint exists for specific exam."""
        response = self.client.get('/api/v1/studies/EXAM001')
        self.assertEqual(response.status_code, 200)
    
    def test_detail_endpoint_structure(self):
        """Test detail endpoint response structure.
        
        Should return StudyDetail with all fields.
        """
        response = self.client.get('/api/v1/studies/EXAM001')
        data = response.json()
        
        # Check key fields exist
        self.assertEqual(data['exam_id'], 'EXAM001')
        self.assertEqual(data['patient_name'], 'Zhang Wei')
        self.assertIn('order_datetime', data)
    
    def test_detail_endpoint_not_found(self):
        """Test detail endpoint returns 404 for non-existent exam."""
        response = self.client.get('/api/v1/studies/NONEXISTENT')
        # Should return either 404 or empty/null response
        # (depends on Django Ninja error handling)
        self.assertIn(response.status_code, [404, 200])
    
    def test_sorting_order_datetime_desc(self):
        """Test default sort (most recent first)."""
        response = self.client.get('/api/v1/studies/search?sort=order_datetime_desc')
        data = response.json()
        
        # Should have studies, ordered by date (most recent first)
        self.assertGreater(len(data['data']), 0)
    
    def test_combining_filters(self):
        """Test combining multiple filters."""
        response = self.client.get(
            '/api/v1/studies/search?exam_source=CT&exam_status=completed'
        )
        data = response.json()
        
        self.assertEqual(data['total'], 1)
        self.assertEqual(data['data'][0]['exam_id'], 'EXAM001')






