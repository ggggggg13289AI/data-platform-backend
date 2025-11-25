from __future__ import annotations

from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.test import RequestFactory, TestCase
from django.utils import timezone

from common.permissions import ProjectPermissions, require_edit
from project.models import Project, ProjectMember, Study, StudyProjectAssignment
from project.service import ProjectService


class ProjectServiceTestCase(TestCase):
    """單元測試：ProjectService 業務邏輯"""

    @classmethod
    def setUpTestData(cls):
        cls.User = get_user_model()
        cls.owner = cls.User.objects.create_user(
            username='owner',
            email='owner@example.com',
            password='pass1234',
            first_name='Owner',
        )
        cls.admin = cls.User.objects.create_user(
            username='admin',
            email='admin@example.com',
            password='pass1234',
            first_name='Admin',
        )
        cls.viewer = cls.User.objects.create_user(
            username='viewer',
            email='viewer@example.com',
            password='pass1234',
            first_name='Viewer',
        )

        now = timezone.now()
        cls.study1 = Study.objects.create(
            exam_id='EXAM-001',
            patient_name='Alice',
            exam_status='completed',
            exam_source='CT',
            exam_item='Chest CT',
            equipment_type='CT',
            order_datetime=now,
        )
        cls.study2 = Study.objects.create(
            exam_id='EXAM-002',
            patient_name='Bob',
            exam_status='completed',
            exam_source='MRI',
            exam_item='Brain MRI',
            equipment_type='MRI',
            order_datetime=now,
        )

    def create_project(self, name: str = 'Test Project', tags: list[str] | None = None) -> Project:
        return ProjectService.create_project(
            name=name,
            user=self.owner,
            description='Project description',
            tags=tags or ['alpha'],
        )

    def test_create_project_sets_owner_membership(self):
        project = self.create_project('Project Ownership')
        self.assertEqual(project.created_by, self.owner)
        self.assertEqual(project.project_members.count(), 1)

        member = project.project_members.get(user=self.owner)
        self.assertEqual(member.role, ProjectMember.ROLE_OWNER)

    def test_get_projects_queryset_filters_by_membership(self):
        project_a = self.create_project('Project A')
        project_b = ProjectService.create_project(
            name='Project B',
            user=self.admin,
            description='Owned by admin',
        )

        qs_owner = ProjectService.get_projects_queryset(user=self.owner)
        self.assertEqual(list(qs_owner), [project_a])

        ProjectMember.objects.create(
            project=project_b,
            user=self.owner,
            role=ProjectMember.ROLE_VIEWER,
        )

        qs_owner_with_access = ProjectService.get_projects_queryset(user=self.owner)
        self.assertCountEqual(list(qs_owner_with_access), [project_a, project_b])

    def test_get_projects_queryset_supports_search_and_tags(self):
        project = self.create_project('Lung Cancer Study', tags=['lung', 'research'])
        ProjectMember.objects.create(
            project=project,
            user=self.viewer,
            role=ProjectMember.ROLE_VIEWER,
        )

        qs = ProjectService.get_projects_queryset(user=self.viewer, q='lung')
        self.assertIn(project, list(qs))

        qs_tags = ProjectService.get_projects_queryset(user=self.viewer, tags='research')
        self.assertIn(project, list(qs_tags))

        qs_miss = ProjectService.get_projects_queryset(user=self.viewer, tags='cardio')
        self.assertNotIn(project, list(qs_miss))

    def test_add_studies_to_project_creates_assignments_and_updates_count(self):
        project = self.create_project('Assignment Project')
        result = ProjectService.add_studies_to_project(
            project=project,
            exam_ids=[self.study1.exam_id, self.study2.exam_id],
            user=self.owner,
        )

        self.assertTrue(result['success'])
        self.assertEqual(result['added_count'], 2)
        self.assertEqual(project.study_count, 2)
        self.assertEqual(StudyProjectAssignment.objects.filter(project=project).count(), 2)

    def test_add_studies_to_project_raises_for_missing_exam(self):
        project = self.create_project('Missing Study Project')
        with self.assertRaises(ValueError):
            ProjectService.add_studies_to_project(
                project=project,
                exam_ids=['NOT-EXIST'],
                user=self.owner,
            )

    def test_remove_studies_from_project_decrements_count(self):
        project = self.create_project('Remove Study Project')
        ProjectService.add_studies_to_project(
            project=project,
            exam_ids=[self.study1.exam_id, self.study2.exam_id],
            user=self.owner,
        )

        result = ProjectService.remove_studies_from_project(
            project=project,
            exam_ids=[self.study1.exam_id],
        )

        self.assertTrue(result['success'])
        self.assertEqual(result['removed_count'], 1)
        project.refresh_from_db()
        self.assertEqual(project.study_count, 1)

    def test_add_member_prevents_duplicates(self):
        project = self.create_project('Duplicate Member Project')
        ProjectService.add_member(project=project, user_id=self.viewer.id)

        with self.assertRaises(ValueError):
            ProjectService.add_member(project=project, user_id=self.viewer.id)

    def test_remove_member_prevents_owner_removal(self):
        project = self.create_project('Owner Removal Project')
        with self.assertRaises(ValueError):
            ProjectService.remove_member(project=project, user_id=self.owner.id)

    def test_update_member_role_disallows_owner_role_changes(self):
        project = self.create_project('Owner Role Project')

        with self.assertRaises(ValueError):
            ProjectService.update_member_role(
                project=project,
                user_id=self.owner.id,
                new_role=ProjectMember.ROLE_ADMIN,
            )

    def test_get_project_statistics_returns_expected_fields(self):
        project = self.create_project('Statistics Project')
        ProjectService.add_studies_to_project(
            project=project,
            exam_ids=[self.study1.exam_id],
            user=self.owner,
        )
        ProjectService.add_member(project=project, user_id=self.viewer.id, role=ProjectMember.ROLE_VIEWER)

        stats = ProjectService.get_project_statistics(project)

        self.assertEqual(stats['project_id'], str(project.id))
        self.assertEqual(stats['study_count'], project.study_count)
        self.assertIn('modality_distribution', stats)
        self.assertIn('member_count', stats)
        self.assertIn('created_at', stats)
        self.assertIn('updated_at', stats)


class ProjectPermissionsTestCase(TestCase):
    """單元測試：ProjectPermissions 權限系統"""

    @classmethod
    def setUpTestData(cls):
        cls.User = get_user_model()
        cls.owner = cls.User.objects.create_user(username='perm_owner', password='pass123')
        cls.admin = cls.User.objects.create_user(username='perm_admin', password='pass123')
        cls.viewer = cls.User.objects.create_user(username='perm_viewer', password='pass123')

        cls.project = ProjectService.create_project(
            name='Permission Project',
            user=cls.owner,
        )
        ProjectService.add_member(cls.project, cls.admin.id, role=ProjectMember.ROLE_ADMIN)
        ProjectService.add_member(cls.project, cls.viewer.id, role=ProjectMember.ROLE_VIEWER)

    def test_get_user_role_and_permissions(self):
        owner_role = ProjectPermissions.get_user_role(self.project, self.owner)
        admin_role = ProjectPermissions.get_user_role(self.project, self.admin)
        viewer_role = ProjectPermissions.get_user_role(self.project, self.viewer)

        self.assertEqual(owner_role, ProjectMember.ROLE_OWNER)
        self.assertEqual(admin_role, ProjectMember.ROLE_ADMIN)
        self.assertEqual(viewer_role, ProjectMember.ROLE_VIEWER)

        owner_permissions = ProjectPermissions.get_user_permissions(self.project, self.owner)
        self.assertIn(ProjectPermissions.PERMISSION_DELETE, owner_permissions)
        self.assertNotIn(ProjectPermissions.PERMISSION_DELETE, ProjectPermissions.get_user_permissions(self.project, self.viewer))

    def test_can_manage_member_logic(self):
        can_owner_manage_admin = ProjectPermissions.can_manage_member(self.project, self.owner, self.admin)
        can_admin_manage_owner = ProjectPermissions.can_manage_member(self.project, self.admin, self.owner)
        can_admin_manage_viewer = ProjectPermissions.can_manage_member(self.project, self.admin, self.viewer)

        self.assertTrue(can_owner_manage_admin)
        self.assertFalse(can_admin_manage_owner)
        self.assertTrue(can_admin_manage_viewer)

    def test_require_permission_decorator_allows_authorized_user(self):
        factory = RequestFactory()

        @require_edit
        def sample_view(request, project_id: str, project=None):
            return project.name if project else None

        request = factory.get('/projects/')
        request.user = self.owner

        response = sample_view(request, str(self.project.id))
        self.assertEqual(response, self.project.name)

    def test_require_permission_decorator_blocks_unauthorized_user(self):
        factory = RequestFactory()

        @require_edit
        def sample_view(request, project_id: str, project=None):
            return project.name if project else None

        request = factory.get('/projects/')
        request.user = self.viewer

        with self.assertRaises(PermissionDenied):
            sample_view(request, str(self.project.id))
