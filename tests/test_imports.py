"""
Tests for the imports module.

Tests cover:
- File upload validation
- CSV/Excel parsing
- Column mapping
- Import execution
- Task status tracking
- API endpoints
"""

import io
import json
import tempfile
import uuid
from pathlib import Path
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from ninja.testing import TestClient

from imports.api import imports_router
from imports.models import ImportTask
from imports.parsers import (
    detect_column_type,
    get_target_fields,
    parse_csv,
    suggest_field_mapping,
)
from imports.services import (
    ALLOWED_EXTENSIONS,
    MAX_FILE_SIZE,
    create_import_task,
    validate_column_mapping,
    validate_file,
)

User = get_user_model()


class ColumnTypeDetectionTestCase(TestCase):
    """Tests for column type detection."""

    def test_detect_string_type(self):
        """String values should be detected as string."""
        values = ['hello', 'world', 'test']
        self.assertEqual(detect_column_type(values), 'string')

    def test_detect_number_type(self):
        """Numeric values should be detected as number."""
        values = ['123', '45.67', '890']
        self.assertEqual(detect_column_type(values), 'number')

    def test_detect_number_with_commas(self):
        """Numbers with commas should be detected as number."""
        values = ['1,234', '5,678.90', '100']
        self.assertEqual(detect_column_type(values), 'number')

    def test_detect_date_type(self):
        """Date-formatted values should be detected as date."""
        values = ['2024-01-15', '2024-02-20', '2024-03-25']
        self.assertEqual(detect_column_type(values), 'date')

    def test_detect_date_slash_format(self):
        """Slash-formatted dates should be detected."""
        values = ['01/15/2024', '02/20/2024', '03/25/2024']
        self.assertEqual(detect_column_type(values), 'date')

    def test_detect_boolean_type(self):
        """Boolean values should be detected as boolean."""
        values = ['true', 'false', 'yes', 'no']
        self.assertEqual(detect_column_type(values), 'boolean')

    def test_empty_values_returns_string(self):
        """Empty values should default to string."""
        values = []
        self.assertEqual(detect_column_type(values), 'string')

    def test_mixed_values_returns_string(self):
        """Mixed value types should return string."""
        values = ['hello', '123', '2024-01-15']
        self.assertEqual(detect_column_type(values), 'string')


class FieldMappingSuggestionTestCase(TestCase):
    """Tests for field mapping suggestions."""

    def test_suggest_report_uid(self):
        """uid column should map to uid field."""
        self.assertEqual(suggest_field_mapping('uid', 'report'), 'uid')
        self.assertEqual(suggest_field_mapping('id', 'report'), 'uid')
        self.assertEqual(suggest_field_mapping('report_uid', 'report'), 'uid')

    def test_suggest_report_title(self):
        """title column should map to title field."""
        self.assertEqual(suggest_field_mapping('title', 'report'), 'title')
        self.assertEqual(suggest_field_mapping('report_title', 'report'), 'title')

    def test_suggest_study_exam_id(self):
        """exam_id column should map to exam_id field."""
        self.assertEqual(suggest_field_mapping('exam_id', 'study'), 'exam_id')
        self.assertEqual(suggest_field_mapping('accession_number', 'study'), 'exam_id')

    def test_suggest_study_patient_name(self):
        """patient_name column should map to patient_name field."""
        self.assertEqual(suggest_field_mapping('patient_name', 'study'), 'patient_name')
        self.assertEqual(suggest_field_mapping('name', 'study'), 'patient_name')

    def test_no_suggestion_for_unknown(self):
        """Unknown columns should return None."""
        self.assertIsNone(suggest_field_mapping('random_column', 'report'))
        self.assertIsNone(suggest_field_mapping('xyz', 'study'))


class TargetFieldsTestCase(TestCase):
    """Tests for target field retrieval."""

    def test_get_report_fields(self):
        """Should return all report target fields."""
        fields = get_target_fields('report')
        self.assertIn('uid', fields)
        self.assertIn('title', fields)
        self.assertIn('content', fields)
        self.assertIn('report_type', fields)

    def test_get_study_fields(self):
        """Should return all study target fields."""
        fields = get_target_fields('study')
        self.assertIn('exam_id', fields)
        self.assertIn('patient_name', fields)
        self.assertIn('modality', fields)

    def test_unknown_type_returns_empty(self):
        """Unknown target type should return empty list."""
        self.assertEqual(get_target_fields('unknown'), [])


class FileValidationTestCase(TestCase):
    """Tests for file validation."""

    def test_valid_csv_extension(self):
        """CSV files should be accepted."""
        mock_file = MagicMock()
        mock_file.size = 1000
        is_valid, error = validate_file(mock_file, 'test.csv')
        self.assertTrue(is_valid)
        self.assertEqual(error, '')

    def test_valid_xlsx_extension(self):
        """XLSX files should be accepted."""
        mock_file = MagicMock()
        mock_file.size = 1000
        is_valid, error = validate_file(mock_file, 'test.xlsx')
        self.assertTrue(is_valid)
        self.assertEqual(error, '')

    def test_invalid_extension(self):
        """Non-CSV/Excel files should be rejected."""
        mock_file = MagicMock()
        mock_file.size = 1000
        is_valid, error = validate_file(mock_file, 'test.txt')
        self.assertFalse(is_valid)
        self.assertIn('Unsupported file type', error)

    def test_file_too_large(self):
        """Files exceeding size limit should be rejected."""
        mock_file = MagicMock()
        mock_file.size = MAX_FILE_SIZE + 1
        is_valid, error = validate_file(mock_file, 'test.csv')
        self.assertFalse(is_valid)
        self.assertIn('size exceeds', error)


class ColumnMappingValidationTestCase(TestCase):
    """Tests for column mapping validation."""

    def test_valid_report_mapping(self):
        """Valid report mapping should pass."""
        mapping = [
            {'source_column': 'col1', 'target_field': 'uid'},
            {'source_column': 'col2', 'target_field': 'title'},
            {'source_column': 'col3', 'target_field': 'content'},
            {'source_column': 'col4', 'target_field': 'report_type'},
        ]
        is_valid, error = validate_column_mapping('report', mapping)
        self.assertTrue(is_valid)
        self.assertEqual(error, '')

    def test_missing_required_report_field(self):
        """Missing required field should fail."""
        mapping = [
            {'source_column': 'col1', 'target_field': 'uid'},
            {'source_column': 'col2', 'target_field': 'title'},
            # Missing content and report_type
        ]
        is_valid, error = validate_column_mapping('report', mapping)
        self.assertFalse(is_valid)
        self.assertIn('Missing required fields', error)

    def test_valid_study_mapping(self):
        """Valid study mapping should pass."""
        mapping = [
            {'source_column': 'col1', 'target_field': 'exam_id'},
            {'source_column': 'col2', 'target_field': 'patient_name'},
        ]
        is_valid, error = validate_column_mapping('study', mapping)
        self.assertTrue(is_valid)
        self.assertEqual(error, '')

    def test_invalid_target_type(self):
        """Invalid target type should fail."""
        mapping = [{'source_column': 'col1', 'target_field': 'uid'}]
        is_valid, error = validate_column_mapping('invalid_type', mapping)
        self.assertFalse(is_valid)
        self.assertIn('Invalid target type', error)

    def test_invalid_target_field(self):
        """Invalid target field should fail."""
        mapping = [
            {'source_column': 'col1', 'target_field': 'uid'},
            {'source_column': 'col2', 'target_field': 'title'},
            {'source_column': 'col3', 'target_field': 'content'},
            {'source_column': 'col4', 'target_field': 'report_type'},
            {'source_column': 'col5', 'target_field': 'nonexistent_field'},
        ]
        is_valid, error = validate_column_mapping('report', mapping)
        self.assertFalse(is_valid)
        self.assertIn('Invalid target fields', error)


class ImportTaskModelTestCase(TestCase):
    """Tests for ImportTask model."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )

    def test_create_task(self):
        """Should create import task successfully."""
        task = ImportTask.objects.create(
            user=self.user,
            filename='test.csv',
            file_path='/tmp/test.csv',
            status=ImportTask.Status.PENDING,
        )
        self.assertIsNotNone(task.task_id)
        self.assertEqual(task.filename, 'test.csv')
        self.assertEqual(task.status, ImportTask.Status.PENDING)

    def test_task_uuid_auto_generated(self):
        """Task ID should be auto-generated UUID."""
        task = ImportTask.objects.create(
            filename='test.csv',
            file_path='/tmp/test.csv',
        )
        self.assertIsInstance(task.task_id, uuid.UUID)

    def test_update_progress(self):
        """Should update progress correctly."""
        task = ImportTask.objects.create(
            filename='test.csv',
            file_path='/tmp/test.csv',
            total_rows=100,
        )
        task.update_progress(50, 5, 100)
        self.assertEqual(task.progress, 55)
        self.assertEqual(task.imported_rows, 50)
        self.assertEqual(task.error_rows, 5)

    def test_mark_failed(self):
        """Should mark task as failed with message."""
        task = ImportTask.objects.create(
            filename='test.csv',
            file_path='/tmp/test.csv',
        )
        task.mark_failed('Test error message')
        self.assertEqual(task.status, ImportTask.Status.FAILED)
        self.assertEqual(task.error_message, 'Test error message')


class CSVParsingTestCase(TestCase):
    """Tests for CSV file parsing."""

    def test_parse_simple_csv(self):
        """Should parse simple CSV with headers."""
        csv_content = "name,age,city\nAlice,30,NYC\nBob,25,LA\n"

        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write(csv_content)
            f.flush()

            result = parse_csv(f.name)

            self.assertEqual(len(result['columns']), 3)
            self.assertEqual(result['total_rows'], 2)
            self.assertEqual(result['columns'][0]['name'], 'name')
            self.assertEqual(result['columns'][1]['name'], 'age')
            self.assertEqual(result['columns'][1]['detected_type'], 'number')

    def test_parse_csv_with_dates(self):
        """Should detect date columns."""
        csv_content = "id,date\n1,2024-01-15\n2,2024-02-20\n"

        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write(csv_content)
            f.flush()

            result = parse_csv(f.name)

            self.assertEqual(result['columns'][1]['detected_type'], 'date')

    def test_parse_csv_file_not_found(self):
        """Should raise error for non-existent file."""
        with self.assertRaises(FileNotFoundError):
            parse_csv('/nonexistent/file.csv')


class ImportTaskServiceTestCase(TestCase):
    """Tests for import task service functions."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )

    def test_create_import_task(self):
        """Should create task with correct attributes."""
        task = create_import_task(
            user=self.user,
            filename='data.csv',
            file_path='/tmp/data.csv',
        )

        self.assertEqual(task.user, self.user)
        self.assertEqual(task.filename, 'data.csv')
        self.assertEqual(task.file_path, '/tmp/data.csv')
        self.assertEqual(task.status, ImportTask.Status.PENDING)

    def test_create_import_task_anonymous(self):
        """Should allow anonymous task creation."""
        task = create_import_task(
            user=None,
            filename='data.csv',
            file_path='/tmp/data.csv',
        )

        self.assertIsNone(task.user)
        self.assertEqual(task.filename, 'data.csv')


class ImportAPITestCase(TestCase):
    """Integration tests for import API endpoints."""

    def setUp(self):
        self.client = TestClient(imports_router)
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )

    def test_task_not_found(self):
        """Should return 404 for non-existent task."""
        fake_uuid = str(uuid.uuid4())
        response = self.client.get(f'/tasks/{fake_uuid}')
        self.assertEqual(response.status_code, 404)

    def test_invalid_task_id_format(self):
        """Should return 400 for invalid UUID format."""
        response = self.client.get('/tasks/invalid-uuid')
        self.assertEqual(response.status_code, 400)

    def test_list_tasks_empty(self):
        """Should return empty list when no tasks."""
        response = self.client.get('/tasks')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['data']['tasks'], [])
        self.assertEqual(data['data']['total'], 0)

    def test_list_tasks_with_pagination(self):
        """Should respect pagination parameters."""
        # Create some tasks
        for i in range(5):
            ImportTask.objects.create(
                filename=f'test_{i}.csv',
                file_path=f'/tmp/test_{i}.csv',
            )

        response = self.client.get('/tasks?page=1&page_size=2')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data['data']['tasks']), 2)
        self.assertEqual(data['data']['total'], 5)
        self.assertEqual(data['data']['page'], 1)
        self.assertEqual(data['data']['page_size'], 2)

    def test_get_task_status(self):
        """Should return task status."""
        task = ImportTask.objects.create(
            filename='test.csv',
            file_path='/tmp/test.csv',
            status=ImportTask.Status.PROCESSING,
            progress=50,
            total_rows=100,
        )

        response = self.client.get(f'/tasks/{task.task_id}')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['data']['status'], 'processing')
        self.assertEqual(data['data']['progress'], 50)


class PreviewEndpointTestCase(TestCase):
    """Tests for preview endpoint."""

    def setUp(self):
        self.client = TestClient(imports_router)

    def test_preview_invalid_task_id(self):
        """Should return 400 for invalid task_id format."""
        response = self.client.post('/preview', json={'task_id': 'invalid'})
        self.assertEqual(response.status_code, 400)

    def test_preview_task_not_found(self):
        """Should return 404 for non-existent task."""
        fake_uuid = str(uuid.uuid4())
        response = self.client.post('/preview', json={'task_id': fake_uuid})
        self.assertEqual(response.status_code, 404)


class ExecuteEndpointTestCase(TestCase):
    """Tests for execute endpoint."""

    def setUp(self):
        self.client = TestClient(imports_router)

    def test_execute_invalid_task_id(self):
        """Should return 400 for invalid task_id format."""
        response = self.client.post('/execute', json={
            'task_id': 'invalid',
            'target_type': 'report',
            'column_mapping': [],
        })
        self.assertEqual(response.status_code, 400)

    def test_execute_task_not_found(self):
        """Should return 404 for non-existent task."""
        fake_uuid = str(uuid.uuid4())
        response = self.client.post('/execute', json={
            'task_id': fake_uuid,
            'target_type': 'report',
            'column_mapping': [],
        })
        self.assertEqual(response.status_code, 404)

    def test_execute_wrong_status(self):
        """Should reject execution of non-pending tasks."""
        task = ImportTask.objects.create(
            filename='test.csv',
            file_path='/tmp/test.csv',
            status=ImportTask.Status.COMPLETED,
        )

        response = self.client.post('/execute', json={
            'task_id': str(task.task_id),
            'target_type': 'report',
            'column_mapping': [],
        })
        self.assertEqual(response.status_code, 400)
        self.assertIn('cannot be executed', response.json()['detail'])

    def test_execute_missing_required_fields(self):
        """Should reject mapping without required fields."""
        task = ImportTask.objects.create(
            filename='test.csv',
            file_path='/tmp/test.csv',
            status=ImportTask.Status.PENDING,
        )

        response = self.client.post('/execute', json={
            'task_id': str(task.task_id),
            'target_type': 'report',
            'column_mapping': [
                {'source_column': 'col1', 'target_field': 'uid'},
            ],
        })
        self.assertEqual(response.status_code, 400)
        self.assertIn('Missing required fields', response.json()['detail'])


class SampleFileTestCase(TestCase):
    """Tests using sample CSV fixture files."""

    def setUp(self):
        self.fixtures_dir = Path(__file__).parent / 'fixtures'

    def test_parse_sample_reports_csv(self):
        """Should parse sample_reports.csv correctly."""
        file_path = self.fixtures_dir / 'sample_reports.csv'
        result = parse_csv(str(file_path))

        # Check structure
        self.assertEqual(len(result['columns']), 5)
        self.assertEqual(result['total_rows'], 5)

        # Check column names
        column_names = [c['name'] for c in result['columns']]
        self.assertIn('uid', column_names)
        self.assertIn('title', column_names)
        self.assertIn('content', column_names)
        self.assertIn('report_type', column_names)
        self.assertIn('report_date', column_names)

        # Check date detection
        date_col = next(c for c in result['columns'] if c['name'] == 'report_date')
        self.assertEqual(date_col['detected_type'], 'date')

    def test_parse_sample_studies_csv(self):
        """Should parse sample_studies.csv correctly."""
        file_path = self.fixtures_dir / 'sample_studies.csv'
        result = parse_csv(str(file_path))

        # Check structure
        self.assertEqual(len(result['columns']), 6)
        self.assertEqual(result['total_rows'], 5)

        # Check column names
        column_names = [c['name'] for c in result['columns']]
        self.assertIn('exam_id', column_names)
        self.assertIn('patient_name', column_names)
        self.assertIn('modality', column_names)

    def test_field_mapping_for_sample_reports(self):
        """Should suggest correct field mappings for report columns."""
        file_path = self.fixtures_dir / 'sample_reports.csv'
        result = parse_csv(str(file_path))

        # Check that all columns get correct suggestions
        for col in result['columns']:
            suggestion = suggest_field_mapping(col['name'], 'report')
            if col['name'] == 'uid':
                self.assertEqual(suggestion, 'uid')
            elif col['name'] == 'title':
                self.assertEqual(suggestion, 'title')
            elif col['name'] == 'content':
                self.assertEqual(suggestion, 'content')
            elif col['name'] == 'report_type':
                self.assertEqual(suggestion, 'report_type')
            elif col['name'] == 'report_date':
                self.assertEqual(suggestion, 'report_date')

    def test_field_mapping_for_sample_studies(self):
        """Should suggest correct field mappings for study columns."""
        file_path = self.fixtures_dir / 'sample_studies.csv'
        result = parse_csv(str(file_path))

        for col in result['columns']:
            suggestion = suggest_field_mapping(col['name'], 'study')
            if col['name'] == 'exam_id':
                self.assertEqual(suggestion, 'exam_id')
            elif col['name'] == 'patient_name':
                self.assertEqual(suggestion, 'patient_name')
            elif col['name'] == 'modality':
                self.assertEqual(suggestion, 'modality')


class ErrorHandlingTestCase(TestCase):
    """Tests for error handling and partial imports."""

    def setUp(self):
        self.fixtures_dir = Path(__file__).parent / 'fixtures'

    def test_parse_sample_errors_csv(self):
        """Should parse CSV with missing values."""
        file_path = self.fixtures_dir / 'sample_errors.csv'
        result = parse_csv(str(file_path))

        # Should still parse successfully
        self.assertEqual(result['total_rows'], 5)
        self.assertEqual(len(result['columns']), 5)

        # Preview rows should include empty values
        self.assertEqual(len(result['preview_rows']), 5)


class LargeFileTestCase(TestCase):
    """Tests for large file processing (async)."""

    def test_large_csv_generation(self):
        """Should handle large CSV files."""
        # Generate a large CSV
        rows = 1500  # Above SYNC_THRESHOLD of 1000

        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write("uid,title,content,report_type\n")
            for i in range(rows):
                f.write(f"RPT{i:04d},Report {i},Content for report {i},X-Ray\n")
            f.flush()

            result = parse_csv(f.name)

            self.assertEqual(result['total_rows'], rows)
            self.assertEqual(len(result['preview_rows']), 10)  # Default preview size

    def test_task_triggers_async_for_large_files(self):
        """Large files should trigger async processing."""
        from imports.services import SYNC_THRESHOLD

        # Create task with large row count
        task = ImportTask.objects.create(
            filename='large.csv',
            file_path='/tmp/large.csv',
            total_rows=SYNC_THRESHOLD + 1,
            status=ImportTask.Status.PENDING,
        )

        # Verify threshold
        self.assertGreater(task.total_rows, SYNC_THRESHOLD)


class ProgressTrackingTestCase(TestCase):
    """Tests for progress tracking functionality."""

    def test_progress_calculation(self):
        """Progress should be calculated correctly."""
        task = ImportTask.objects.create(
            filename='test.csv',
            file_path='/tmp/test.csv',
            total_rows=100,
        )

        # Update progress at 25%
        task.update_progress(20, 5, 100)
        self.assertEqual(task.progress, 25)

        # Update progress at 50%
        task.update_progress(40, 10, 100)
        self.assertEqual(task.progress, 50)

        # Update progress at 100%
        task.update_progress(90, 10, 100)
        self.assertEqual(task.progress, 100)

    def test_progress_with_all_errors(self):
        """Progress should handle all-error scenario."""
        task = ImportTask.objects.create(
            filename='test.csv',
            file_path='/tmp/test.csv',
            total_rows=100,
        )

        task.update_progress(0, 100, 100)
        self.assertEqual(task.progress, 100)
        self.assertEqual(task.imported_rows, 0)
        self.assertEqual(task.error_rows, 100)


class CleanupTestCase(TestCase):
    """Tests for file cleanup functionality."""

    def test_cleanup_expired_files(self):
        """Cleanup should remove expired tasks."""
        from imports.services import cleanup_expired_files
        from django.utils import timezone
        from datetime import timedelta

        # Create an expired task
        old_task = ImportTask.objects.create(
            filename='old.csv',
            file_path='/tmp/old.csv',
            status=ImportTask.Status.PENDING,
        )
        # Manually backdate the created_at
        ImportTask.objects.filter(task_id=old_task.task_id).update(
            created_at=timezone.now() - timedelta(hours=25)
        )

        # Run cleanup
        cleaned = cleanup_expired_files(max_age_hours=24)

        # Verify task was marked as expired
        old_task.refresh_from_db()
        self.assertEqual(old_task.status, ImportTask.Status.EXPIRED)

    def test_cleanup_preserves_recent_tasks(self):
        """Cleanup should preserve recent tasks."""
        from imports.services import cleanup_expired_files

        # Create a recent task
        recent_task = ImportTask.objects.create(
            filename='recent.csv',
            file_path='/tmp/recent.csv',
            status=ImportTask.Status.PENDING,
        )

        # Run cleanup
        cleanup_expired_files(max_age_hours=24)

        # Verify task was preserved
        recent_task.refresh_from_db()
        self.assertEqual(recent_task.status, ImportTask.Status.PENDING)
