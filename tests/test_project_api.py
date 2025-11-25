from __future__ import annotations

import json

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.utils import timezone

from project.models import Project, ProjectMember, Study, StudyProjectAssignment
from project.service import ProjectService


class ProjectApiTestCase(TestCase):
    """整合測試：Projects API 端點"""

    @classmethod
    def setUpTestData(cls):
        cls.User = get_user_model()
        cls.owner = cls.User.objects.create_user(
            username='api_owner',
            email='api_owner@example.com',
            password='pass1234',
        )
        cls.editor = cls.User.objects.create_user(
            username='api_editor',
            email='api_editor@example.com',
            password='pass1234',
        )
        cls.viewer = cls.User.objects.create_user(
            username='api_viewer',
            email='api_viewer@example.com',
            password='pass1234',
        )

        now = timezone.now()
        cls.study1 = Study.objects.create(
            exam_id='API-EXAM-001',
            patient_name='Alice API',
            exam_status='completed',
            exam_source='CT',
            exam_item='CT Chest',
            equipment_type='CT',
            order_datetime=now,
        )
        cls.study2 = Study.objects.create(
            exam_id='API-EXAM-002',
            patient_name='Bob API',
            exam_status='completed',
            exam_source='MRI',
            exam_item='MRI Brain',
            equipment_type='MRI',
            order_datetime=now,
        )

    def setUp(self):
        self.client = Client()
        self.client.force_login(self.owner)
        self.project = ProjectService.create_project(
            name='API Project',
            user=self.owner,
            description='Project for API tests',
            tags=['integration'],
        )

    def test_list_projects_returns_results(self):
        response = self.client.get('/api/v1/projects')
        self.assertEqual(response.status_code, 200)

        data = json.loads(response.content)
        self.assertIn('items', data)
        self.assertEqual(data['count'], 1)
        self.assertEqual(data['items'][0]['name'], 'API Project')
        self.assertEqual(data['items'][0]['user_role'], ProjectMember.ROLE_OWNER)
        self.assertTrue(data['items'][0]['can_assign_studies'])
        self.assertTrue(data['items'][0]['can_manage_members'])
        self.assertTrue(data['items'][0]['can_archive'])

    def test_create_project_endpoint(self):
        payload = {
            'name': 'New API Project',
            'description': 'Created via API',
            'tags': ['api'],
        }
        response = self.client.post(
            '/api/v1/projects',
            data=json.dumps(payload),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 201)

        response_payload = json.loads(response.content)
        self.assertEqual(response_payload['name'], payload['name'])
        self.assertEqual(response_payload['member_count'], 1)
        self.assertTrue(response_payload['can_assign_studies'])

        project_exists = Project.objects.filter(name='New API Project').exists()
        self.assertTrue(project_exists)

    def test_add_studies_endpoint_updates_study_count(self):
        payload = {'exam_ids': [self.study1.exam_id, self.study2.exam_id]}
        url = f'/api/v1/projects/{self.project.id}/studies'
        response = self.client.post(
            url,
            data=json.dumps(payload),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)

        data = json.loads(response.content)
        self.assertEqual(data['added_count'], 2)
        self.assertEqual(data['failed_items'], [])
        self.assertEqual(data['requested_count'], 2)

        self.project.refresh_from_db()
        self.assertEqual(self.project.study_count, 2)
        self.assertEqual(
            StudyProjectAssignment.objects.filter(project=self.project).count(),
            2,
        )

    def test_add_studies_returns_failed_items_for_duplicates(self):
        ProjectService.add_studies_to_project(
            project=self.project,
            exam_ids=[self.study1.exam_id],
            user=self.owner,
        )

        payload = {'exam_ids': [self.study1.exam_id]}
        url = f'/api/v1/projects/{self.project.id}/studies'
        response = self.client.post(
            url,
            data=json.dumps(payload),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data['added_count'], 0)
        self.assertEqual(len(data['failed_items']), 1)
        self.assertEqual(data['failed_items'][0]['reason'], 'already_assigned')

    def test_add_studies_enforces_batch_limit(self):
        excessive_ids = [f'EXAM-{i:04d}' for i in range(501)]
        url = f'/api/v1/projects/{self.project.id}/studies'
        response = self.client.post(
            url,
            data=json.dumps({'exam_ids': excessive_ids}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 400)
        payload = json.loads(response.content)
        self.assertEqual(payload['code'], 'too_many_items')
        self.assertEqual(payload['max_batch_size'], 500)

    def test_add_member_and_update_role(self):
        ProjectService.add_member(self.project, self.editor.id, role=ProjectMember.ROLE_EDITOR)
        payload = {'user_id': str(self.viewer.id), 'role': ProjectMember.ROLE_VIEWER}

        add_response = self.client.post(
            f'/api/v1/projects/{self.project.id}/members',
            data=json.dumps(payload),
            content_type='application/json',
        )
        self.assertEqual(add_response.status_code, 200)

        self.client.force_login(self.owner)
        update_payload = {'role': ProjectMember.ROLE_EDITOR}
        update_response = self.client.put(
            f'/api/v1/projects/{self.project.id}/members/{self.viewer.id}',
            data=json.dumps(update_payload),
            content_type='application/json',
        )
        self.assertEqual(update_response.status_code, 200)

        member = ProjectMember.objects.get(project=self.project, user=self.viewer)
        self.assertEqual(member.role, ProjectMember.ROLE_EDITOR)

    def test_update_member_role_requires_owner(self):
        ProjectService.add_member(self.project, self.viewer.id, role=ProjectMember.ROLE_VIEWER)
        self.client.force_login(self.viewer)

        payload = {'role': ProjectMember.ROLE_EDITOR}
        response = self.client.put(
            f'/api/v1/projects/{self.project.id}/members/{self.viewer.id}',
            data=json.dumps(payload),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 403)

    def test_statistics_endpoint_returns_counts(self):
        ProjectService.add_studies_to_project(
            project=self.project,
            exam_ids=[self.study1.exam_id],
            user=self.owner,
        )
        ProjectService.add_member(self.project, self.viewer.id, role=ProjectMember.ROLE_VIEWER)

        response = self.client.get(f'/api/v1/projects/{self.project.id}/statistics')
        self.assertEqual(response.status_code, 200)

        data = json.loads(response.content)
        self.assertEqual(data['study_count'], 1)
        self.assertEqual(data['member_count'], 2)

    def test_batch_assign_requires_permissions(self):
        other_project = ProjectService.create_project(
            name='Other Project',
            user=self.viewer,
        )
        payload = {
            'exam_ids': [self.study1.exam_id],
            'project_ids': [str(other_project.id)],
        }

        response = self.client.post(
            '/api/v1/projects/batch-assign/',
            data=json.dumps(payload),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)

        data = json.loads(response.content)
        self.assertEqual(data['total_assignments'], 0)
        self.assertEqual(
            StudyProjectAssignment.objects.filter(project=other_project).count(),
            0,
        )
