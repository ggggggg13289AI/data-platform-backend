import logging
from typing import Any

from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.shortcuts import get_object_or_404
from ninja import Router
from ninja.errors import HttpError
from ninja.pagination import paginate
from ninja_jwt.authentication import JWTAuth

from common.models import StudyProjectAssignment
from common.pagination import ProjectPagination, ReportPagination
from common.permissions import (
    ProjectPermissions,
    require_delete,
    require_edit,
    require_manage_members,
    require_manage_studies,
    require_view,
)
from project.models import Project, ProjectMember
from project.schemas import (
    AddMemberRequest,
    AddStudiesRequest,
    BatchAssignRequest,
    CreateProjectRequest,
    MemberInfo,
    ProjectDetailResponse,
    ProjectListItem,
    ProjectStatistics,
    ProjectStudyItem,
    RemoveStudiesRequest,
    UpdateMemberRoleRequest,
    UpdateProjectRequest,
    ProjectResourceItem,
)
from project.service import ProjectBatchLimitExceeded, ProjectService
from project.services.resource_aggregator import ResourceAggregator
from report.api import ReportDetailResponse

logger = logging.getLogger(__name__)

router = Router(auth=JWTAuth())


ASSIGNMENT_SORT_MAP = {
    '-assigned_at': '-assigned_at',
    'assigned_at': 'assigned_at',
    'patient_name': 'study__patient_name',
    '-patient_name': '-study__patient_name',
}

VALID_MEMBER_ROLES = {choice[0] for choice in ProjectMember.ROLE_CHOICES}


@router.get('/', response=list[ProjectListItem])
@paginate(ProjectPagination)
def list_projects(
    request,
    q: str = '',
    status: str | None = None,
    tags: str | None = None,
    created_by: str | None = None,
    sort: str = ProjectService.DEFAULT_SORT,
):
    queryset = ProjectService.get_projects_queryset(
        user=request.user,
        q=q or None,
        status=status,
        tags=tags,
        created_by=created_by,
        sort=sort,
    )
    return queryset


@router.post('/', response={201: ProjectDetailResponse})
def create_project(request, payload: CreateProjectRequest):
    # JWT authentication ensures request.user is authenticated
    # No additional authentication check needed

    project = ProjectService.create_project(
        name=payload.name,
        user=request.user,
        description=payload.description or '',
        tags=payload.tags or [],
        status=payload.status or Project.STATUS_ACTIVE,
        settings=payload.settings or {},
    )

    member_count = project.project_members.count()  # type: ignore[attr-defined]

    return 201, ProjectDetailResponse(
        **project.to_dict(),
        member_count=member_count,
        user_role=ProjectMember.ROLE_OWNER,
        user_permissions=ProjectPermissions.ROLE_PERMISSIONS[ProjectMember.ROLE_OWNER],
        can_manage_members=True,
        can_assign_studies=True,
        can_archive=True,
    )


# Batch assign studies to multiple projects (static route before dynamic routes)
@router.post('/batch-assign', response=dict[str, Any])
def batch_assign_studies(request, payload: BatchAssignRequest):
    """
    批量將研究分配到多個專案

    將指定的研究 (exam_ids) 分配到多個專案 (project_ids)。
    只會處理用戶有 MANAGE_STUDIES 權限的專案。
    """
    results = []
    total_assignments = 0
    logger.info(f'request.user {request.user}')

    for project_id in payload.project_ids:
        project = get_object_or_404(Project, id=project_id)

        if not ProjectPermissions.check_permission(
            project,
            request.user,
            ProjectPermissions.PERMISSION_MANAGE_STUDIES,
        ):
            continue

        try:
            result = ProjectService.add_studies_to_project(
                project=project,
                exam_ids=payload.exam_ids,
                user=request.user,
            )
        except ValueError:
            continue

        total_assignments += result['added_count']
        results.append(
            {
                'project_id': str(project.id),
                'project_name': project.name,
                'added_count': result['added_count'],
            }
        )

    return {
        'success': True,
        'total_assignments': total_assignments,
        'projects_updated': len(results),
        'details': results,
    }


@router.get('/{project_id}', response=ProjectDetailResponse)
@require_view
def get_project(request, project_id: str, project=None):
    if project is None:
        raise Http404('專案不存在')
    member_count = project.project_members.count()
    user_role = ProjectPermissions.get_user_role(project, request.user)
    user_permissions = ProjectPermissions.get_user_permissions(project, request.user)
    permission_flags = ProjectPermissions.get_permission_flags(project, request.user)

    return ProjectDetailResponse(
        **project.to_dict(),
        member_count=member_count,
        user_role=user_role,
        user_permissions=user_permissions,
        can_manage_members=permission_flags.get('can_manage_members', False),
        can_assign_studies=permission_flags.get('can_assign_studies', False),
        can_archive=permission_flags.get('can_archive', False),
    )


@router.put('/{project_id}', response=ProjectDetailResponse)
@require_edit
def update_project(request, project_id: str, payload: UpdateProjectRequest, project=None):
    if project is None:
        raise Http404('專案不存在')

    update_fields = []

    # Data driven update (Linus rule: eliminate repetitive if/else)
    fields_to_update = [
        'name', 'description', 'tags', 'status', 'settings', 'metadata'
    ]

    for field in fields_to_update:
        value = getattr(payload, field)
        if value is not None:
            setattr(project, field, value)
            update_fields.append(field)

    if update_fields:
        project.save(update_fields=update_fields)

    member_count = project.project_members.count()
    user_role = ProjectPermissions.get_user_role(project, request.user)
    user_permissions = ProjectPermissions.get_user_permissions(project, request.user)
    permission_flags = ProjectPermissions.get_permission_flags(project, request.user)

    return ProjectDetailResponse(
        **project.to_dict(),
        member_count=member_count,
        user_role=user_role,
        user_permissions=user_permissions,
        can_manage_members=permission_flags.get('can_manage_members', False),
        can_assign_studies=permission_flags.get('can_assign_studies', False),
        can_archive=permission_flags.get('can_archive', False),
    )


@router.delete('/{project_id}', response={204: None})
@require_delete
def delete_project(request, project_id: str, project=None):
    if project is None:
        raise Http404('專案不存在')

    project.delete()
    return 204, None


@router.post('/{project_id}/archive', response={200: dict[str, Any]})
@require_edit
def archive_project(request, project_id: str, project=None):
    if project is None:
        raise Http404('專案不存在')
    project.status = Project.STATUS_ARCHIVED
    project.save(update_fields=['status'])
    return {'success': True, 'status': Project.STATUS_ARCHIVED}


@router.post('/{project_id}/restore', response={200: dict[str, Any]})
@require_edit
def restore_project(request, project_id: str, project=None):
    if project is None:
        raise Http404('專案不存在')
    project.status = Project.STATUS_ACTIVE
    project.save(update_fields=['status'])
    return {'success': True, 'status': Project.STATUS_ACTIVE}


@router.post('/{project_id}/duplicate', response={201: ProjectDetailResponse})
@require_view
def duplicate_project(request, project_id: str, project=None):
    if project is None:
        raise Http404('專案不存在')
    duplicate = ProjectService.create_project(
        name=f'{project.name} (副本)',
        user=request.user,
        description=project.description,
        tags=list(project.tags),
        status=Project.STATUS_DRAFT,
        settings=dict(project.settings),
    )
    duplicate.metadata = dict(project.metadata)
    duplicate.save(update_fields=['metadata'])

    member_count = duplicate.project_members.count()  # type: ignore[attr-defined]

    return 201, ProjectDetailResponse(
        **duplicate.to_dict(),
        member_count=member_count,
        user_role=ProjectMember.ROLE_OWNER,
        user_permissions=ProjectPermissions.ROLE_PERMISSIONS[ProjectMember.ROLE_OWNER],
        can_manage_members=True,
        can_assign_studies=True,
        can_archive=True,
    )


@router.post('/{project_id}/studies', response={200: dict[str, Any]})
@require_manage_studies
def add_studies(request, project_id: str, payload: AddStudiesRequest, project=None):
    if project is None:
        raise Http404('專案不存在')
    try:
        result = ProjectService.add_studies_to_project(
            project=project,
            exam_ids=payload.exam_ids,
            user=request.user,
        )
    except ProjectBatchLimitExceeded as exc:
        import json
        error_detail = json.dumps({
            'code': 'too_many_items',
            'message': f'一次最多僅能處理 {exc.max_allowed} 筆資料',
            'requested_count': exc.requested_count,
            'max_batch_size': exc.max_allowed,
        }, ensure_ascii=False)
        raise HttpError(400, error_detail) from exc

    return {
        **result,
        'project_id': str(project.id),
        'project_name': project.name,
        'current_study_count': project.study_count,
    }


@router.delete('/{project_id}/studies', response={200: dict[str, Any]})
@require_manage_studies
def remove_studies(request, project_id: str, payload: RemoveStudiesRequest, project=None):
    if project is None:
        raise Http404('專案不存在')
    result = ProjectService.remove_studies_from_project(
        project=project,
        exam_ids=payload.exam_ids,
    )

    return {
        **result,
        'current_study_count': project.study_count,
    }


@router.get('/{project_id}/studies', response=list[ProjectStudyItem])
@paginate(ProjectPagination)
@require_view
def list_project_studies(request, project_id: str, sort: str = '-assigned_at', project=None):
    if project is None:
        raise Http404('專案不存在')
    sort_field = ASSIGNMENT_SORT_MAP.get(sort, '-assigned_at')
    assignments = (
        StudyProjectAssignment.objects.filter(project=project)
        .select_related('study', 'assigned_by')
        .order_by(sort_field)
    )

    # Return QuerySet directly to allow Pydantic validation/serialization from ORM objects
    # ProjectStudyItem includes a root_validator to flatten the structure
    return assignments


@router.get('/{project_id}/reports', response=list[ReportDetailResponse])
@paginate(ReportPagination)
@require_view
def list_project_reports(request, project_id: str, q: str = '', report_type: str | None = None, sort: str = '-verified_at', project=None):
    if project is None:
        raise Http404('專案不存在')
    return ProjectService.get_project_reports_queryset(
        project=project,
        q=q or None,
        report_type=report_type,
        sort=sort
    )


@router.post('/{project_id}/members', response=MemberInfo)
@require_manage_members
def add_member(request, project_id: str, payload: AddMemberRequest, project=None):
    if project is None:
        raise Http404('專案不存在')
    if payload.role not in VALID_MEMBER_ROLES:
        raise HttpError(400, '無效的角色設定')

    try:
        member = ProjectService.add_member(
            project=project,
            user_id=payload.user_id,
            role=payload.role,
        )
    except ValueError as exc:
        raise HttpError(400, str(exc)) from exc

    permissions = ProjectPermissions.ROLE_PERMISSIONS.get(member.role, [])
    member_data = member.to_dict()
    member_data['permissions'] = permissions

    return MemberInfo(**member_data)


@router.delete('/{project_id}/members/{user_id}', response={204: None})
@require_manage_members
def remove_member(request, project_id: str, user_id: str, project=None):
    if project is None:
        raise Http404('專案不存在')
    if str(request.user.id) == user_id:
        member = get_object_or_404(ProjectMember, project=project, user_id=user_id)
        if member.role == ProjectMember.ROLE_OWNER:
            raise HttpError(400, 'Owner 無法自行移除')
        member.delete()
        return 204, None

    try:
        ProjectService.remove_member(project, user_id)
    except ValueError as exc:
        raise HttpError(400, str(exc)) from exc

    return 204, None


@router.put('/{project_id}/members/{user_id}', response=MemberInfo)
def update_member_role(request, project_id: str, user_id: str, payload: UpdateMemberRoleRequest):
    project = get_object_or_404(Project, id=project_id)

    if ProjectPermissions.get_user_role(project, request.user) != ProjectMember.ROLE_OWNER:
        raise PermissionDenied('只有 Owner 可變更成員角色')

    if payload.role not in VALID_MEMBER_ROLES:
        raise HttpError(400, '無效的角色設定')

    try:
        member = ProjectService.update_member_role(
            project=project,
            user_id=user_id,
            new_role=payload.role,
        )
    except ValueError as exc:
        raise HttpError(400, str(exc)) from exc

    permissions = ProjectPermissions.ROLE_PERMISSIONS.get(member.role, [])
    member_data = member.to_dict()
    member_data['permissions'] = permissions

    return MemberInfo(**member_data)


@router.get('/{project_id}/members', response=list[MemberInfo])
@require_view
def list_members(request, project_id: str, project=None):
    if project is None:
        raise Http404('專案不存在')
    members = (
        ProjectMember.objects.filter(project=project)
        .select_related('user')
        .order_by('role', 'joined_at')
    )

    results = []
    for member in members:
        member_data = member.to_dict()
        member_data['permissions'] = ProjectPermissions.ROLE_PERMISSIONS.get(member.role, [])
        results.append(MemberInfo(**member_data))
    return results


@router.get('/{project_id}/statistics', response=ProjectStatistics)
@require_view
def get_statistics(request, project_id: str, project=None):
    if project is None:
        raise Http404('專案不存在')
    stats = ProjectService.get_project_statistics(project)
    return ProjectStatistics(**stats)


@router.get('/search', response=list[ProjectListItem])
@paginate(ProjectPagination)
def search_projects(request, q: str = '', status: str | None = None, tags: str | None = None, created_by: str | None = None, sort: str = ProjectService.DEFAULT_SORT):
    return ProjectService.get_projects_queryset(
        user=request.user,
        q=q or None,
        status=status,
        tags=tags,
        created_by=created_by,
        sort=sort,
    )


@router.get('/studies/{study_id}', response=dict[str, Any])
def get_study_projects(request, study_id: str):
    assignments = (
        StudyProjectAssignment.objects.filter(study_id=study_id)
        .select_related('project')
        .filter(project__project_members__user=request.user)
    )

    projects = []
    for assignment in assignments:
        project = assignment.project
        projects.append(
            {
                'id': str(project.id),
                'name': project.name,
                'status': project.status,
                'user_role': ProjectPermissions.get_user_role(project, request.user),
                'assigned_at': assignment.assigned_at.isoformat() if assignment.assigned_at else None,
            }
        )

    return {
        'exam_id': study_id,
        'projects': projects,
        'total_projects': len(projects),
    }

@router.get('/{project_id}/resources', response=dict[str, Any])
@require_view
def list_project_resources(
    request,
    project_id: str,
    resource_types: list[str] = Query(default=['study', 'report']),
    page: int = 1,
    page_size: int = 20,
    q: str = None,
    project=None
):
    """
    Unified project resources list (Studies + Reports).
    Aggregates resources based on StudyProjectAssignment (Accession Number).
    """
    if project is None:
        raise Http404('專案不存在')

    return ResourceAggregator.get_project_resources(
        project_id=project_id,
        resource_types=resource_types,
        page=page,
        page_size=page_size,
        q=q
    )
