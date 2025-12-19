from datetime import datetime
from typing import Any, cast

from ninja import Schema
from pydantic import root_validator
from pydantic.fields import FieldInfo

from project.models import Project, ProjectMember
from study.schemas import StudyListItem as BaseStudyListItem
from report.schemas import ReportResponse, AdvancedSearchNode


class CreateProjectRequest(Schema):
    name: str
    description: str | None = ''
    tags: list[str] = []
    status: str | None = Project.STATUS_ACTIVE
    settings: dict[str, Any] | None = {}


class UpdateProjectRequest(Schema):
    name: str | None = None
    description: str | None = None
    tags: list[str] | None = None
    status: str | None = None
    settings: dict[str, Any] | None = None
    metadata: dict[str, Any] | None = None


class UserInfo(Schema):
    id: str
    name: str
    email: str | None = None


class PermissionFlags(Schema):
    can_manage_members: bool = False
    can_assign_studies: bool = False
    can_archive: bool = False


class ProjectListItem(Schema):
    id: str
    name: str
    description: str
    status: str
    tags: list[str]
    study_count: int
    member_count: int
    created_at: datetime
    updated_at: datetime
    created_by: UserInfo
    user_role: str | None = None
    user_permissions: list[str] = []
    can_manage_members: bool = False
    can_assign_studies: bool = False
    can_archive: bool = False


class ProjectDetailResponse(Schema):
    id: str
    name: str
    description: str
    status: str
    tags: list[str]
    study_count: int
    member_count: int
    created_at: datetime
    updated_at: datetime
    created_by: UserInfo
    user_role: str | None
    user_permissions: list[str]
    settings: dict[str, Any]
    metadata: dict[str, Any]
    can_manage_members: bool = False
    can_assign_studies: bool = False
    can_archive: bool = False


class AddStudiesRequest(Schema):
    exam_ids: list[str]


class RemoveStudiesRequest(Schema):
    exam_ids: list[str]


class BatchAssignRequest(Schema):
    exam_ids: list[str]
    project_ids: list[str]


class BatchAssignQueryFilters(Schema):
    q: str | None = None
    exam_status: str | list[str] | None = None
    exam_source: str | list[str] | None = None
    exam_item: str | None = None
    exam_equipment: list[str] | None = None
    application_order_no: str | None = None
    patient_gender: str | list[str] | None = None
    exam_description: list[str] | None = None
    exam_room: list[str] | None = None
    patient_age_min: int | None = None
    patient_age_max: int | None = None
    start_date: str | None = None
    end_date: str | None = None


class BatchAssignByQueryRequest(Schema):
    project_ids: list[str]
    filters: BatchAssignQueryFilters
    max_batch_size: int | None = None


class FailedAssignmentItem(Schema):
    exam_id: str
    reason: str


class BatchAssignByQueryDetail(Schema):
    project_id: str
    project_name: str | None = None
    added_count: int
    skipped_count: int
    failed_items_sample: list[FailedAssignmentItem] = []
    failed_items_truncated: bool = False
    failed_items_sample_limit: int = 20
    failed_reason: str | None = None


class BatchAssignByQueryResponse(Schema):
    success: bool
    matched_count: int
    max_batch_size: int
    projects_updated: int
    details: list[BatchAssignByQueryDetail]


class AddMemberRequest(Schema):
    user_id: str
    role: str = ProjectMember.ROLE_VIEWER


class UpdateMemberRoleRequest(Schema):
    role: str


class MemberInfo(Schema):
    user_id: str
    name: str
    email: str | None
    role: str
    joined_at: datetime
    permissions: list[str]


class ProjectStudyItem(BaseStudyListItem):
    assigned_at: datetime
    assigned_by: UserInfo

    class Config:
        orm_mode = True

    @root_validator(pre=True)
    def flatten_assignment(cls, values):
        # Handle StudyProjectAssignment object
        if hasattr(values, 'study') and hasattr(values, 'assigned_at'):
            study = values.study
            # Extract base fields from study
            data = {}
            # Get field names from BaseStudyListItem - Pydantic v1 __fields__ is a dict
            base_fields = cast(dict[str, FieldInfo], BaseStudyListItem.__fields__)
            for field_name in base_fields:
                 if hasattr(study, field_name):
                     data[field_name] = getattr(study, field_name)

            # Extract assignment fields
            data['assigned_at'] = values.assigned_at

            # Handle UserInfo for assigned_by
            user = values.assigned_by
            data['assigned_by'] = {
                'id': str(user.id),
                'name': user.get_full_name() or user.username,
                'email': user.email
            }
            return data
        return values


class ProjectStatistics(Schema):
    project_id: str
    project_name: str
    study_count: int
    member_count: int
    created_at: datetime
    updated_at: datetime
    last_activity_at: datetime | None = None
    modality_distribution: dict[str, int]


class ProjectResourceAssignment(Schema):
    assigned_at: datetime
    assigned_by: UserInfo


class ProjectResourceItem(Schema):
    """
    Unified resource item (Study or Report) keyed by Accession Number.
    """
    resource_type: str  # 'study', 'report'
    accession_number: str
    resource_timestamp: datetime

    study: BaseStudyListItem | None = None
    report: ReportResponse | None = None

    assignment: ProjectResourceAssignment | None = None

class SearchResultItem(Schema):
    resource_type: str
    accession_number: str
    score: float
    snippet: str
    resource_payload: dict[str, Any]
    resource_timestamp: str


class ProjectSearchResponse(Schema):
    items: list[SearchResultItem]
    total: int
    page: int
    page_size: int


class ProjectAdvancedSearchRequest(Schema):
    """
    Project Resource Advanced Search Request Schema.
    Supports multi-condition queries using JSON DSL.
    """
    mode: str = 'multi'  # 'basic' or 'multi'
    tree: AdvancedSearchNode | None = None
    resource_types: list[str] = ['study', 'report']
    page: int = 1
    page_size: int = 20


class ProjectListAdvancedSearchRequest(Schema):
    """
    Project List Advanced Search Request Schema.
    Supports multi-condition queries using JSON DSL for project listing.
    """
    mode: str = 'multi'  # 'basic' or 'multi'
    tree: AdvancedSearchNode | None = None
    page: int = 1
    page_size: int = 20
    sort: str | None = None
