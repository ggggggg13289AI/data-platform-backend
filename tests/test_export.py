"""
Tests for export functionality.

Tests CSV and Excel export with various filters and edge cases.
Follows pragmatic testing - focuses on actual user scenarios.
"""

from datetime import datetime
from io import BytesIO
from unittest.mock import patch

import pandas as pd
from django.test import TestCase
from django.test.client import Client
from django.utils import timezone

from common.export_service import ExportConfig, ExportService
from study.models import Study


class ExportServiceTests(TestCase):
    """Test export service methods."""

    def setUp(self):
        """Create test data."""
        # Create sample studies
        Study.objects.create(
            exam_id='TEST001',
            medical_record_no='MR001',
            patient_name='John Doe',
            patient_gender='M',
            patient_age=45,
            exam_status='completed',
            exam_source='CT',
            exam_description='Chest CT',
            exam_room='Room 1',
            exam_equipment='Siemens CT',
            order_datetime=timezone.make_aware(datetime(2025, 1, 1, 10, 0, 0)),
            certified_physician='Dr. Smith'
        )

        Study.objects.create(
            exam_id='TEST002',
            medical_record_no='MR002',
            patient_name='Jane Smith',
            patient_gender='F',
            patient_age=32,
            exam_status='pending',
            exam_source='MRI',
            exam_description='Brain MRI',
            exam_room='Room 2',
            exam_equipment='GE MRI',
            order_datetime=timezone.make_aware(datetime(2025, 1, 2, 14, 30, 0)),
            certified_physician='Dr. Johnson'
        )

    def test_prepare_export_data(self):
        """Test data preparation for export."""
        queryset = Study.objects.all().order_by('exam_id')
        export_data = ExportService.prepare_export_data(queryset)

        self.assertEqual(len(export_data), 2)
        self.assertEqual(export_data[0]['exam_id'], 'TEST001')
        self.assertEqual(export_data[0]['patient_name'], 'John Doe')
        self.assertEqual(export_data[1]['exam_id'], 'TEST002')
        self.assertEqual(export_data[1]['patient_name'], 'Jane Smith')

    def test_patient_birth_date_export(self):
        """Test that patient_birth_date (CharField) exports correctly without calling .isoformat()."""
        # Create a study with patient_birth_date value
        Study.objects.create(
            exam_id='BIRTHDATE001',
            medical_record_no='MR_BD001',
            patient_name='Birth Date Test',
            patient_birth_date='1990-05-15',  # String value, not date object
            patient_gender='M',
            patient_age=34,
            exam_status='completed',
            exam_source='CT',
            exam_description='Birth Date Test CT',
            exam_room='Room 1',
            exam_equipment='Test Equipment',
            equipment_type='CT Scanner',
            order_datetime=timezone.make_aware(datetime(2025, 1, 1, 10, 0, 0)),
            certified_physician='Dr. Test'
        )

        queryset = Study.objects.filter(exam_id='BIRTHDATE001')
        export_data = ExportService.prepare_export_data(queryset)

        # Verify the birth_date is correctly exported as string
        self.assertEqual(len(export_data), 1)
        self.assertEqual(export_data[0]['patient_birth_date'], '1990-05-15')
        self.assertIsInstance(export_data[0]['patient_birth_date'], str)

        # Test CSV export with birth date
        csv_content = ExportService.export_to_csv(queryset)
        df = pd.read_csv(BytesIO(csv_content))
        self.assertEqual(len(df), 1)
        self.assertEqual(df.iloc[0]['patient_birth_date'], '1990-05-15')

        # Test Excel export with birth date
        excel_content = ExportService.export_to_excel(queryset)
        df_excel = pd.read_excel(BytesIO(excel_content), sheet_name='Studies Export')
        self.assertEqual(len(df_excel), 1)
        self.assertEqual(df_excel.iloc[0]['patient_birth_date'], '1990-05-15')

    def test_export_to_csv(self):
        """Test CSV export generation."""
        queryset = Study.objects.all().order_by('exam_id')
        csv_content = ExportService.export_to_csv(queryset)

        # Verify it's bytes
        self.assertIsInstance(csv_content, bytes)

        # Parse CSV to verify content
        df = pd.read_csv(BytesIO(csv_content))

        # Check headers
        self.assertIn('exam_id', df.columns)
        self.assertIn('patient_name', df.columns)
        self.assertIn('exam_status', df.columns)

        # Check data
        self.assertEqual(len(df), 2)
        self.assertEqual(df.iloc[0]['exam_id'], 'TEST001')
        self.assertEqual(df.iloc[1]['exam_id'], 'TEST002')

    def test_export_to_excel(self):
        """Test Excel export generation."""
        queryset = Study.objects.all().order_by('exam_id')
        excel_content = ExportService.export_to_excel(queryset)

        # Verify it's bytes
        self.assertIsInstance(excel_content, bytes)

        # Parse Excel to verify content
        df = pd.read_excel(BytesIO(excel_content), sheet_name='Studies Export')

        # Check headers
        self.assertIn('exam_id', df.columns)
        self.assertIn('patient_name', df.columns)
        self.assertIn('exam_status', df.columns)

        # Check data
        self.assertEqual(len(df), 2)
        self.assertEqual(df.iloc[0]['exam_id'], 'TEST001')
        self.assertEqual(df.iloc[1]['exam_id'], 'TEST002')

    def test_empty_queryset_export(self):
        """Test export with empty queryset."""
        queryset = Study.objects.filter(exam_id='NONEXISTENT')

        # Test CSV
        csv_content = ExportService.export_to_csv(queryset)
        df_csv = pd.read_csv(BytesIO(csv_content))
        self.assertEqual(len(df_csv), 0)
        self.assertIn('exam_id', df_csv.columns)  # Headers should still exist

        # Test Excel
        excel_content = ExportService.export_to_excel(queryset)
        df_excel = pd.read_excel(BytesIO(excel_content))
        self.assertEqual(len(df_excel), 0)
        self.assertIn('exam_id', df_excel.columns)  # Headers should still exist

    def test_generate_export_filename(self):
        """Test filename generation."""
        # Test CSV filename
        csv_filename = ExportService.generate_export_filename('csv')
        self.assertTrue(csv_filename.startswith('studies_export_'))
        self.assertTrue(csv_filename.endswith('.csv'))

        # Test Excel filename
        xlsx_filename = ExportService.generate_export_filename('xlsx')
        self.assertTrue(xlsx_filename.startswith('studies_export_'))
        self.assertTrue(xlsx_filename.endswith('.xlsx'))

    def test_get_content_type(self):
        """Test content type determination."""
        self.assertEqual(
            ExportService.get_content_type('csv'),
            'text/csv; charset=utf-8'
        )
        self.assertEqual(
            ExportService.get_content_type('xlsx'),
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )


class ExportAPITests(TestCase):
    """Test export API endpoint."""

    def setUp(self):
        """Set up test client and data."""
        self.client = Client()

        # Create test data
        Study.objects.create(
            exam_id='API001',
            medical_record_no='MR001',
            patient_name='Test Patient',
            patient_gender='M',
            patient_age=30,
            exam_status='completed',
            exam_source='CT',
            exam_description='Test CT',
            order_datetime=timezone.make_aware(datetime(2025, 1, 1, 10, 0, 0))
        )

    def test_export_csv_endpoint(self):
        """Test CSV export via API endpoint."""
        response = self.client.get('/api/v1/studies/export?format=csv')

        # Check response status
        self.assertEqual(response.status_code, 200)

        # Check content type
        self.assertEqual(response['Content-Type'], 'text/csv; charset=utf-8')

        # Check Content-Disposition header
        self.assertIn('Content-Disposition', response)
        self.assertIn('attachment', response['Content-Disposition'])
        self.assertIn('.csv', response['Content-Disposition'])

        # Verify CSV content
        csv_content = response.content
        df = pd.read_csv(BytesIO(csv_content))
        self.assertEqual(len(df), 1)
        self.assertEqual(df.iloc[0]['exam_id'], 'API001')

    def test_export_excel_endpoint(self):
        """Test Excel export via API endpoint."""
        response = self.client.get('/api/v1/studies/export?format=xlsx')

        # Check response status
        self.assertEqual(response.status_code, 200)

        # Check content type
        self.assertEqual(
            response['Content-Type'],
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )

        # Check Content-Disposition header
        self.assertIn('Content-Disposition', response)
        self.assertIn('attachment', response['Content-Disposition'])
        self.assertIn('.xlsx', response['Content-Disposition'])

    def test_export_with_filters(self):
        """Test export with search filters."""
        # Create additional test data
        Study.objects.create(
            exam_id='API002',
            medical_record_no='MR002',
            patient_name='Another Patient',
            patient_gender='F',
            patient_age=25,
            exam_status='pending',
            exam_source='MRI',
            exam_description='Brain MRI',
            order_datetime=timezone.make_aware(datetime(2025, 1, 2, 14, 0, 0))
        )

        # Export only completed studies
        response = self.client.get('/api/v1/studies/export?format=csv&exam_status=completed')

        self.assertEqual(response.status_code, 200)

        # Parse CSV and verify filter
        csv_content = response.content
        df = pd.read_csv(BytesIO(csv_content))
        self.assertEqual(len(df), 1)
        self.assertEqual(df.iloc[0]['exam_status'], 'completed')

    def test_export_with_search_query(self):
        """Test export with text search."""
        response = self.client.get('/api/v1/studies/export?format=csv&q=Test')

        self.assertEqual(response.status_code, 200)

        # Verify content includes searched item
        csv_content = response.content
        df = pd.read_csv(BytesIO(csv_content))
        self.assertGreater(len(df), 0)

    def test_export_with_invalid_format(self):
        """Test export with invalid format defaults to CSV."""
        response = self.client.get('/api/v1/studies/export?format=invalid')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/csv; charset=utf-8')

    def test_export_with_array_parameters(self):
        """Test export with array parameters (bracket notation)."""
        # Create studies with different genders
        Study.objects.create(
            exam_id='API003',
            medical_record_no='MR003',
            patient_name='Female Patient',
            patient_gender='F',
            patient_age=40,
            exam_status='completed',
            order_datetime=timezone.make_aware(datetime(2025, 1, 3, 10, 0, 0))
        )

        # Test with bracket notation (frontend format)
        response = self.client.get(
            '/api/v1/studies/export?format=csv&patient_gender[]=F'
        )

        self.assertEqual(response.status_code, 200)

        # Verify only female patients exported
        csv_content = response.content
        df = pd.read_csv(BytesIO(csv_content))
        for _, row in df.iterrows():
            if pd.notna(row['patient_gender']):
                self.assertEqual(row['patient_gender'], 'F')

    @patch('studies.export_service.ExportConfig.MAX_EXPORT_RECORDS', 2)
    def test_export_limit(self):
        """Test export record limit."""
        # Create more studies than limit
        for i in range(5):
            Study.objects.create(
                exam_id=f'LIMIT{i:03d}',
                medical_record_no=f'MR{i:03d}',
                patient_name=f'Patient {i}',
                order_datetime=timezone.make_aware(datetime(2025, 1, i+1, 10, 0, 0))
            )

        response = self.client.get('/api/v1/studies/export?format=csv')
        self.assertEqual(response.status_code, 200)

        # Verify export is limited
        csv_content = response.content
        df = pd.read_csv(BytesIO(csv_content))
        self.assertLessEqual(len(df), 2)  # Should be limited to 2 records


class ExportConfigTests(TestCase):
    """Test export configuration."""

    def test_config_values(self):
        """Test configuration constants are set correctly."""
        self.assertEqual(ExportConfig.MAX_EXPORT_RECORDS, 10000)
        self.assertEqual(ExportConfig.EXPORT_BATCH_SIZE, 1000)
        self.assertEqual(ExportConfig.CSV_ENCODING, 'utf-8-sig')
        self.assertEqual(ExportConfig.EXCEL_ENGINE, 'openpyxl')
        self.assertEqual(ExportConfig.DEFAULT_EXPORT_FORMAT, 'csv')
        self.assertIn('csv', ExportConfig.ALLOWED_EXPORT_FORMATS)
        self.assertIn('xlsx', ExportConfig.ALLOWED_EXPORT_FORMATS)

    def test_csv_columns_defined(self):
        """Test CSV columns are properly defined."""
        expected_columns = [
            'exam_id', 'medical_record_no', 'patient_name',
            'exam_status', 'exam_source'
        ]
        for col in expected_columns:
            self.assertIn(col, ExportConfig.CSV_COLUMNS)
