"""
Service layer for Projects feature.

Encapsulates business logic for managing projects, members, and study assignments.
"""

from __future__ import annotations

from typing import Sequence, List, Dict

from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Count, Prefetch, Q, QuerySet

from .models import Project, ProjectMember, Study, StudyProjectAssignment

User = get_user_model()


class ProjectBatchLimitExceeded(ValueError):
    """Raised when batch operations exceed the allowed exam_id limit."""

    def __init__(self, requested_count: int, max_allowed: int):
        self.requested_count = requested_count
        self.max_allowed = max_allowed
        super().__init__(f'Batch size {requested_count} exceeds max allowed {max_allowed}')


class ProjectService:
    """專案服務類別"""

    DEFAULT_SORT = '-updated_at'
    MAX_BATCH_SIZE = 500

    ALLOWED_SORT_FIELDS = {
        'name',
        '-name',
        'created_at',
        '-created_at',
        'updated_at',
        '-updated_at',
        'study_count',
        '-study_count',
    }

    @staticmethod
    def create_project(
        name: str,
        user,
        description: str = '',
        tags: Sequence[str] | None = None,
        status: str = Project.STATUS_ACTIVE,
        settings: dict | None = None,
    ) -> Project:
        """建立專案"""
        with transaction.atomic():
            project = Project.objects.create(
                name=name,
                description=description or '',
                status=status or Project.STATUS_ACTIVE,
                tags=list(tags or []),
                settings=settings or {},
                created_by=user,
            )

            ProjectMember.objects.create(
                project=project,
                user=user,
                role=ProjectMember.ROLE_OWNER,
            )

            return project

    @classmethod
    def get_projects_queryset(
        cls,
        user,
        q: str | None = None,
        status: str | None = None,
        tags: str | Sequence[str] | None = None,
        created_by: str | None = None,
        sort: str = DEFAULT_SORT,
    ) -> QuerySet[Project]:
        """建立專案查詢集"""
        if user is None or not getattr(user, 'is_authenticated', False):
            return Project.objects.none()

        queryset = (
            Project.objects.filter(project_members__user=user)
            .select_related('created_by')
            .prefetch_related(
                Prefetch(
                    'project_members',
                    queryset=ProjectMember.objects.select_related('user'),
                )
            )
            .annotate(member_count=Count('project_members', distinct=True))
            .distinct()
        )

        if q:
            queryset = queryset.filter(Q(name__icontains=q) | Q(description__icontains=q))

        if status:
            queryset = queryset.filter(status=status)

        if tags:
            tag_list = tags.split(',') if isinstance(tags, str) else list(tags)
            for tag in filter(None, tag_list):
                queryset = queryset.filter(tags__contains=[tag])

        if created_by:
            queryset = queryset.filter(created_by_id=created_by)

        sort_field = sort if sort in cls.ALLOWED_SORT_FIELDS else cls.DEFAULT_SORT
        queryset = queryset.order_by(sort_field)

        return queryset

    @classmethod
    def add_studies_to_project(cls, project: Project, exam_ids: Sequence[str], user) -> dict:
        """批量新增研究到專案"""
        normalized_ids = [exam_id for exam_id in dict.fromkeys(exam_ids) if exam_id]
        if not normalized_ids:
            return {
                'success': True,
                'added_count': 0,
                'skipped_count': 0,
                'failed_items': [],
                'requested_count': 0,
                'max_batch_size': cls.MAX_BATCH_SIZE,
            }

        if len(normalized_ids) > cls.MAX_BATCH_SIZE:
            raise ProjectBatchLimitExceeded(len(normalized_ids), cls.MAX_BATCH_SIZE)

        with transaction.atomic():
            studies = Study.objects.filter(exam_id__in=normalized_ids)
            found_ids = set(studies.values_list('exam_id', flat=True))
            missing_ids = sorted(set(normalized_ids) - found_ids)

            failed_items: List[Dict[str, str]] = [
                {'exam_id': exam_id, 'reason': 'not_found'}
                for exam_id in missing_ids
            ]

            existing = set(
                StudyProjectAssignment.objects.filter(
                    project=project,
                    study_id__in=normalized_ids,
                ).values_list('study_id', flat=True)
            )

            new_exam_ids = [exam_id for exam_id in normalized_ids if exam_id not in existing]

            failed_items.extend(
                {'exam_id': exam_id, 'reason': 'already_assigned'} for exam_id in existing
            )

            assignments = [
                StudyProjectAssignment(
                    project=project,
                    study_id=exam_id,
                    assigned_by=user,
                )
                for exam_id in new_exam_ids
            ]

            StudyProjectAssignment.objects.bulk_create(assignments)

            added_count = len(new_exam_ids)
            if added_count:
                project.increment_study_count(added_count)

            return {
                'success': True,
                'added_count': added_count,
                'skipped_count': len(existing),
                'failed_items': failed_items,
                'requested_count': len(normalized_ids),
                'max_batch_size': cls.MAX_BATCH_SIZE,
            }

    @staticmethod
    def remove_studies_from_project(project: Project, exam_ids: Sequence[str]) -> dict:
        """批量移除研究"""
        normalized_ids = [exam_id for exam_id in dict.fromkeys(exam_ids) if exam_id]
        if not normalized_ids:
            return {'success': True, 'removed_count': 0}

        with transaction.atomic():
            deleted_count, _ = StudyProjectAssignment.objects.filter(
                project=project,
                study_id__in=normalized_ids,
            ).delete()

            if deleted_count:
                project.decrement_study_count(deleted_count)

            return {'success': True, 'removed_count': deleted_count}

    @staticmethod
    def add_member(project: Project, user_id: str, role: str = ProjectMember.ROLE_VIEWER) -> ProjectMember:
        """新增成員"""
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist as exc:
            raise ValueError('使用者不存在') from exc

        if ProjectMember.objects.filter(project=project, user=user).exists():
            raise ValueError('使用者已是專案成員')

        return ProjectMember.objects.create(
            project=project,
            user=user,
            role=role,
        )

    @staticmethod
    def remove_member(project: Project, user_id: str) -> dict:
        """移除成員"""
        try:
            member = ProjectMember.objects.get(project=project, user_id=user_id)
        except ProjectMember.DoesNotExist as exc:
            raise ValueError('專案成員不存在') from exc

        if member.role == ProjectMember.ROLE_OWNER:
            raise ValueError('無法移除專案 Owner')

        member.delete()
        return {'success': True}

    @staticmethod
    def update_member_role(project: Project, user_id: str, new_role: str) -> ProjectMember:
        """更新成員角色"""
        try:
            member = ProjectMember.objects.get(project=project, user_id=user_id)
        except ProjectMember.DoesNotExist as exc:
            raise ValueError('專案成員不存在') from exc

        if member.role == ProjectMember.ROLE_OWNER or new_role == ProjectMember.ROLE_OWNER:
            raise ValueError('無法變更 Owner 角色')

        member.role = new_role
        member.save(update_fields=['role'])
        return member

    @staticmethod
    def get_project_statistics(project: Project) -> dict:
        """取得專案統計資訊"""
        modality_dist = (
            StudyProjectAssignment.objects.filter(project=project)
            .values('study__exam_source')
            .annotate(count=Count('id'))
            .order_by('-count')
        )
        modality_distribution = {
            (item['study__exam_source'] or 'unknown'): item['count'] for item in modality_dist
        }

        member_count = ProjectMember.objects.filter(project=project).count()

        last_assignment = (
            StudyProjectAssignment.objects.filter(project=project)
            .order_by('-assigned_at')
            .first()
        )

        last_activity_at = last_assignment.assigned_at if last_assignment else None

        return {
            'project_id': str(project.id),
            'project_name': project.name,
            'study_count': project.study_count,
            'member_count': member_count,
            'created_at': project.created_at.isoformat() if project.created_at else None,
            'updated_at': project.updated_at.isoformat() if project.updated_at else None,
            'last_activity_at': last_activity_at.isoformat() if last_activity_at else None,
            'modality_distribution': modality_distribution,
        }
