import json
import logging
import time
from dataclasses import asdict
from typing import Any

from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.http import Http404
from django.shortcuts import get_object_or_404
from ninja import Query, Router
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
    BatchAssignByQueryDetail,
    BatchAssignByQueryRequest,
    BatchAssignByQueryResponse,
    BatchAssignQueryFilters,
    BatchAssignRequest,
    CreateProjectRequest,
    MemberInfo,
    ProjectAdvancedSearchRequest,
    ProjectDetailResponse,
    ProjectListAdvancedSearchRequest,
    ProjectListItem,
    ProjectSearchResponse,
    ProjectStatistics,
    ProjectStudyItem,
    RemoveStudiesRequest,
    UpdateMemberRoleRequest,
    UpdateProjectRequest,
)
from project.service import ProjectBatchLimitExceeded, ProjectService
from project.services.resource_aggregator import ResourceAggregator
from project.services.search_registry import ProjectSearchRegistry
from report.api import ReportDetailResponse
from study.services import StudyService

logger = logging.getLogger(__name__)

router = Router(auth=JWTAuth())

QUERY_ASSIGN_SERVER_CAP = 10_000
FAILED_ITEMS_SAMPLE_LIMIT = 20


ASSIGNMENT_SORT_MAP = {
    "-assigned_at": "-assigned_at",
    "assigned_at": "assigned_at",
    "patient_name": "study__patient_name",
    "-patient_name": "-study__patient_name",
}

VALID_MEMBER_ROLES = {choice[0] for choice in ProjectMember.ROLE_CHOICES}
SEARCH_RESULT_MULTIPLIER = 3
MAX_PROVIDER_RESULTS = 200

#
# @router.get('/', response=list[ProjectListItem])
# @paginate(ProjectPagination)
# def list_projects(
#     request,
#     q: str = '',
#     status: str | None = None,
#     tags: str | None = None,
#     created_by: str | None = None,
#     sort: str = ProjectService.DEFAULT_SORT,
# ):
#     queryset = ProjectService.get_projects_queryset(
#         user=request.user,
#         q=q or None,
#         status=status,
#         tags=tags,
#         created_by=created_by,
#         sort=sort,
#     )
#     return queryset
#
#
# @router.get('', response=list[ProjectListItem])
# @paginate(ProjectPagination)
# def list_projects_no_slash(
#     request,
#     q: str = '',
#     status: str | None = None,
#     tags: str | None = None,
#     created_by: str | None = None,
#     sort: str = ProjectService.DEFAULT_SORT,
# ):
#     return list_projects(
#         request,
#         q=q,
#         status=status,
#         tags=tags,
#         created_by=created_by,
#         sort=sort,
#     )


@router.get("/", response=list[ProjectListItem])
@paginate(ProjectPagination)
def list_projects(
    request,
    q: str = "",
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


@router.get("", response=list[ProjectListItem])
@paginate(ProjectPagination)
def list_projects_no_slash(
    request,
    q: str = "",
    status: str | None = None,
    tags: str | None = None,
    created_by: str | None = None,
    sort: str = ProjectService.DEFAULT_SORT,
):
    # 直接返回 queryset，避免雙重分頁裝飾器衝突
    queryset = ProjectService.get_projects_queryset(
        user=request.user,
        q=q or None,
        status=status,
        tags=tags,
        created_by=created_by,
        sort=sort,
    )
    return queryset


@router.post("/", response={201: ProjectDetailResponse})
def create_project(request, payload: CreateProjectRequest):
    # JWT authentication ensures request.user is authenticated
    # No additional authentication check needed

    # region agent log
    try:
        with open(
            "/mnt/d/00_Chen/spider/image_data_platform/.cursor/debug.log", "a", encoding="utf-8"
        ) as debug_log_file:
            debug_log_file.write(
                json.dumps(
                    {
                        "sessionId": "debug-session",
                        "runId": "run1",
                        "hypothesisId": "H5-route-match",
                        "location": "project/api.py:create_project",
                        "message": "enter_create_project",
                        "data": {
                            "name": payload.name,
                            "tags_count": len(payload.tags or []),
                            "status": payload.status or Project.STATUS_ACTIVE,
                            "via": "slash",
                        },
                        "timestamp": int(time.time() * 1000),
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )
    except Exception:
        pass
    # endregion

    project = ProjectService.create_project(
        name=payload.name,
        user=request.user,
        description=payload.description or "",
        tags=payload.tags or [],
        status=payload.status or Project.STATUS_ACTIVE,
        settings=payload.settings or {},
    )

    member_count = project.project_members.count()  # type: ignore[attr-defined]

    # region agent log
    try:
        with open(
            "/mnt/d/00_Chen/spider/image_data_platform/.cursor/debug.log", "a", encoding="utf-8"
        ) as debug_log_file:
            debug_log_file.write(
                json.dumps(
                    {
                        "sessionId": "debug-session",
                        "runId": "run1",
                        "hypothesisId": "H5-route-match",
                        "location": "project/api.py:create_project",
                        "message": "exit_create_project",
                        "data": {
                            "project_id": str(project.id),
                            "member_count": member_count,
                            "via": "slash",
                        },
                        "timestamp": int(time.time() * 1000),
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )
    except Exception:
        pass
    # endregion

    return 201, ProjectDetailResponse(
        **project.to_dict(),
        member_count=member_count,
        user_role=ProjectMember.ROLE_OWNER,
        user_permissions=ProjectPermissions.ROLE_PERMISSIONS[ProjectMember.ROLE_OWNER],
        can_manage_members=True,
        can_assign_studies=True,
        can_archive=True,
    )


# Allow POST without trailing slash to avoid APPEND_SLASH redirect for APIs
@router.post("", response={201: ProjectDetailResponse})
def create_project_no_slash(request, payload: CreateProjectRequest):
    # region agent log
    try:
        with open(
            "/mnt/d/00_Chen/spider/image_data_platform/.cursor/debug.log", "a", encoding="utf-8"
        ) as debug_log_file:
            debug_log_file.write(
                json.dumps(
                    {
                        "sessionId": "debug-session",
                        "runId": "run1",
                        "hypothesisId": "H5-route-match",
                        "location": "project/api.py:create_project_no_slash",
                        "message": "enter_create_project_no_slash",
                        "data": {
                            "name": payload.name,
                            "tags_count": len(payload.tags or []),
                            "status": payload.status or Project.STATUS_ACTIVE,
                            "via": "no_slash",
                        },
                        "timestamp": int(time.time() * 1000),
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )
    except Exception:
        pass
    # endregion

    result = create_project(request, payload)

    # region agent log
    try:
        with open(
            "/mnt/d/00_Chen/spider/image_data_platform/.cursor/debug.log", "a", encoding="utf-8"
        ) as debug_log_file:
            debug_log_file.write(
                json.dumps(
                    {
                        "sessionId": "debug-session",
                        "runId": "run1",
                        "hypothesisId": "H5-route-match",
                        "location": "project/api.py:create_project_no_slash",
                        "message": "exit_create_project_no_slash",
                        "data": {
                            "via": "no_slash",
                            "status_code": result[0] if isinstance(result, tuple) else None,
                        },
                        "timestamp": int(time.time() * 1000),
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )
    except Exception:
        pass
    # endregion

    return result


# Batch assign studies to multiple projects (static route before dynamic routes)
@router.post("/batch-assign", response=dict[str, Any])
def batch_assign_studies(request, payload: BatchAssignRequest):
    """
    批量將研究分配到多個專案

    將指定的研究 (exam_ids) 分配到多個專案 (project_ids)。
    只會處理用戶有 MANAGE_STUDIES 權限的專案。
    """
    requested_count = len(payload.exam_ids)
    if requested_count > ProjectService.MAX_BATCH_SIZE:
        error_detail = json.dumps(
            {
                "code": "too_many_items",
                "message": f"一次最多僅能處理 {ProjectService.MAX_BATCH_SIZE} 筆資料",
                "requested_count": requested_count,
                "max_batch_size": ProjectService.MAX_BATCH_SIZE,
            },
            ensure_ascii=False,
        )
        raise HttpError(400, error_detail)

    results = []
    total_assignments = 0
    logger.info(f"request.user {request.user}")

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
        except ProjectBatchLimitExceeded as exc:
            error_detail = json.dumps(
                {
                    "code": "too_many_items",
                    "message": f"一次最多僅能處理 {exc.max_allowed} 筆資料",
                    "requested_count": exc.requested_count,
                    "max_batch_size": exc.max_allowed,
                },
                ensure_ascii=False,
            )
            raise HttpError(400, error_detail) from exc

        total_assignments += result["added_count"]
        results.append(
            {
                "project_id": str(project.id),
                "project_name": project.name,
                "added_count": result["added_count"],
            }
        )

    return {
        "success": True,
        "total_assignments": total_assignments,
        "projects_updated": len(results),
        "details": results,
    }


@router.post("/batch-assign/query", response={200: BatchAssignByQueryResponse})
def batch_assign_studies_by_query(request, payload: BatchAssignByQueryRequest):
    """
    依查詢條件批次將研究分配到多個專案。
    """
    filters = payload.filters or BatchAssignQueryFilters()
    effective_max_batch = min(
        payload.max_batch_size or QUERY_ASSIGN_SERVER_CAP, QUERY_ASSIGN_SERVER_CAP
    )

    def normalize_single(value):
        if isinstance(value, list):
            return value[0] if value else None
        return value

    def normalize_to_list(value):
        if value is None:
            return None
        if isinstance(value, list):
            return [v for v in value if v]
        return [value] if value else None

    matched_count = StudyService.count_studies(
        q=filters.q,
        exam_status=normalize_single(filters.exam_status),
        exam_source=normalize_single(filters.exam_source),
        exam_equipment=filters.exam_equipment,
        application_order_no=filters.application_order_no,
        patient_gender=normalize_to_list(filters.patient_gender),
        exam_description=filters.exam_description,
        exam_room=filters.exam_room,
        patient_age_min=filters.patient_age_min,
        patient_age_max=filters.patient_age_max,
        start_date=filters.start_date,
        end_date=filters.end_date,
        exam_item=filters.exam_item,
    )

    if matched_count > effective_max_batch:
        error_detail = json.dumps(
            {
                "code": "too_many_items",
                "message": f"一次最多僅能處理 {effective_max_batch} 筆資料",
                "requested_count": matched_count,
                "max_batch_size": effective_max_batch,
            },
            ensure_ascii=False,
        )
        raise HttpError(400, error_detail)

    exam_ids = StudyService.get_exam_ids_by_filters(
        q=filters.q,
        exam_status=normalize_single(filters.exam_status),
        exam_source=normalize_single(filters.exam_source),
        exam_equipment=filters.exam_equipment,
        application_order_no=filters.application_order_no,
        patient_gender=normalize_to_list(filters.patient_gender),
        exam_description=filters.exam_description,
        exam_room=filters.exam_room,
        patient_age_min=filters.patient_age_min,
        patient_age_max=filters.patient_age_max,
        start_date=filters.start_date,
        end_date=filters.end_date,
        sort="order_datetime_desc",
        limit=effective_max_batch,
        exam_item=filters.exam_item,
    )

    exam_ids = list(dict.fromkeys(exam_ids))
    if not exam_ids:
        return BatchAssignByQueryResponse(
            success=True,
            matched_count=matched_count,
            max_batch_size=effective_max_batch,
            projects_updated=0,
            details=[],
        )

    def chunked(sequence: list[str], size: int) -> list[list[str]]:
        return [sequence[i : i + size] for i in range(0, len(sequence), size)]

    def assign_to_project(project, ids: list[str]):
        added_total = 0
        skipped_total = 0
        failed_items: list[dict[str, str]] = []

        for batch in chunked(ids, ProjectService.MAX_BATCH_SIZE):
            result = ProjectService.add_studies_to_project(
                project=project,
                exam_ids=batch,
                user=request.user,
            )
            added_total += result.get("added_count", 0)
            skipped_total += result.get("skipped_count", 0)
            failed_items.extend(result.get("failed_items", []))

        return added_total, skipped_total, failed_items

    details: list[BatchAssignByQueryDetail] = []
    projects_with_permission = 0
    total_added = 0

    for project_id in payload.project_ids:
        project = get_object_or_404(Project, id=project_id)

        if not ProjectPermissions.check_permission(
            project,
            request.user,
            ProjectPermissions.PERMISSION_MANAGE_STUDIES,
        ):
            details.append(
                BatchAssignByQueryDetail(
                    project_id=str(project.id),
                    project_name=project.name,
                    added_count=0,
                    skipped_count=0,
                    failed_items_sample=[],
                    failed_items_truncated=False,
                    failed_items_sample_limit=FAILED_ITEMS_SAMPLE_LIMIT,
                    failed_reason="permission_denied",
                )
            )
            continue

        projects_with_permission += 1
        added_count, skipped_count, failed_items = assign_to_project(project, exam_ids)
        total_added += added_count

        failed_sample = failed_items[:FAILED_ITEMS_SAMPLE_LIMIT]
        details.append(
            BatchAssignByQueryDetail(
                project_id=str(project.id),
                project_name=project.name,
                added_count=added_count,
                skipped_count=skipped_count,
                failed_items_sample=[
                    {"exam_id": item.get("exam_id", ""), "reason": item.get("reason", "")}
                    for item in failed_sample
                ],
                failed_items_truncated=len(failed_items) > FAILED_ITEMS_SAMPLE_LIMIT,
                failed_items_sample_limit=FAILED_ITEMS_SAMPLE_LIMIT,
                failed_reason=None,
            )
        )

    if projects_with_permission == 0:
        raise HttpError(403, "permission_denied")

    return BatchAssignByQueryResponse(
        success=True,
        matched_count=matched_count,
        max_batch_size=effective_max_batch,
        projects_updated=projects_with_permission,
        details=details,
    )


@router.get("/{project_id}", response=ProjectDetailResponse)
@require_view
def get_project(request, project_id: str, project=None):
    if project is None:
        raise Http404("專案不存在")
    member_count = project.project_members.count()
    user_role = ProjectPermissions.get_user_role(project, request.user)
    user_permissions = ProjectPermissions.get_user_permissions(project, request.user)
    permission_flags = ProjectPermissions.get_permission_flags(project, request.user)

    return ProjectDetailResponse(
        **project.to_dict(),
        member_count=member_count,
        user_role=user_role,
        user_permissions=user_permissions,
        can_manage_members=permission_flags.get("can_manage_members", False),
        can_assign_studies=permission_flags.get("can_assign_studies", False),
        can_archive=permission_flags.get("can_archive", False),
    )


@router.put("/{project_id}", response=ProjectDetailResponse)
@require_edit
def update_project(request, project_id: str, payload: UpdateProjectRequest, project=None):
    if project is None:
        raise Http404("專案不存在")

    update_fields = []

    # Data driven update (Linus rule: eliminate repetitive if/else)
    fields_to_update = ["name", "description", "tags", "status", "settings", "metadata"]

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
        can_manage_members=permission_flags.get("can_manage_members", False),
        can_assign_studies=permission_flags.get("can_assign_studies", False),
        can_archive=permission_flags.get("can_archive", False),
    )


@router.delete("/{project_id}", response={204: None})
@require_delete
def delete_project(request, project_id: str, project=None):
    if project is None:
        raise Http404("專案不存在")

    project.delete()
    return 204, None


@router.post("/{project_id}/archive", response={200: dict[str, Any]})
@require_edit
def archive_project(request, project_id: str, project=None):
    if project is None:
        raise Http404("專案不存在")
    project.status = Project.STATUS_ARCHIVED
    project.save(update_fields=["status"])
    return {"success": True, "status": Project.STATUS_ARCHIVED}


@router.post("/{project_id}/restore", response={200: dict[str, Any]})
@require_edit
def restore_project(request, project_id: str, project=None):
    if project is None:
        raise Http404("專案不存在")
    project.status = Project.STATUS_ACTIVE
    project.save(update_fields=["status"])
    return {"success": True, "status": Project.STATUS_ACTIVE}


@router.post("/{project_id}/duplicate", response={201: ProjectDetailResponse})
@require_view
def duplicate_project(request, project_id: str, project=None):
    if project is None:
        raise Http404("專案不存在")
    duplicate = ProjectService.create_project(
        name=f"{project.name} (副本)",
        user=request.user,
        description=project.description,
        tags=list(project.tags),
        status=Project.STATUS_DRAFT,
        settings=dict(project.settings),
    )
    duplicate.metadata = dict(project.metadata)
    duplicate.save(update_fields=["metadata"])

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


@router.post("/{project_id}/studies", response={200: dict[str, Any]})
@require_manage_studies
def add_studies(request, project_id: str, payload: AddStudiesRequest, project=None):
    if project is None:
        raise Http404("專案不存在")
    try:
        result = ProjectService.add_studies_to_project(
            project=project,
            exam_ids=payload.exam_ids,
            user=request.user,
        )
    except ProjectBatchLimitExceeded as exc:
        import json

        error_detail = json.dumps(
            {
                "code": "too_many_items",
                "message": f"一次最多僅能處理 {exc.max_allowed} 筆資料",
                "requested_count": exc.requested_count,
                "max_batch_size": exc.max_allowed,
            },
            ensure_ascii=False,
        )
        raise HttpError(400, error_detail) from exc

    return {
        **result,
        "project_id": str(project.id),
        "project_name": project.name,
        "current_study_count": project.study_count,
    }


@router.delete("/{project_id}/studies", response={200: dict[str, Any]})
@require_manage_studies
def remove_studies(request, project_id: str, payload: RemoveStudiesRequest, project=None):
    if project is None:
        raise Http404("專案不存在")
    result = ProjectService.remove_studies_from_project(
        project=project,
        exam_ids=payload.exam_ids,
    )

    return {
        **result,
        "current_study_count": project.study_count,
    }


@router.get("/{project_id}/studies", response=list[ProjectStudyItem])
@paginate(ProjectPagination)
@require_view
def list_project_studies(
    request, project_id: str, q: str = "", sort: str = "-assigned_at", project=None
):
    if project is None:
        raise Http404("專案不存在")
    sort_field = ASSIGNMENT_SORT_MAP.get(sort, "-assigned_at")
    assignments = StudyProjectAssignment.objects.filter(project=project).select_related(
        "study", "assigned_by"
    )

    # Apply search filter if provided
    if q:
        assignments = assignments.filter(
            Q(study__patient_name__icontains=q)
            | Q(study__exam_description__icontains=q)
            | Q(study__exam_id__icontains=q)
            | Q(study__medical_record_no__icontains=q)
            | Q(study__exam_item__icontains=q)
        )

    assignments = assignments.order_by(sort_field)

    # Return QuerySet directly to allow Pydantic validation/serialization from ORM objects
    # ProjectStudyItem includes a root_validator to flatten the structure
    return assignments


@router.get("/{project_id}/reports", response=list[ReportDetailResponse])
@paginate(ReportPagination)
@require_view
def list_project_reports(
    request,
    project_id: str,
    q: str = "",
    report_type: str | None = None,
    sort: str = "-verified_at",
    project=None,
):
    if project is None:
        raise Http404("專案不存在")
    return ProjectService.get_project_reports_queryset(
        project=project, q=q or None, report_type=report_type, sort=sort
    )


@router.post("/{project_id}/members", response=MemberInfo)
@require_manage_members
def add_member(request, project_id: str, payload: AddMemberRequest, project=None):
    if project is None:
        raise Http404("專案不存在")
    if payload.role not in VALID_MEMBER_ROLES:
        raise HttpError(400, "無效的角色設定")

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
    member_data["permissions"] = permissions

    return MemberInfo(**member_data)


@router.delete("/{project_id}/members/{user_id}", response={204: None})
@require_manage_members
def remove_member(request, project_id: str, user_id: str, project=None):
    if project is None:
        raise Http404("專案不存在")
    if str(request.user.id) == user_id:
        member = get_object_or_404(ProjectMember, project=project, user_id=user_id)
        if member.role == ProjectMember.ROLE_OWNER:
            raise HttpError(400, "Owner 無法自行移除")
        member.delete()
        return 204, None

    try:
        ProjectService.remove_member(project, user_id)
    except ValueError as exc:
        raise HttpError(400, str(exc)) from exc

    return 204, None


@router.put("/{project_id}/members/{user_id}", response=MemberInfo)
def update_member_role(request, project_id: str, user_id: str, payload: UpdateMemberRoleRequest):
    project = get_object_or_404(Project, id=project_id)

    if ProjectPermissions.get_user_role(project, request.user) != ProjectMember.ROLE_OWNER:
        raise PermissionDenied("只有 Owner 可變更成員角色")

    if payload.role not in VALID_MEMBER_ROLES:
        raise HttpError(400, "無效的角色設定")

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
    member_data["permissions"] = permissions

    return MemberInfo(**member_data)


@router.get("/{project_id}/members", response=list[MemberInfo])
@require_view
def list_members(request, project_id: str, project=None):
    if project is None:
        raise Http404("專案不存在")
    members = (
        ProjectMember.objects.filter(project=project)
        .select_related("user")
        .order_by("role", "joined_at")
    )

    results = []
    for member in members:
        member_data = member.to_dict()
        member_data["permissions"] = ProjectPermissions.ROLE_PERMISSIONS.get(member.role, [])
        results.append(MemberInfo(**member_data))
    return results


@router.get("/{project_id}/statistics", response=ProjectStatistics)
@require_view
def get_statistics(request, project_id: str, project=None):
    if project is None:
        raise Http404("專案不存在")
    stats = ProjectService.get_project_statistics(project)
    return ProjectStatistics(**stats)


@router.get("/search", response=list[ProjectListItem])
@paginate(ProjectPagination)
def search_projects(
    request,
    q: str = "",
    status: str | None = None,
    tags: str | None = None,
    created_by: str | None = None,
    sort: str = ProjectService.DEFAULT_SORT,
):
    return ProjectService.get_projects_queryset(
        user=request.user,
        q=q or None,
        status=status,
        tags=tags,
        created_by=created_by,
        sort=sort,
    )


@router.post("/search/advanced", response=list[ProjectListItem])
@paginate(ProjectPagination)
def advanced_search_projects(request, payload: ProjectListAdvancedSearchRequest):
    """
    Advanced multi-condition search for projects.
    Supports JSON DSL queries similar to report advanced search.
    """
    if payload.mode == "multi" and not payload.tree:
        raise HttpError(400, "Multi-condition payload is required when using multi mode")

    # Use ProjectService to handle advanced search
    queryset = ProjectService.advanced_search_projects(
        user=request.user,
        payload=payload,
    )

    return queryset


@router.get("/studies/{study_id}", response=dict[str, Any])
def get_study_projects(request, study_id: str):
    assignments = (
        StudyProjectAssignment.objects.filter(study_id=study_id)
        .select_related("project")
        .filter(project__project_members__user=request.user)
    )

    projects = []
    for assignment in assignments:
        project = assignment.project
        projects.append(
            {
                "id": str(project.id),
                "name": project.name,
                "status": project.status,
                "user_role": ProjectPermissions.get_user_role(project, request.user),
                "assigned_at": assignment.assigned_at.isoformat()
                if assignment.assigned_at
                else None,
            }
        )

    return {
        "exam_id": study_id,
        "projects": projects,
        "total_projects": len(projects),
    }


@router.get("/{project_id}/resources", response=dict[str, Any])
@require_view
def list_project_resources(
    request,
    project_id: str,
    resource_types: list[str] = Query(default=["study", "report"]),
    page: int = 1,
    page_size: int = 20,
    q: str = None,
    project=None,
):
    """
    Unified project resources list (Studies + Reports).
    Aggregates resources based on StudyProjectAssignment (Accession Number).
    """
    if project is None:
        raise Http404("專案不存在")

    try:
        return ResourceAggregator.get_project_resources(
            project_id=project_id,
            resource_types=resource_types,
            page=page,
            page_size=page_size,
            q=q,
        )
    except ValueError as exc:
        raise HttpError(400, str(exc)) from exc
    # return {'response': '200'}


@router.get("/{project_id}/search", response=ProjectSearchResponse)
@require_view
def search_project_resources(
    request,
    project_id: str,
    q: str = Query(..., min_length=1),
    resource_types: list[str] = Query(default=["study", "report"]),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    project=None,
):
    """
    Full-text search across all project resources.
    """
    if project is None:
        raise Http404("專案不存在")

    trimmed = q.strip()
    if not trimmed:
        return {
            "items": [],
            "total": 0,
            "page": page,
            "page_size": page_size,
        }

    provider_limit = min(max(page_size * SEARCH_RESULT_MULTIPLIER, 50), MAX_PROVIDER_RESULTS)
    results = ProjectSearchRegistry.search(
        project_id=project_id,
        query=trimmed,
        resource_types=resource_types,
        per_provider_limit=provider_limit,
    )

    total = len(results)
    start = (page - 1) * page_size
    page_results = results[start : start + page_size]

    return {
        "items": [asdict(item) for item in page_results],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.post("/{project_id}/search/advanced", response=ProjectSearchResponse)
@require_view
def advanced_search_project_resources(
    request,
    project_id: str,
    payload: ProjectAdvancedSearchRequest,
    project=None,
):
    """
    Advanced multi-condition search for project resources.
    Supports JSON DSL queries identical to /reports/search/advanced endpoint.

    Uses AdvancedQueryBuilder to properly process structured queries including:
    - Gender filters (patient_gender in ['M', 'F'])
    - Age range filters (patient_age <= 18, patient_age >= 0)
    - Text search operators (contains, starts_with, etc.)
    - Full-text search on report content
    """
    if project is None:
        raise Http404("專案不存在")

    if payload.mode == "multi" and not payload.tree:
        raise HttpError(400, "Multi-condition payload is required when using multi mode")

    from django.contrib.postgres.search import SearchQuery

    from report.models import Report
    from report.service import ReportService
    from report.services import AdvancedQueryBuilder, AdvancedQueryValidationError

    # Get project's exam IDs to scope the search
    project_exam_ids = StudyProjectAssignment.objects.filter(project_id=project_id).values_list(
        "study_id", flat=True
    )

    # Start with Reports scoped to this project
    queryset = Report.objects.filter(report_id__in=project_exam_ids, is_latest=True)

    extra_search_query = None

    if payload.mode == "multi" and payload.tree:
        try:
            builder_payload = payload.tree.dict(exclude_none=True)
            builder = AdvancedQueryBuilder(builder_payload)
            result = builder.build()

            # Apply structured DSL filters (gender, age, date ranges, etc.)
            if result.filters:
                queryset = queryset.filter(result.filters)

            # Apply full-text search if present
            extra_search_query = result.search_query
        except AdvancedQueryValidationError as exc:
            raise HttpError(400, str(exc)) from exc
    else:
        # Basic text search mode
        text = ""
        if payload.tree:
            # Extract text from tree for basic search fallback
            def extract_text_from_tree(node: dict) -> str:
                if node.get("field") and node.get("value"):
                    value = node.get("value")
                    if isinstance(value, str):
                        return value
                if node.get("conditions"):
                    texts = [extract_text_from_tree(c) for c in node.get("conditions", [])]
                    return " ".join([t for t in texts if t])
                return ""

            text = extract_text_from_tree(payload.tree.dict(exclude_none=True)).strip()

        if text:
            queryset = queryset.filter(
                Q(report_id__icontains=text)
                | Q(uid__icontains=text)
                | Q(title__icontains=text)
                | Q(content_processed__icontains=text)
            )
            extra_search_query = SearchQuery(text, config=AdvancedQueryBuilder.SEARCH_CONFIG)

    # Apply full-text search filter
    if extra_search_query is not None:
        queryset = queryset.filter(search_vector=extra_search_query)

    # Order by verification date (most recent first)
    queryset = queryset.order_by("-verified_at")

    # Get total count before pagination
    total = queryset.count()

    # Apply pagination
    start = (payload.page - 1) * payload.page_size
    paginated_reports = list(queryset[start : start + payload.page_size])

    # Batch load Study info to avoid N+1 queries
    report_ids = [report.report_id for report in paginated_reports if report.report_id]
    study_map = ReportService._batch_load_studies(report_ids) if report_ids else {}

    # Convert to SearchResult format for consistent response
    items = []
    for report in paginated_reports:
        report_data = ReportService._serialize_report(report, study_map=study_map)
        items.append(
            {
                "resource_type": "report",
                "accession_number": report.report_id or "",
                "score": 1.0,
                "snippet": report.title or "",
                "resource_payload": report_data,
                "resource_timestamp": report.verified_at.isoformat() if report.verified_at else "",
            }
        )

    return {
        "items": items,
        "total": total,
        "page": payload.page,
        "page_size": payload.page_size,
    }
