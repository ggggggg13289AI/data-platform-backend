# Projects Route 實作指南

**文件版本**：1.0  
**建立日期**：2025-11-12  
**文件狀態**：✅ 規劃完成  
**作者**：Claude Code  
**專案**：醫學影像資料管理平台

---

## 📋 文件目的

本文件提供 Projects 功能的完整實作指南，包含：

1. API 端點詳細規格
2. 權限系統設計與實作
3. 分階段實作計畫
4. 程式碼範例與最佳實踐

---

## 🚀 實作總覽

### 技術棧

| 層級 | 技術 | 用途 |
|------|------|------|
| **API 框架** | Django Ninja | RESTful API 端點 |
| **ORM** | Django ORM | 資料庫操作 |
| **驗證** | Pydantic | 請求/回應驗證 |
| **資料庫** | PostgreSQL | 資料儲存 |
| **認證** | JWT/Bearer Token | 使用者認證 |

### 程式碼結構

```
studies/
├── models.py                    # 新增 3 個模型
├── project_api.py              # 新建：22 個 API 端點
├── project_service.py          # 新建：業務邏輯層
├── permissions.py              # 新建：權限系統
├── migrations/
│   └── 000X_add_project_models.py  # 新建：資料庫遷移
└── tests/
    ├── test_project_models.py      # 新建：模型測試
    ├── test_project_service.py     # 新建：服務測試
    ├── test_project_api.py         # 新建：API 測試
    └── test_permissions.py         # 新建：權限測試
```

---

## 🔐 權限系統設計

### 角色定義

#### Owner（擁有者）
- **數量限制**：每個專案 1 人
- **獲得方式**：建立專案時自動成為 Owner
- **特殊權限**：
  - 刪除專案
  - 變更成員角色
  - 轉讓 Owner 權限（未來功能）
- **限制**：
  - 不可被移除
  - 不可自行降級

#### Admin（管理員）
- **數量限制**：無限制
- **主要職責**：協助管理專案與成員
- **權限範圍**：
  - 所有 Editor 權限
  - 新增/移除成員
  - 變更成員為 Viewer/Editor
- **限制**：
  - 不可變更 Owner 角色
  - 不可刪除專案

#### Editor（編輯者）
- **數量限制**：無限制
- **主要職責**：編輯專案內容與研究
- **權限範圍**：
  - 所有 Viewer 權限
  - 編輯專案資訊
  - 新增/移除研究
  - 封存/恢復專案
- **限制**：
  - 不可管理成員

#### Viewer（檢視者）
- **數量限制**：無限制
- **主要職責**：查看專案資訊
- **權限範圍**：
  - 查看專案詳情
  - 查看研究列表
  - 查看成員列表
  - 查看統計資訊
- **限制**：
  - 不可進行任何修改

### 權限實作

#### permissions.py

```python
from django.core.exceptions import PermissionDenied
from functools import wraps
from .models import Project, ProjectMember

class ProjectPermissions:
    """專案權限檢查類別"""
    
    # 權限定義
    PERMISSION_VIEW = 'view'
    PERMISSION_EDIT = 'edit'
    PERMISSION_DELETE = 'delete'
    PERMISSION_MANAGE_MEMBERS = 'manage_members'
    PERMISSION_MANAGE_STUDIES = 'manage_studies'
    
    # 角色權限映射
    ROLE_PERMISSIONS = {
        'owner': [
            PERMISSION_VIEW,
            PERMISSION_EDIT,
            PERMISSION_DELETE,
            PERMISSION_MANAGE_MEMBERS,
            PERMISSION_MANAGE_STUDIES,
        ],
        'admin': [
            PERMISSION_VIEW,
            PERMISSION_EDIT,
            PERMISSION_MANAGE_MEMBERS,
            PERMISSION_MANAGE_STUDIES,
        ],
        'editor': [
            PERMISSION_VIEW,
            PERMISSION_EDIT,
            PERMISSION_MANAGE_STUDIES,
        ],
        'viewer': [
            PERMISSION_VIEW,
        ],
    }
    
    @classmethod
    def get_user_role(cls, project, user):
        """取得使用者在專案中的角色"""
        try:
            member = ProjectMember.objects.get(project=project, user=user)
            return member.role
        except ProjectMember.DoesNotExist:
            return None
    
    @classmethod
    def get_user_permissions(cls, project, user):
        """取得使用者的權限列表"""
        role = cls.get_user_role(project, user)
        if not role:
            return []
        return cls.ROLE_PERMISSIONS.get(role, [])
    
    @classmethod
    def check_permission(cls, project, user, permission):
        """檢查使用者是否有特定權限"""
        permissions = cls.get_user_permissions(project, user)
        return permission in permissions
    
    @classmethod
    def require_permission(cls, permission):
        """權限檢查裝飾器"""
        def decorator(func):
            @wraps(func)
            def wrapper(request, project_id, *args, **kwargs):
                try:
                    project = Project.objects.get(id=project_id)
                except Project.DoesNotExist:
                    raise Http404("專案不存在")
                
                if not cls.check_permission(project, request.user, permission):
                    raise PermissionDenied(
                        f"您沒有 '{permission}' 權限"
                    )
                
                # 將 project 傳入函數
                return func(request, project, *args, **kwargs)
            return wrapper
        return decorator
    
    @classmethod
    def can_manage_member(cls, project, operator, target_user):
        """檢查是否可管理特定成員"""
        operator_role = cls.get_user_role(project, operator)
        target_role = cls.get_user_role(project, target_user)
        
        # Owner 不可被管理
        if target_role == 'owner':
            return False
        
        # 只有 Owner 和 Admin 可管理成員
        if operator_role not in ['owner', 'admin']:
            return False
        
        # Admin 不可變更其他 Admin 的角色
        if operator_role == 'admin' and target_role == 'admin':
            return False
        
        return True

# 便捷裝飾器
require_view = ProjectPermissions.require_permission(ProjectPermissions.PERMISSION_VIEW)
require_edit = ProjectPermissions.require_permission(ProjectPermissions.PERMISSION_EDIT)
require_delete = ProjectPermissions.require_permission(ProjectPermissions.PERMISSION_DELETE)
require_manage_members = ProjectPermissions.require_permission(ProjectPermissions.PERMISSION_MANAGE_MEMBERS)
require_manage_studies = ProjectPermissions.require_permission(ProjectPermissions.PERMISSION_MANAGE_STUDIES)
```

---

## 📡 API 端點實作

### project_service.py（業務邏輯層）

```python
from django.db import transaction, models
from django.db.models import Q, Count, Prefetch
from django.contrib.auth.models import User
from .models import Project, ProjectMember, StudyProjectAssignment, Study

class ProjectService:
    """專案服務類別"""
    
    @staticmethod
    def create_project(name, user, description='', tags=None, status='active', settings=None):
        """建立專案"""
        with transaction.atomic():
            project = Project.objects.create(
                name=name,
                description=description,
                status=status,
                tags=tags or [],
                settings=settings or {},
                created_by=user
            )
            
            # 建立者自動成為 Owner
            ProjectMember.objects.create(
                project=project,
                user=user,
                role='owner'
            )
            
            return project
    
    @staticmethod
    def get_projects_queryset(
        user,
        q=None,
        status=None,
        tags=None,
        created_by=None,
        sort='-updated_at'
    ):
        """建立專案查詢集"""
        
        # 基礎查詢：只查詢使用者有權限的專案
        queryset = Project.objects.filter(
            project_members__user=user
        ).select_related('created_by').distinct()
        
        # 關鍵字搜尋
        if q:
            queryset = queryset.filter(
                Q(name__icontains=q) | Q(description__icontains=q)
            )
        
        # 狀態篩選
        if status:
            queryset = queryset.filter(status=status)
        
        # 標籤篩選
        if tags:
            tag_list = tags.split(',') if isinstance(tags, str) else tags
            for tag in tag_list:
                queryset = queryset.filter(tags__contains=[tag])
        
        # 建立者篩選
        if created_by:
            queryset = queryset.filter(created_by_id=created_by)
        
        # 排序
        queryset = queryset.order_by(sort)
        
        return queryset
    
    @staticmethod
    def add_studies_to_project(project, exam_ids, user):
        """批量新增研究到專案"""
        with transaction.atomic():
            # 驗證研究存在
            studies = Study.objects.filter(exam_id__in=exam_ids)
            if studies.count() != len(exam_ids):
                found_ids = set(studies.values_list('exam_id', flat=True))
                missing_ids = set(exam_ids) - found_ids
                raise ValueError(f"研究不存在: {', '.join(missing_ids)}")
            
            # 過濾已分配的研究
            existing_assignments = StudyProjectAssignment.objects.filter(
                project=project,
                study_id__in=exam_ids
            ).values_list('study_id', flat=True)
            
            new_exam_ids = [eid for eid in exam_ids if eid not in existing_assignments]
            
            # 批量建立分配記錄
            assignments = [
                StudyProjectAssignment(
                    project=project,
                    study_id=exam_id,
                    assigned_by=user
                )
                for exam_id in new_exam_ids
            ]
            
            StudyProjectAssignment.objects.bulk_create(assignments)
            
            # 更新計數
            added_count = len(new_exam_ids)
            project.increment_study_count(added_count)
            
            return {
                'success': True,
                'added_count': added_count,
                'skipped_count': len(existing_assignments),
            }
    
    @staticmethod
    def remove_studies_from_project(project, exam_ids):
        """批量移除研究"""
        with transaction.atomic():
            deleted_count, _ = StudyProjectAssignment.objects.filter(
                project=project,
                study_id__in=exam_ids
            ).delete()
            
            # 更新計數
            if deleted_count > 0:
                project.decrement_study_count(deleted_count)
            
            return {
                'success': True,
                'removed_count': deleted_count,
            }
    
    @staticmethod
    def add_member(project, user_id, role='viewer'):
        """新增成員"""
        user = User.objects.get(id=user_id)
        
        # 檢查是否已是成員
        if ProjectMember.objects.filter(project=project, user=user).exists():
            raise ValueError("使用者已是專案成員")
        
        member = ProjectMember.objects.create(
            project=project,
            user=user,
            role=role
        )
        
        return member
    
    @staticmethod
    def remove_member(project, user_id):
        """移除成員"""
        # 不可移除 Owner
        member = ProjectMember.objects.get(project=project, user_id=user_id)
        if member.role == 'owner':
            raise ValueError("無法移除專案 Owner")
        
        member.delete()
        return {'success': True}
    
    @staticmethod
    def update_member_role(project, user_id, new_role):
        """更新成員角色"""
        member = ProjectMember.objects.get(project=project, user_id=user_id)
        
        # 不可變更 Owner 角色
        if member.role == 'owner' or new_role == 'owner':
            raise ValueError("無法變更 Owner 角色")
        
        member.role = new_role
        member.save()
        
        return member
    
    @staticmethod
    def get_project_statistics(project):
        """取得專案統計資訊"""
        
        # 研究按 Modality 分布
        modality_dist = StudyProjectAssignment.objects.filter(
            project=project
        ).values('study__modality').annotate(
            count=Count('id')
        ).order_by('-count')
        
        modality_distribution = {
            item['study__modality']: item['count'] 
            for item in modality_dist
        }
        
        # 成員數量
        member_count = ProjectMember.objects.filter(project=project).count()
        
        # 最後活動時間
        last_assignment = StudyProjectAssignment.objects.filter(
            project=project
        ).order_by('-assigned_at').first()
        
        last_activity_at = last_assignment.assigned_at if last_assignment else None
        
        return {
            'project_id': str(project.id),
            'project_name': project.name,
            'study_count': project.study_count,
            'member_count': member_count,
            'created_at': project.created_at.isoformat(),
            'updated_at': project.updated_at.isoformat(),
            'last_activity_at': last_activity_at.isoformat() if last_activity_at else None,
            'modality_distribution': modality_distribution,
        }
```

### project_api.py（API 端點）

```python
from ninja import Router, Schema
from ninja.pagination import paginate
from typing import List, Optional
from datetime import datetime
from django.shortcuts import get_object_or_404
from django.http import Http404
from django.core.exceptions import PermissionDenied

from .models import Project, ProjectMember, Study
from .project_service import ProjectService
from .permissions import (
    ProjectPermissions,
    require_view,
    require_edit,
    require_delete,
    require_manage_members,
    require_manage_studies,
)
from .pagination import ProjectPagination

router = Router(tags=['projects'])

# ============ Pydantic Schemas ============

class CreateProjectRequest(Schema):
    name: str
    description: Optional[str] = ''
    tags: List[str] = []
    status: Optional[str] = 'active'
    settings: Optional[dict] = {}

class UpdateProjectRequest(Schema):
    name: Optional[str] = None
    description: Optional[str] = None
    tags: Optional[List[str]] = None
    status: Optional[str] = None
    settings: Optional[dict] = None

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
    user_role: str

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
    user_role: str
    user_permissions: List[str]
    settings: dict
    metadata: dict

class AddStudiesRequest(Schema):
    exam_ids: List[str]
    metadata: Optional[dict] = {}

class RemoveStudiesRequest(Schema):
    exam_ids: List[str]

class BatchAssignRequest(Schema):
    exam_ids: List[str]
    project_ids: List[str]

class AddMemberRequest(Schema):
    user_id: str
    role: str = 'viewer'

class UpdateMemberRoleRequest(Schema):
    role: str

class MemberInfo(Schema):
    user_id: str
    name: str
    email: str
    role: str
    joined_at: datetime
    permissions: List[str]

class StudyListItem(Schema):
    exam_id: str
    patient_name: str
    exam_date: str
    modality: str
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
    modality_distribution: dict

# ============ API Endpoints ============

@router.get('/projects', response=List[ProjectListItem])
@paginate(ProjectPagination)
def list_projects(
    request,
    q: str = '',
    status: Optional[str] = None,
    tags: Optional[str] = None,
    created_by: Optional[str] = None,
    sort: str = '-updated_at',
):
    """列出專案"""
    queryset = ProjectService.get_projects_queryset(
        user=request.user,
        q=q,
        status=status,
        tags=tags,
        created_by=created_by,
        sort=sort
    )
    
    # 添加使用者角色資訊
    projects = []
    for project in queryset:
        role = ProjectPermissions.get_user_role(project, request.user)
        member_count = project.project_members.count()
        
        project_data = {
            **project.to_dict(),
            'user_role': role,
            'member_count': member_count,
        }
        projects.append(ProjectListItem(**project_data))
    
    return projects

@router.post('/projects', response={201: ProjectDetailResponse})
def create_project(request, payload: CreateProjectRequest):
    """建立專案"""
    project = ProjectService.create_project(
        name=payload.name,
        user=request.user,
        description=payload.description,
        tags=payload.tags,
        status=payload.status,
        settings=payload.settings
    )
    
    return 201, ProjectDetailResponse(
        **project.to_dict(),
        user_role='owner',
        user_permissions=ProjectPermissions.ROLE_PERMISSIONS['owner'],
        member_count=1
    )

@router.get('/projects/{project_id}', response=ProjectDetailResponse)
@require_view
def get_project(request, project: Project):
    """取得專案詳情"""
    role = ProjectPermissions.get_user_role(project, request.user)
    permissions = ProjectPermissions.get_user_permissions(project, request.user)
    member_count = project.project_members.count()
    
    return ProjectDetailResponse(
        **project.to_dict(),
        user_role=role,
        user_permissions=permissions,
        member_count=member_count
    )

@router.put('/projects/{project_id}', response=ProjectDetailResponse)
@require_edit
def update_project(request, project: Project, payload: UpdateProjectRequest):
    """更新專案"""
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
    
    if update_fields:
        project.save(update_fields=update_fields)
    
    role = ProjectPermissions.get_user_role(project, request.user)
    permissions = ProjectPermissions.get_user_permissions(project, request.user)
    
    return ProjectDetailResponse(
        **project.to_dict(),
        user_role=role,
        user_permissions=permissions,
        member_count=project.project_members.count()
    )

@router.delete('/projects/{project_id}', response={204: None})
@require_delete
def delete_project(request, project: Project):
    """刪除專案"""
    project.delete()
    return 204, None

@router.post('/projects/{project_id}/archive', response={200: dict})
@require_edit
def archive_project(request, project: Project):
    """封存專案"""
    project.status = 'archived'
    project.save(update_fields=['status'])
    return {'success': True, 'status': 'archived'}

@router.post('/projects/{project_id}/restore', response={200: dict})
@require_edit
def restore_project(request, project: Project):
    """恢復專案"""
    project.status = 'active'
    project.save(update_fields=['status'])
    return {'success': True, 'status': 'active'}

@router.post('/projects/{project_id}/duplicate', response={201: ProjectDetailResponse})
@require_view
def duplicate_project(request, project: Project):
    """複製專案"""
    new_project = ProjectService.create_project(
        name=f"{project.name} (副本)",
        user=request.user,
        description=project.description,
        tags=project.tags.copy(),
        status='draft',
        settings=project.settings.copy()
    )
    
    return 201, ProjectDetailResponse(
        **new_project.to_dict(),
        user_role='owner',
        user_permissions=ProjectPermissions.ROLE_PERMISSIONS['owner'],
        member_count=1
    )

@router.post('/projects/{project_id}/studies', response={200: dict})
@require_manage_studies
def add_studies(request, project: Project, payload: AddStudiesRequest):
    """新增研究到專案"""
    result = ProjectService.add_studies_to_project(
        project=project,
        exam_ids=payload.exam_ids,
        user=request.user
    )
    
    return {
        **result,
        'project_name': project.name,
        'current_study_count': project.study_count
    }

@router.delete('/projects/{project_id}/studies', response={200: dict})
@require_manage_studies
def remove_studies(request, project: Project, payload: RemoveStudiesRequest):
    """移除研究"""
    result = ProjectService.remove_studies_from_project(
        project=project,
        exam_ids=payload.exam_ids
    )
    
    return {
        **result,
        'current_study_count': project.study_count
    }

@router.get('/projects/{project_id}/studies', response=List[StudyListItem])
@paginate(ProjectPagination)
@require_view
def list_project_studies(request, project: Project, sort: str = '-assigned_at'):
    """列出專案的研究"""
    assignments = StudyProjectAssignment.objects.filter(
        project=project
    ).select_related('study', 'assigned_by').order_by(sort)
    
    return [
        StudyListItem(
            exam_id=a.study.exam_id,
            patient_name=a.study.patient_name,
            exam_date=a.study.exam_date,
            modality=a.study.modality,
            assigned_at=a.assigned_at,
            assigned_by=UserInfo(
                id=str(a.assigned_by.id),
                name=a.assigned_by.get_full_name() or a.assigned_by.username
            )
        )
        for a in assignments
    ]

@router.post('/projects/{project_id}/members', response={200: MemberInfo})
@require_manage_members
def add_member(request, project: Project, payload: AddMemberRequest):
    """新增成員"""
    member = ProjectService.add_member(
        project=project,
        user_id=payload.user_id,
        role=payload.role
    )
    
    permissions = ProjectPermissions.ROLE_PERMISSIONS.get(member.role, [])
    
    return MemberInfo(
        **member.to_dict(),
        permissions=permissions
    )

@router.delete('/projects/{project_id}/members/{user_id}', response={204: None})
@require_manage_members
def remove_member(request, project: Project, user_id: str):
    """移除成員"""
    # 允許成員自行退出
    if str(request.user.id) == user_id:
        member = ProjectMember.objects.get(project=project, user_id=user_id)
        if member.role != 'owner':
            member.delete()
            return 204, None
    
    ProjectService.remove_member(project, user_id)
    return 204, None

@router.put('/projects/{project_id}/members/{user_id}', response=MemberInfo)
def update_member_role(request, project_id: str, user_id: str, payload: UpdateMemberRoleRequest):
    """更新成員角色（僅 Owner 可操作）"""
    project = get_object_or_404(Project, id=project_id)
    
    # 檢查是否為 Owner
    if ProjectPermissions.get_user_role(project, request.user) != 'owner':
        raise PermissionDenied("只有 Owner 可變更成員角色")
    
    member = ProjectService.update_member_role(
        project=project,
        user_id=user_id,
        new_role=payload.role
    )
    
    permissions = ProjectPermissions.ROLE_PERMISSIONS.get(member.role, [])
    
    return MemberInfo(
        **member.to_dict(),
        permissions=permissions
    )

@router.get('/projects/{project_id}/members', response=List[MemberInfo])
@require_view
def list_members(request, project: Project):
    """列出專案成員"""
    members = ProjectMember.objects.filter(
        project=project
    ).select_related('user').order_by('role', 'joined_at')
    
    return [
        MemberInfo(
            **m.to_dict(),
            permissions=ProjectPermissions.ROLE_PERMISSIONS.get(m.role, [])
        )
        for m in members
    ]

@router.get('/projects/{project_id}/statistics', response=ProjectStatistics)
@require_view
def get_statistics(request, project: Project):
    """取得專案統計資訊"""
    stats = ProjectService.get_project_statistics(project)
    return ProjectStatistics(**stats)

@router.get('/projects/search', response=List[ProjectListItem])
@paginate(ProjectPagination)
def search_projects(request, q: str = '', **filters):
    """搜尋專案（與 list_projects 相同，為前端相容性保留）"""
    return list_projects(request, q=q, **filters)

@router.get('/studies/{study_id}/projects', response={200: dict})
def get_study_projects(request, study_id: str):
    """取得研究所屬的專案"""
    # 只返回使用者有權限的專案
    assignments = StudyProjectAssignment.objects.filter(
        study_id=study_id
    ).select_related('project').filter(
        project__project_members__user=request.user
    )
    
    projects = []
    for a in assignments:
        role = ProjectPermissions.get_user_role(a.project, request.user)
        projects.append({
            'id': str(a.project.id),
            'name': a.project.name,
            'status': a.project.status,
            'user_role': role,
            'assigned_at': a.assigned_at.isoformat(),
        })
    
    return {
        'exam_id': study_id,
        'projects': projects,
        'total_projects': len(projects)
    }

@router.post('/projects/batch-assign', response={200: dict})
def batch_assign_studies(request, payload: BatchAssignRequest):
    """批量分配研究到多個專案"""
    results = []
    total_assignments = 0
    
    for project_id in payload.project_ids:
        project = get_object_or_404(Project, id=project_id)
        
        # 檢查權限
        if not ProjectPermissions.check_permission(
            project, request.user, ProjectPermissions.PERMISSION_MANAGE_STUDIES
        ):
            continue
        
        result = ProjectService.add_studies_to_project(
            project=project,
            exam_ids=payload.exam_ids,
            user=request.user
        )
        
        total_assignments += result['added_count']
        results.append({
            'project_id': str(project.id),
            'project_name': project.name,
            'added_count': result['added_count'],
        })
    
    return {
        'success': True,
        'total_assignments': total_assignments,
        'projects_updated': len(results),
        'details': results
    }
```

---

## 📅 分階段實作計畫

### Phase 1：資料模型與基礎架構（2-3 天）

#### Day 1：模型定義與遷移

**任務清單**：
- [ ] 在 `models.py` 中定義 3 個模型
- [ ] 建立遷移檔案
- [ ] 執行遷移並驗證
- [ ] 建立基本單元測試

**檢查點**：
```bash
# 建立遷移
python manage.py makemigrations

# 檢查遷移 SQL
python manage.py sqlmigrate studies 000X

# 執行遷移
python manage.py migrate

# 驗證表格建立
python manage.py dbshell
\dt projects*
```

#### Day 2：服務層與權限系統

**任務清單**：
- [ ] 實作 `ProjectService` 類別
- [ ] 實作 `ProjectPermissions` 類別
- [ ] 撰寫服務層單元測試
- [ ] 撰寫權限系統單元測試

**測試覆蓋率目標**：≥ 80%

---

### Phase 2：API 端點實作（3-4 天）

#### Day 3：核心 CRUD（5 個端點）

**實作端點**：
1. GET /projects（列表）
2. POST /projects（建立）
3. GET /projects/:id（詳情）
4. PUT /projects/:id（更新）
5. DELETE /projects/:id（刪除）

**測試策略**：
- 正常流程測試
- 權限測試
- 驗證測試
- 錯誤處理測試

#### Day 4：生命週期與研究管理（8 個端點）

**實作端點**：
6. POST /projects/:id/archive
7. POST /projects/:id/restore
8. POST /projects/:id/duplicate
9. POST /projects/:id/studies
10. DELETE /projects/:id/studies
11. GET /projects/:id/studies
12. POST /projects/batch-assign
13. GET /studies/:studyId/projects

#### Day 5：成員管理與搜尋（6 個端點）

**實作端點**：
14. POST /projects/:id/members
15. DELETE /projects/:id/members/:userId
16. PUT /projects/:id/members/:userId
17. GET /projects/:id/members
18. GET /projects/:id/statistics
19. GET /projects/search

---

### Phase 3：整合測試與部署（2 天）

#### Day 6：整合測試

**測試項目**：
- [ ] 前後端整合測試
- [ ] 併發操作測試
- [ ] 效能測試（p95 < 500ms）
- [ ] 資料一致性測試

#### Day 7：部署準備

**任務清單**：
- [ ] 程式碼 review
- [ ] 安全性審查
- [ ] 文件撰寫
- [ ] 部署檢查清單

---

## ✅ 驗收標準

### 功能驗收

```markdown
## Phase 1 驗收清單
- [ ] 3 個模型定義完成且通過 review
- [ ] 遷移檔案可正常執行與回滾
- [ ] 服務層單元測試覆蓋率 ≥ 80%
- [ ] 權限系統測試覆蓋率 ≥ 90%

## Phase 2 驗收清單
- [ ] 22 個 API 端點全部實作完成
- [ ] 每個端點有完整的 Pydantic schema
- [ ] API 測試覆蓋率 100%
- [ ] OpenAPI 文件自動生成

## Phase 3 驗收清單
- [ ] 前後端整合測試通過
- [ ] 效能指標達標（p95 < 500ms）
- [ ] 安全性審查無重大漏洞
- [ ] 完整繁體中文文件
```

---

## 📝 總結

### 實作要點

1. **遵循現有模式**：參考 Studies API 和 Reports API 的實作模式
2. **完整權限檢查**：每個端點都需進行權限驗證
3. **事務完整性**：批量操作使用 `@transaction.atomic`
4. **效能優化**：適當使用 `select_related` 和 `prefetch_related`
5. **錯誤處理**：提供清晰的錯誤訊息

### 預期產出

完成後將交付：
- ✅ 3 個 Django 模型
- ✅ 1 個服務層類別（~400 行）
- ✅ 1 個權限系統類別（~150 行）
- ✅ 22 個 API 端點（~800 行）
- ✅ 完整測試套件（~500 行）
- ✅ 繁體中文文件

**總程式碼量**：~2,400 行  
**預計工時**：7-8 個工作天

---

**文件狀態**：✅ 實作指南完成  
**下一步**：等待 pagination 分支合併後開始實作