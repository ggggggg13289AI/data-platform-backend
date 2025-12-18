from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from common.models import StudyProjectAssignment
from project.models import Project
from project.services.accession_resolver import AccessionKeyResolver
from project.services.resource_aggregator import ResourceAggregator
from report.models import Report
from study.models import Study


class AccessionResolverTest(TestCase):
    def test_resolve_study(self):
        self.assertEqual(AccessionKeyResolver.resolve_study_id('ACC123'), 'ACC123')

    def test_resolve_report(self):
        self.assertEqual(AccessionKeyResolver.resolve_report_id('ACC123'), 'ACC123')

    def test_validate_linkage(self):
        self.assertTrue(AccessionKeyResolver.validate_linkage('ACC123', 'ACC123'))


class ResourceAggregatorTest(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(username='tester', password='pass')
        self.project = Project.objects.create(
            name='Demo Project',
            description='Sample',
            status=Project.STATUS_ACTIVE,
            tags=[],
            created_by=self.user,
            settings={},
            metadata={},
        )
        now = timezone.now()
        self.study = Study.objects.create(
            exam_id='ACC-001',
            medical_record_no='MR-001',
            application_order_no='APP-1',
            patient_name='Alice',
            patient_gender='F',
            patient_age=30,
            exam_status='completed',
            exam_source='CT',
            exam_item='Head CT',
            exam_description='Brain',
            exam_room='Room 1',
            exam_equipment='Scanner 1',
            equipment_type='CT',
            order_datetime=now,
            check_in_datetime=now,
            report_certification_datetime=now,
            certified_physician='Dr. Foo',
        )
        self.report = Report.objects.create(
            uid='UID-1',
            report_id='ACC-001',
            title='Report Title',
            report_type='medical_imaging',
            content_raw='Detailed report',
            content_processed='Detailed report processed',
            content_hash='hash-1',
            version_number=1,
            is_latest=True,
            source_url='http://example.com',
            verified_at=now,
        )
        StudyProjectAssignment.objects.create(
            project=self.project,
            study=self.study,
            assigned_by=self.user,
        )

    def test_aggregator_combines_study_and_report(self):
        result = ResourceAggregator.get_project_resources(
            project_id=str(self.project.id),
            resource_types=['study', 'report'],
            page=1,
            page_size=10,
        )

        self.assertEqual(result['count'], 1)
        self.assertEqual(result['page'], 1)
        self.assertEqual(result['page_size'], 10)

        item = result['items'][0]
        self.assertEqual(item.accession_number, 'ACC-001')
        self.assertIsNotNone(item.study)
        self.assertIsNotNone(item.report)
        self.assertEqual(item.assignment.assigned_by.id, str(self.user.id))
        self.assertEqual(item.resource_type, 'study')

    def test_aggregator_respects_query_and_resource_type(self):
        filtered = ResourceAggregator.get_project_resources(
            project_id=str(self.project.id),
            resource_types=['report'],
            page=1,
            page_size=10,
            q='Alice',
        )
        self.assertEqual(filtered['count'], 1)
        self.assertIsNone(filtered['items'][0].study)
        self.assertIsNotNone(filtered['items'][0].report)

        empty = ResourceAggregator.get_project_resources(
            project_id=str(self.project.id),
            resource_types=['report'],
            page=1,
            page_size=10,
            q='missing',
        )
        self.assertEqual(empty['count'], 0)
        self.assertEqual(empty['items'], [])
