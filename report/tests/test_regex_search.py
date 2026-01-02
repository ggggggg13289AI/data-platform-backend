"""
Tests for imaging report regex search functionality.

Tests cover:
- Regex pattern validation
- Regex search operators (regex, iregex)
- Imaging-specific fields (imaging_findings, impression, content_raw)
- Invalid regex pattern error handling
"""

from __future__ import annotations

from unittest import skipUnless

from django.db import connection
from django.test import SimpleTestCase, TestCase
from django.utils import timezone

from report.models import Report
from report.schemas import AdvancedSearchRequest, AdvancedSearchNode
from report.service import ReportService
from report.services import (
    AdvancedQueryBuilder,
    AdvancedQueryValidationError,
    InvalidRegexPatternError,
)


class RegexPatternValidationTest(SimpleTestCase):
    """Test regex pattern validation before database execution."""

    def test_valid_regex_pattern_accepted(self):
        """Valid regex patterns should not raise errors."""
        payload = {
            'operator': 'AND',
            'conditions': [
                {'field': 'content_raw', 'operator': 'iregex', 'value': 'normal.+x-ray'}
            ],
        }
        result = AdvancedQueryBuilder(payload).build()
        self.assertIn('content_raw', str(result.filters))

    def test_invalid_regex_pattern_raises_error(self):
        """Invalid regex patterns should raise InvalidRegexPatternError."""
        payload = {
            'operator': 'AND',
            'conditions': [
                {'field': 'content_raw', 'operator': 'iregex', 'value': '(unbalanced['}
            ],
        }
        with self.assertRaises(InvalidRegexPatternError) as ctx:
            AdvancedQueryBuilder(payload).build()

        self.assertIn('(unbalanced[', str(ctx.exception))

    def test_case_sensitive_regex_operator(self):
        """'regex' operator should use case-sensitive matching."""
        payload = {
            'operator': 'AND',
            'conditions': [
                {'field': 'content_raw', 'operator': 'regex', 'value': 'Normal'}
            ],
        }
        result = AdvancedQueryBuilder(payload).build()
        # Check that regex (not iregex) lookup is used
        self.assertIn('regex', str(result.filters))

    def test_case_insensitive_regex_operator(self):
        """'iregex' operator should use case-insensitive matching."""
        payload = {
            'operator': 'AND',
            'conditions': [
                {'field': 'content_raw', 'operator': 'iregex', 'value': 'normal'}
            ],
        }
        result = AdvancedQueryBuilder(payload).build()
        # Check that iregex lookup is used
        self.assertIn('iregex', str(result.filters))


class ImagingFieldsValidationTest(SimpleTestCase):
    """Test that imaging-specific fields are properly configured."""

    def test_imaging_findings_field_accepts_text_operators(self):
        """imaging_findings should support text operators."""
        payload = {
            'operator': 'AND',
            'conditions': [
                {'field': 'imaging_findings', 'operator': 'contains', 'value': 'cardiomegaly'}
            ],
        }
        result = AdvancedQueryBuilder(payload).build()
        self.assertIn('imaging_findings', str(result.filters))

    def test_imaging_findings_field_accepts_regex_operators(self):
        """imaging_findings should support regex operators."""
        payload = {
            'operator': 'AND',
            'conditions': [
                {'field': 'imaging_findings', 'operator': 'iregex', 'value': '(cardiomegaly|effusion)'}
            ],
        }
        result = AdvancedQueryBuilder(payload).build()
        self.assertIn('imaging_findings', str(result.filters))

    def test_impression_field_accepts_text_operators(self):
        """impression should support text operators."""
        payload = {
            'operator': 'AND',
            'conditions': [
                {'field': 'impression', 'operator': 'contains', 'value': 'pneumonia'}
            ],
        }
        result = AdvancedQueryBuilder(payload).build()
        self.assertIn('impression', str(result.filters))

    def test_impression_field_accepts_regex_operators(self):
        """impression should support regex operators."""
        payload = {
            'operator': 'AND',
            'conditions': [
                {'field': 'impression', 'operator': 'iregex', 'value': 'pneumonia|lung.?infection'}
            ],
        }
        result = AdvancedQueryBuilder(payload).build()
        self.assertIn('impression', str(result.filters))

    def test_content_raw_field_accepts_regex_operators(self):
        """content_raw should support regex operators."""
        payload = {
            'operator': 'AND',
            'conditions': [
                {'field': 'content_raw', 'operator': 'iregex', 'value': 'normal.+chest'}
            ],
        }
        result = AdvancedQueryBuilder(payload).build()
        self.assertIn('content_raw', str(result.filters))

    def test_unsupported_operator_raises_error(self):
        """Unsupported operators should raise validation error."""
        payload = {
            'operator': 'AND',
            'conditions': [
                # 'between' is not supported for text fields
                {'field': 'imaging_findings', 'operator': 'between', 'value': {'start': 'a', 'end': 'z'}}
            ],
        }
        with self.assertRaises(AdvancedQueryValidationError):
            AdvancedQueryBuilder(payload).build()


class RegexOperatorEdgeCasesTest(SimpleTestCase):
    """Test edge cases for regex operators."""

    def test_empty_regex_pattern_raises_error(self):
        """Empty regex pattern should raise validation error."""
        payload = {
            'operator': 'AND',
            'conditions': [
                {'field': 'content_raw', 'operator': 'iregex', 'value': ''}
            ],
        }
        with self.assertRaises(AdvancedQueryValidationError):
            AdvancedQueryBuilder(payload).build()

    def test_whitespace_only_regex_pattern_raises_error(self):
        """Whitespace-only regex pattern should raise validation error."""
        payload = {
            'operator': 'AND',
            'conditions': [
                {'field': 'content_raw', 'operator': 'iregex', 'value': '   '}
            ],
        }
        with self.assertRaises(AdvancedQueryValidationError):
            AdvancedQueryBuilder(payload).build()

    def test_complex_regex_pattern_accepted(self):
        """Complex but valid regex patterns should be accepted."""
        complex_patterns = [
            r'normal\s*(chest|abdomen)',
            r'(?:impression|imp|conclusion):?\s*',
            r'(cardiomegaly|pleural\s+effusion)',
            r'\d{4}-\d{2}-\d{2}',  # Date pattern
            r'[A-Z][a-z]+\s+\d+',  # Word followed by number
        ]

        for pattern in complex_patterns:
            with self.subTest(pattern=pattern):
                payload = {
                    'operator': 'AND',
                    'conditions': [
                        {'field': 'content_raw', 'operator': 'iregex', 'value': pattern}
                    ],
                }
                result = AdvancedQueryBuilder(payload).build()
                self.assertIsNotNone(result.filters)


@skipUnless(connection.vendor == 'postgresql', 'PostgreSQL-only feature tests')
class RegexSearchIntegrationTest(TestCase):
    """Integration tests for regex search with actual database queries.

    Note: These tests require the generated columns to be created via migrations.
    If migrations haven't been applied, some tests may fail.
    """

    def setUp(self):
        """Create test reports with imaging content."""
        self.report_normal = Report.objects.create(
            uid='uid-normal',
            report_id='RPT-NORMAL',
            title='Chest X-Ray Normal',
            report_type='Radiology',
            content_raw='Imaging findings: No significant abnormality. Impression: Normal chest X-ray.',
            content_processed='Imaging findings: No significant abnormality. Impression: Normal chest X-ray.',
            content_hash='hash-normal',
            source_url='http://example.com/report/normal',
            verified_at=timezone.now(),
            metadata={'status': 'verified'},
        )

        self.report_abnormal = Report.objects.create(
            uid='uid-abnormal',
            report_id='RPT-ABNORMAL',
            title='Chest CT Abnormal',
            report_type='Radiology',
            content_raw='Imaging findings: Mild cardiomegaly and pleural effusion noted. Impression: Suspected pneumonia. Suggest follow-up CT.',
            content_processed='Imaging findings: Mild cardiomegaly and pleural effusion noted. Impression: Suspected pneumonia. Suggest follow-up CT.',
            content_hash='hash-abnormal',
            source_url='http://example.com/report/abnormal',
            verified_at=timezone.now(),
            metadata={'status': 'verified'},
        )

    def test_regex_search_on_content_raw(self):
        """Test regex search directly on content_raw field."""
        payload = AdvancedSearchRequest(
            mode='multi',
            tree=AdvancedSearchNode(
                operator='AND',
                conditions=[
                    {'field': 'content_raw', 'operator': 'iregex', 'value': 'normal.+x-ray'}
                ],
            ),
            page=1,
            page_size=10,
        )

        response = ReportService.advanced_search(payload)
        self.assertEqual(response['total'], 1)
        self.assertEqual(response['items'][0]['uid'], 'uid-normal')

    def test_regex_search_with_alternation(self):
        """Test regex with alternation pattern (|)."""
        payload = AdvancedSearchRequest(
            mode='multi',
            tree=AdvancedSearchNode(
                operator='AND',
                conditions=[
                    {'field': 'content_raw', 'operator': 'iregex', 'value': '(cardiomegaly|effusion)'}
                ],
            ),
            page=1,
            page_size=10,
        )

        response = ReportService.advanced_search(payload)
        self.assertEqual(response['total'], 1)
        self.assertEqual(response['items'][0]['uid'], 'uid-abnormal')

    def test_combined_regex_and_text_search(self):
        """Test combining regex search with text search."""
        payload = AdvancedSearchRequest(
            mode='multi',
            tree=AdvancedSearchNode(
                operator='AND',
                conditions=[
                    {'field': 'report_type', 'operator': 'equals', 'value': 'Radiology'},
                    {'field': 'content_raw', 'operator': 'iregex', 'value': 'pneumonia'}
                ],
            ),
            page=1,
            page_size=10,
        )

        response = ReportService.advanced_search(payload)
        self.assertEqual(response['total'], 1)
        self.assertEqual(response['items'][0]['uid'], 'uid-abnormal')

    def test_case_sensitive_regex_no_match(self):
        """Case-sensitive regex should not match wrong case."""
        payload = AdvancedSearchRequest(
            mode='multi',
            tree=AdvancedSearchNode(
                operator='AND',
                conditions=[
                    # Using 'regex' (case-sensitive) with lowercase 'normal'
                    # Should NOT match 'Normal' in the report
                    {'field': 'content_raw', 'operator': 'regex', 'value': '^normal'}
                ],
            ),
            page=1,
            page_size=10,
        )

        response = ReportService.advanced_search(payload)
        # Should return 0 because 'Normal' doesn't match '^normal' (case-sensitive)
        self.assertEqual(response['total'], 0)
