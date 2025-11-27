"""
Unit tests for Study field queries in AdvancedQueryBuilder.
"""

from datetime import datetime
from unittest import skipUnless

from django.db import connection
from django.test import TestCase, Client

from report.models import Report
from report.schemas import AdvancedSearchRequest
from report.service import ReportService
from report.services import AdvancedQueryBuilder, AdvancedQueryValidationError
from study.models import Study


@skipUnless(connection.vendor == 'postgresql', 'PostgreSQL-only feature tests')
class StudyFieldQueryTest(TestCase):
    """Test AdvancedQueryBuilder with Study field conditions."""

    @classmethod
    def setUpTestData(cls):
        """Create test Study and Report records."""
        # Study 1: 65-year-old male, MRI, completed
        cls.study1 = Study.objects.create(
            exam_id='EXAM001',
            patient_name='張三',
            patient_age=65,
            patient_gender='M',
            exam_source='MRI',
            exam_item='Brain MRI',
            exam_status='completed',
            order_datetime=datetime(2024, 1, 15, 10, 0, 0),
            equipment_type='Siemens 3T'
        )

        # Study 2: 45-year-old female, CT, completed
        cls.study2 = Study.objects.create(
            exam_id='EXAM002',
            patient_name='李四',
            patient_age=45,
            patient_gender='F',
            exam_source='CT',
            exam_item='Chest CT',
            exam_status='completed',
            order_datetime=datetime(2024, 2, 20, 14, 30, 0),
            equipment_type='GE 64-slice'
        )

        # Study 3: 30-year-old male, X-ray, pending
        cls.study3 = Study.objects.create(
            exam_id='EXAM003',
            patient_name='王五',
            patient_age=30,
            patient_gender='M',
            exam_source='X-ray',
            exam_item='Chest X-ray',
            exam_status='pending',
            order_datetime=datetime(2024, 3, 10, 9, 15, 0),
            equipment_type='Canon'
        )

        # Create Reports linked to Studies
        cls.report1 = Report.objects.create(
            uid='REP001',
            report_id='EXAM001',  # Links to study1
            title='Brain MRI Report - Normal',
            report_type='Radiology',
            content_raw='Normal brain structure. No abnormalities detected.',
            content_processed='normal brain structure abnormalities detected',
            is_latest=True,
            verified_at=datetime(2024, 1, 16, 10, 0, 0)
        )

        cls.report2 = Report.objects.create(
            uid='REP002',
            report_id='EXAM002',  # Links to study2
            title='Chest CT Report - Pneumonia',
            report_type='Radiology',
            content_raw='Findings consistent with pneumonia.',
            content_processed='findings consistent pneumonia',
            is_latest=True,
            verified_at=datetime(2024, 2, 21, 9, 0, 0)
        )

        cls.report3 = Report.objects.create(
            uid='REP003',
            report_id='EXAM003',  # Links to study3
            title='Chest X-ray Report',
            report_type='Radiology',
            content_raw='Pending radiologist review.',
            content_processed='pending radiologist review',
            is_latest=True,
            verified_at=None
        )

    def test_single_study_field_patient_age_gte(self):
        """Test filtering by Study.patient_age >= 60."""
        payload = {
            'operator': 'AND',
            'conditions': [{'field': 'study.patient_age', 'operator': 'gte', 'value': 60}],
        }

        builder = AdvancedQueryBuilder(payload)
        result = builder.build()

        reports = Report.objects.filter(result.filters)
        self.assertEqual(reports.count(), 1)
        self.assertEqual(reports.first().uid, 'REP001')

    def test_single_study_field_exam_source_equals(self):
        """Test filtering by Study.exam_source = 'CT'."""
        payload = {
            'operator': 'AND',
            'conditions': [{'field': 'study.exam_source', 'operator': 'equals', 'value': 'CT'}],
        }

        builder = AdvancedQueryBuilder(payload)
        result = builder.build()

        reports = Report.objects.filter(result.filters)
        self.assertEqual(reports.count(), 1)
        self.assertEqual(reports.first().uid, 'REP002')

    def test_study_field_exam_source_in_list(self):
        """Test filtering by Study.exam_source IN ['MRI', 'CT']."""
        payload = {
            'operator': 'AND',
            'conditions': [
                {'field': 'study.exam_source', 'operator': 'in', 'value': ['MRI', 'CT']}
            ],
        }

        builder = AdvancedQueryBuilder(payload)
        result = builder.build()

        reports = Report.objects.filter(result.filters)
        self.assertEqual(reports.count(), 2)
        uids = {r.uid for r in reports}
        self.assertEqual(uids, {'REP001', 'REP002'})

    def test_mixed_report_and_study_filters(self):
        """Test combining Report and Study field filters with AND."""
        payload = {
            'operator': 'AND',
            'conditions': [
                {'field': 'title', 'operator': 'contains', 'value': 'MRI'},
                {'field': 'study.exam_source', 'operator': 'equals', 'value': 'MRI'},
                {'field': 'study.patient_age', 'operator': 'gte', 'value': 60},
            ],
        }

        builder = AdvancedQueryBuilder(payload)
        result = builder.build()

        reports = Report.objects.filter(result.filters)
        self.assertEqual(reports.count(), 1)
        self.assertEqual(reports.first().uid, 'REP001')

    def test_study_field_with_or_logic(self):
        """Test OR logic with Study fields."""
        payload = {
            'operator': 'OR',
            'conditions': [
                {'field': 'study.exam_source', 'operator': 'equals', 'value': 'MRI'},
                {'field': 'study.exam_source', 'operator': 'equals', 'value': 'X-ray'},
            ],
        }

        builder = AdvancedQueryBuilder(payload)
        result = builder.build()

        reports = Report.objects.filter(result.filters)
        self.assertEqual(reports.count(), 2)
        uids = {r.uid for r in reports}
        self.assertEqual(uids, {'REP001', 'REP003'})

    def test_nested_group_with_study_fields(self):
        """Test nested groups combining Report and Study filters."""
        payload = {
            'operator': 'AND',
            'conditions': [
                {
                    'operator': 'OR',
                    'conditions': [
                        {'field': 'study.exam_source', 'operator': 'equals', 'value': 'MRI'},
                        {'field': 'study.exam_source', 'operator': 'equals', 'value': 'CT'},
                    ],
                },
                {'field': 'study.patient_age', 'operator': 'gte', 'value': 40},
            ],
        }

        builder = AdvancedQueryBuilder(payload)
        result = builder.build()

        reports = Report.objects.filter(result.filters)
        self.assertEqual(reports.count(), 2)
        uids = {r.uid for r in reports}
        self.assertEqual(uids, {'REP001', 'REP002'})

    def test_study_field_patient_name_contains(self):
        """Test text operator on Study.patient_name."""
        payload = {
            'operator': 'AND',
            'conditions': [{'field': 'study.patient_name', 'operator': 'contains', 'value': '張'}],
        }

        builder = AdvancedQueryBuilder(payload)
        result = builder.build()

        reports = Report.objects.filter(result.filters)
        self.assertEqual(reports.count(), 1)
        self.assertEqual(reports.first().uid, 'REP001')

    def test_study_field_order_datetime_range(self):
        """Test datetime range operator on Study.order_datetime."""
        payload = {
            'operator': 'AND',
            'conditions': [
                {
                    'field': 'study.order_datetime',
                    'operator': 'between',
                    'value': {'start': '2024-01-01', 'end': '2024-02-01'},
                }
            ],
        }

        builder = AdvancedQueryBuilder(payload)
        result = builder.build()

        reports = Report.objects.filter(result.filters)
        self.assertEqual(reports.count(), 1)
        self.assertEqual(reports.first().uid, 'REP001')

    def test_invalid_study_field_name(self):
        """Test validation error for invalid Study field."""
        payload = {
            'operator': 'AND',
            'conditions': [
                {'field': 'study.invalid_field', 'operator': 'equals', 'value': 'test'}
            ],
        }

        builder = AdvancedQueryBuilder(payload)
        with self.assertRaisesMessage(
            AdvancedQueryValidationError, 'Unsupported Study field: study.invalid_field'
        ):
            builder.build()

    def test_unsupported_operator_for_study_field(self):
        """Test validation error for unsupported operator on Study field."""
        payload = {
            'operator': 'AND',
            'conditions': [
                {'field': 'study.patient_age', 'operator': 'contains', 'value': '60'}
            ],
        }

        builder = AdvancedQueryBuilder(payload)
        with self.assertRaisesMessage(
            AdvancedQueryValidationError,
            'Operator "contains" is not allowed for field "study.patient_age"',
        ):
            builder.build()

    def test_study_field_patient_gender_in_list(self):
        """Test choice field with IN operator."""
        payload = {
            'operator': 'AND',
            'conditions': [
                {'field': 'study.patient_gender', 'operator': 'in', 'value': ['M', 'F']}
            ],
        }

        builder = AdvancedQueryBuilder(payload)
        result = builder.build()

        reports = Report.objects.filter(result.filters)
        self.assertEqual(reports.count(), 3)  # All reports

    def test_complex_nested_query_with_study_and_report(self):
        """Test complex nested query combining multiple conditions."""
        payload = {
            'operator': 'AND',
            'conditions': [
                {
                    'operator': 'OR',
                    'conditions': [
                        {'field': 'title', 'operator': 'contains', 'value': 'MRI'},
                        {'field': 'title', 'operator': 'contains', 'value': 'CT'},
                    ],
                },
                {
                    'operator': 'AND',
                    'conditions': [
                        {'field': 'study.patient_age', 'operator': 'gte', 'value': 40},
                        {'field': 'study.exam_status', 'operator': 'in', 'value': ['completed']},
                    ],
                },
            ],
        }

        builder = AdvancedQueryBuilder(payload)
        result = builder.build()

        reports = Report.objects.filter(result.filters)
        self.assertEqual(reports.count(), 2)
        uids = {r.uid for r in reports}
        self.assertEqual(uids, {'REP001', 'REP002'})

