from datetime import datetime
from typing import Any, Dict, List, Optional

from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.shortcuts import get_object_or_404
from ninja import Router, Schema
from ninja.errors import HttpError
from ninja.pagination import paginate
from ninja_jwt.authentication import JWTAuth

from .models import Project, ProjectMember, StudyProjectAssignment
from .pagination import ProjectPagination
from .permissions import (
    ProjectPermissions,
    require_delete,
    require_edit,
    require_manage_members,
    require_manage_studies,
    require_view,
)
from .project_service import ProjectService


router = Router(tags=['projects'])


class CreateProjectRequest(Schema):
    name: str
    description: Optional[str] = ''
    tags: List[str] = []
    status: Optional[str] = Project.STATUS_ACTIVE
    settings: Optional[Dict[str, Any]] = {}


class UpdateProjectRequest(Schema):
    name: Optional[str] = None
    description: Optional[str] = None
    tags: Optional[List[str]] = None
    status: Optional[str] = None
    settings: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None


class UserInfo(Schema):
    id: str
    name: str
    email: Optional[str] = None


class ProjectListItem(Schema):
    id: str
    name: str
    description: str
    status: str
    tags: List[str]
    study_count: int
    member_count: int
    created_at: datetime
    updated_at: datetime
    created_by: UserInfo
    user_role: Optional[str] = None


class ProjectDetailResponse(Schema):
    id: str
    name: str
    description: str
    status: str
    tags: List[str]
    study_count: int
    member_count: int
    created_at: datetime
    updated_at: datetime
    created_by: UserInfo
    user_role: Optional[str]
    user_permissions: List[str]
    settings: Dict[str, Any]
    metadata: Dict[str, Any]


class AddStudiesRequest(Schema):
    exam_ids: List[str]


class RemoveStudiesRequest(Schema):
    exam_ids: List[str]


class BatchAssignRequest(Schema):
    exam_ids: List[str]
    project_ids: List[str]


class AddMemberRequest(Schema):
    user_id: str
    role: str = ProjectMember.ROLE_VIEWER


class UpdateMemberRoleRequest(Schema):
    role: str


class MemberInfo(Schema):
    user_id: str
    name: str
    email: Optional[str]
    role: str
    joined_at: datetime
    permissions: List[str]


class StudyListItem(Schema):
    exam_id: str
    patient_name: str
    exam_date: Optional[str]
    modality: Optional[str]
    assigned_at: datetime
    assigned_by: UserInfo


class ProjectStatistics(Schema):
    project_id: str
    project_name: str
    study_count: int
    member_count: int
    created_at: datetime
    updated_at: datetime
    last_activity_at: Optional[datetime] = None
    modality_distribution: Dict[str, int]


ASSIGNMENT_SORT_MAP = {
    '-assigned_at': '-assigned_at',
    'assigned_at': 'assigned_at',
    'patient_name': 'study__patient_name',
    '-patient_name': '-study__patient_name',
}

VALID_MEMBER_ROLES = {choice[0] for choice in ProjectMember.ROLE_CHOICES}


@router.get('/projects', response=List[ProjectListItem], auth=JWTAuth())
@paginate(ProjectPagination)
def list_projects(
    request,
    q: str = '',
    status: Optional[str] = None,
    tags: Optional[str] = None,
    created_by: Optional[str] = None,
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


@router.post('/projects', response={201: ProjectDetailResponse}, auth=JWTAuth())
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

    member_count = project.project_members.count()

    return 201, ProjectDetailResponse(
        **project.to_dict(),
        member_count=member_count,
        user_role=ProjectMember.ROLE_OWNER,
        user_permissions=ProjectPermissions.ROLE_PERMISSIONS[ProjectMember.ROLE_OWNER],
    )


@router.get('/projects/{project_id}', response=ProjectDetailResponse)
@require_view
def get_project(request, project_id: str, project=None):
    if project is None:
        raise Http404('專案不存在')
    member_count = project.project_members.count()
    user_role = ProjectPermissions.get_user_role(project, request.user)
    user_permissions = ProjectPermissions.get_user_permissions(project, request.user)

    return ProjectDetailResponse(
        **project.to_dict(),
        member_count=member_count,
        user_role=user_role,
        user_permissions=user_permissions,
    )


@router.put('/projects/{project_id}', response=ProjectDetailResponse)
@require_edit
def update_project(request, project_id: str, payload: UpdateProjectRequest, project=None):
    if project is None:
        raise Http404('專案不存在')
    update_fields = []

    if payload.name is not None:
        project.name = payload.name
        update_fields.append('name')
    if payload.description is not None:
        project.description = payload.description
        update_fields.append('description')
    if payload.tags is not None:
        project.tags = payload.tags
        update_fields.append('tags')
    if payload.status is not None:
        project.status = payload.status
        update_fields.append('status')
    if payload.settings is not None:
        project.settings = payload.settings
        update_fields.append('settings')
    if payload.metadata is not None:
        project.metadata = payload.metadata
        update_fields.append('metadata')

    if update_fields:
        project.save(update_fields=update_fields)

    member_count = project.project_members.count()
    user_role = ProjectPermissions.get_user_role(project, request.user)
    user_permissions = ProjectPermissions.get_user_permissions(project, request.user)

    return ProjectDetailResponse(
        **project.to_dict(),
        member_count=member_count,
        user_role=user_role,
        user_permissions=user_permissions,
    )


@router.delete('/projects/{project_id}', response={204: None})
@require_delete
def delete_project(request, project_id: str, project=None):
    if project is None:
        raise Http404('專案不存在')
    project.delete()
    return 204, None


@router.post('/projects/{project_id}/archive', response={200: Dict[str, Any]})
@require_edit
def archive_project(request, project_id: str, project=None):
    if project is None:
        raise Http404('專案不存在')
    project.status = Project.STATUS_ARCHIVED
    project.save(update_fields=['status'])
    return {'success': True, 'status': Project.STATUS_ARCHIVED}


@router.post('/projects/{project_id}/restore', response={200: Dict[str, Any]})
@require_edit
def restore_project(request, project_id: str, project=None):
    if project is None:
        raise Http404('專案不存在')
    project.status = Project.STATUS_ACTIVE
    project.save(update_fields=['status'])
    return {'success': True, 'status': Project.STATUS_ACTIVE}


@router.post('/projects/{project_id}/duplicate', response={201: ProjectDetailResponse})
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

    member_count = duplicate.project_members.count()

    return 201, ProjectDetailResponse(
        **duplicate.to_dict(),
        member_count=member_count,
        user_role=ProjectMember.ROLE_OWNER,
        user_permissions=ProjectPermissions.ROLE_PERMISSIONS[ProjectMember.ROLE_OWNER],
    )


@router.post('/projects/{project_id}/studies', response={200: Dict[str, Any]})
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
    except ValueError as exc:
        raise HttpError(400, str(exc)) from exc

    return {
        **result,
        'project_name': project.name,
        'current_study_count': project.study_count,
    }


@router.delete('/projects/{project_id}/studies', response={200: Dict[str, Any]})
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


@router.get('/projects/{project_id}/studies', response=List[StudyListItem])
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
    return assignments


@router.post('/projects/{project_id}/members', response=MemberInfo)
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


@router.delete('/projects/{project_id}/members/{user_id}', response={204: None})
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


@router.put('/projects/{project_id}/members/{user_id}', response=MemberInfo, auth=JWTAuth())
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


@router.get('/projects/{project_id}/members', response=List[MemberInfo])
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


@router.get('/projects/{project_id}/statistics', response=ProjectStatistics)
@require_view
def get_statistics(request, project_id: str, project=None):
    if project is None:
        raise Http404('專案不存在')
    stats = ProjectService.get_project_statistics(project)
    return ProjectStatistics(**stats)


@router.get('/projects/search', response=List[ProjectListItem], auth=JWTAuth())
@paginate(ProjectPagination)
def search_projects(request, q: str = '', status: Optional[str] = None, tags: Optional[str] = None, created_by: Optional[str] = None, sort: str = ProjectService.DEFAULT_SORT):
    return ProjectService.get_projects_queryset(
        user=request.user,
        q=q or None,
        status=status,
        tags=tags,
        created_by=created_by,
        sort=sort,
    )


@router.get('/studies/{study_id}/projects', response=Dict[str, Any], auth=JWTAuth())
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


@router.post('/projects/batch-assign', response=Dict[str, Any], auth=JWTAuth())
@router.post('/projects/batch-assign/', response=Dict[str, Any], auth=JWTAuth())
def batch_assign_studies(request, payload: BatchAssignRequest):
    results = []
    total_assignments = 0

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
