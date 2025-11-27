from __future__ import annotations

from unittest import skipUnless

from django.db import connection
from django.test import SimpleTestCase, TestCase
from django.utils import timezone

from report.models import Report
from report.schemas import AdvancedSearchRequest, AdvancedSearchNode, BasicAdvancedQuery
from report.service import ReportService
from report.services import AdvancedQueryBuilder, AdvancedQueryValidationError


class AdvancedQueryBuilderTest(SimpleTestCase):
    def test_nested_group_builds_q_objects(self):
        payload: AdvancedSearchNode = AdvancedSearchNode(
            operator='AND',
            conditions=[
                {'field': 'report_type', 'operator': 'equals', 'value': 'Radiology'},
                {
                    'operator': 'OR',
                    'conditions': [
                        {'field': 'title', 'operator': 'contains', 'value': 'MRI'},
                        {'field': 'title', 'operator': 'contains', 'value': 'CT'},
                    ],
                },
            ],
        )

        result = AdvancedQueryBuilder(payload.dict()).build()
        self.assertIn('report_type', str(result.filters))
        self.assertIsNone(result.search_query)

    def test_guardrails_raise_validation_error(self):
        deep_payload = {'operator': 'AND', 'conditions': []}
        node = deep_payload
        for _ in range(AdvancedQueryBuilder.MAX_DEPTH + 1):
            child = {'operator': 'AND', 'conditions': []}
            node['conditions'].append(child)
            node = child

        with self.assertRaises(AdvancedQueryValidationError):
            AdvancedQueryBuilder(deep_payload).build()


@skipUnless(connection.vendor == 'postgresql', 'PostgreSQL-only feature tests')
class AdvancedSearchServiceTest(TestCase):
    def setUp(self):
        self.report = Report.objects.create(
            uid='uid-1',
            report_id='RPT-001',
            title='MRI Brain Lesion',
            report_type='Radiology',
            content_raw='There is a small lesion in the left temporal lobe.',
            content_processed='There is a small lesion in the left temporal lobe.',
            content_hash='hash-1',
            source_url='http://example.com/report/1',
            verified_at=timezone.now(),
            metadata={'status': 'verified'},
        )

        self.report_latest = Report.objects.get(pk=self.report.pk)

    def test_basic_mode_full_text_search(self):
        payload = AdvancedSearchRequest(
            mode='basic',
            basic=BasicAdvancedQuery(text='lesion'),
            page=1,
            page_size=5,
        )

        response = ReportService.advanced_search(payload)
        self.assertEqual(response['total'], 1)
        self.assertEqual(response['items'][0]['uid'], self.report_latest.uid)

    def test_multi_mode_dsl_filters(self):
        payload = AdvancedSearchRequest(
            mode='multi',
            tree=AdvancedSearchNode(
                operator='AND',
                conditions=[
                    {'field': 'report_type', 'operator': 'equals', 'value': 'Radiology'},
                    {'field': 'content', 'operator': 'search', 'value': 'lesion'},
                ],
            ),
            page=1,
            page_size=5,
        )

        response = ReportService.advanced_search(payload)
        self.assertEqual(response['total'], 1)
        self.assertEqual(response['items'][0]['title'], 'MRI Brain Lesion')

