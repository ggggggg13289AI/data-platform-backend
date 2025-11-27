# 後端需求分析 - Projects Feature
## Backend Requirements Analysis - Projects Feature

**文件版本**: v1.0
**建立日期**: 2025-11-12
**專案**: Medical Imaging Data Platform
**技術棧**: Django 5.1 + Django Ninja + PostgreSQL
**功能模組**: Projects Management API

---

## 一、Executive Summary (執行摘要)

### 1.1 Current Status (當前狀態)

**Backend Implementation**: ❌ 0% Complete (需從零開始建置)
**Frontend Contract**: ✅ 100% Defined (22個API端點已定義完整)

### 1.2 Implementation Scope (實作範圍)

**必須實作的元件**:

| Component | Description | Priority | Complexity |
|-----------|-------------|----------|------------|
| Django Models | 4個資料模型 | 🔴 Critical | Medium |
| Django Ninja API | 22個API端點 | 🔴 Critical | High |
| Service Layer | 業務邏輯層 | 🟡 Important | Medium |
| Permissions | 權限控制系統 | 🟡 Important | High |
| Migrations | 資料庫遷移 | 🔴 Critical | Low |
| Unit Tests | 單元測試 | 🟢 Recommended | Medium |

---

## 二、Technical Architecture (技術架構)

### 2.1 Architecture Pattern (架構模式)

**採用三層架構** (Three-Layer Architecture):

```
┌─────────────────────────────────────┐
│   API Layer (Django Ninja)          │  ← REST API 端點
│   - project_api.py                  │
│   - Pydantic Schemas                │
│   - Request/Response Handling       │
└─────────────────────────────────────┘
              ↓
┌─────────────────────────────────────┐
│   Service Layer                      │  ← 業務邏輯
│   - project_service.py               │
│   - Business Rules                   │
│   - Query Optimization               │
└─────────────────────────────────────┘
              ↓
┌─────────────────────────────────────┐
│   Data Layer (Django ORM)            │  ← 資料存取
│   - models.py                        │
│   - Database Queries                 │
│   - Transactions                     │
└─────────────────────────────────────┘
```

### 2.2 File Structure (檔案結構)

```
backend_django/
├── studies/                          # 現有 app
│   ├── models.py                     # + Project models
│   ├── project_api.py               # NEW: API router
│   ├── project_service.py           # NEW: Business logic
│   ├── permissions.py                # NEW: Permission checks
│   └── migrations/
│       └── 000X_add_project_models.py  # NEW: Migration
├── config/
│   └── api.py                        # + Register project_router
└── tests/
    └── test_project_api.py           # NEW: API tests
```

###

 2.3 Design Principles (設計原則)

遵循現有程式碼風格（參考 `report_api.py`）:

1. **PRAGMATIC DESIGN** (實用設計)
   - Flat structure where possible
   - No premature abstraction
   - Explicit is better than implicit

2. **Django Best Practices** (Django 最佳實踐)
   - Use Django ORM efficiently
   - Proper indexing on foreign keys
   - Transaction management for data integrity

3. **API Design Standards** (API 設計標準)
   - RESTful conventions
   - Consistent error responses
   - Comprehensive logging

---

## 三、Data Models Design (資料模型設計)

### 3.1 Core Project Model (核心專案模型)

```python
# backend_django/studies/models.py

from django.db import models
from django.contrib.auth.models import User
import uuid

class Project(models.Model):
    """
    Medical imaging project for organizing studies.

    Design: Flat structure with flexible metadata storage.
    Follows same pattern as Report model for consistency.
    """

    # Primary Key
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        db_index=True
    )

    # Basic Information
    name = models.CharField(max_length=200, db_index=True)
    description = models.TextField(blank=True, default='')

    # Status Management
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('archived', 'Archived'),
        ('completed', 'Completed'),
        ('draft', 'Draft'),
    ]
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='active',
        db_index=True
    )

    # Categorization
    tags = models.JSONField(default=list, blank=True)  # Array of strings

    # Ownership and Collaboration
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_projects'
    )
    members = models.ManyToManyField(
        User,
        through='ProjectMember',
        related_name='projects'
    )

    # Metrics (denormalized for performance)
    study_count = models.IntegerField(default=0)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Flexible Settings and Metadata
    settings = models.JSONField(default=dict, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = 'projects'
        ordering = ['-updated_at']
        indexes = [
            models.Index(fields=['status', '-updated_at']),
            models.Index(fields=['created_by', '-created_at']),
            models.Index(fields=['-study_count']),
        ]
        verbose_name = 'Project'
        verbose_name_plural = 'Projects'

    def __str__(self):
        return f'{self.name} ({self.status})'

    def to_dict(self):
        """Convert to dictionary for API response."""
        return {
            'id': str(self.id),
            'name': self.name,
            'description': self.description,
            'status': self.status,
            'tags': self.tags,
            'study_count': self.study_count,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'created_by': self.created_by.username if self.created_by else None,
        }
```

### 3.2 Project Member Model (專案成員模型)

```python
class ProjectMember(models.Model):
    """
    Through model for Project-User many-to-many relationship.
    Tracks role and permissions for each member.
    """

    ROLE_CHOICES = [
        ('owner', 'Owner'),
        ('admin', 'Admin'),
        ('editor', 'Editor'),
        ('viewer', 'Viewer'),
    ]

    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='project_members'
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='project_memberships'
    )
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default='viewer'
    )
    joined_at = models.DateTimeField(auto_now_add=True)
    permissions = models.JSONField(default=list, blank=True)  # Flexible permissions

    class Meta:
        db_table = 'project_members'
        unique_together = [['project', 'user']]
        indexes = [
            models.Index(fields=['project', 'role']),
            models.Index(fields=['user', '-joined_at']),
        ]
        verbose_name = 'Project Member'
        verbose_name_plural = 'Project Members'

    def __str__(self):
        return f'{self.user.username} ({self.role}) in {self.project.name}'
```

### 3.3 Study-Project Assignment Model (研究-專案關聯模型)

```python
class StudyProjectAssignment(models.Model):
    """
    Junction table linking studies to projects.
    One study can belong to multiple projects.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='study_assignments'
    )
    study = models.ForeignKey(
        'Study',  # Reference to existing Study model
        on_delete=models.CASCADE,
        related_name='project_assignments',
        to_field='exam_id'  # Link to Study's primary key
    )
    assigned_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True
    )
    assigned_at = models.DateTimeField(auto_now_add=True, db_index=True)
    metadata = models.JSONField(default=dict, blank=True)  # notes, tags, priority

    class Meta:
        db_table = 'study_project_assignments'
        unique_together = [['project', 'study']]
        indexes = [
            models.Index(fields=['project', '-assigned_at']),
            models.Index(fields=['study', 'project']),
        ]
        verbose_name = 'Study-Project Assignment'
        verbose_name_plural = 'Study-Project Assignments'

    def __str__(self):
        return f'Study {self.study.exam_id} in Project {self.project.name}'
```

### 3.4 Database Indexes Strategy (資料庫索引策略)

**索引設計原則**:

1. **Primary Keys**: UUID with automatic indexing
2. **Foreign Keys**: Automatic indexes on all FKs
3. **Composite Indexes**: For common query patterns
4. **Timestamp Indexes**: For sorting and filtering

**預計查詢模式與對應索引**:

| Query Pattern | Index |
|---------------|-------|
| List projects by status and date | `(status, -updated_at)` |
| User's projects ordered by date | `(created_by, -created_at)` |
| Popular projects by study count | `(-study_count)` |
| Project's studies ordered by assignment | `(project, -assigned_at)` |
| Study's projects | `(study, project)` |
| Member's role in project | `(project, role)` |

---

## 四、API Layer Design (API 層設計)

### 4.1 Router Setup (路由設置)

```python
# backend_django/studies/project_api.py

"""
Project API Endpoints for CRUD and advanced operations.

PRAGMATIC DESIGN: Simple endpoints matching actual use cases.
Following the pattern established in report_api.py.
"""

from typing import List, Optional
from ninja import Router, Query
from django.shortcuts import get_object_or_404
from django.db import transaction
from .models import Project, ProjectMember, StudyProjectAssignment
from .project_service import ProjectService
from pydantic import BaseModel
import logging

logger = logging.getLogger(__name__)

# Create router
project_router = Router()
```

### 4.2 Pydantic Schemas (請求/回應架構)

```python
# Request Schemas
class CreateProjectRequest(BaseModel):
    """Schema for creating a new project."""
    name: str
    description: Optional[str] = ''
    tags: List[str] = []
    status: Optional[str] = 'active'
    settings: Optional[dict] = {}

class UpdateProjectRequest(BaseModel):
    """Schema for updating project."""
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    tags: Optional[List[str]] = None
    settings: Optional[dict] = None

class AddStudiesRequest(BaseModel):
    """Schema for adding studies to project."""
    project_id: str
    exam_ids: List[str]

class AddMemberRequest(BaseModel):
    """Schema for adding member to project."""
    user_id: str
    role: str  # owner, admin, editor, viewer

# Response Schemas
class ProjectListItemResponse(BaseModel):
    """Response schema for project list item."""
    id: str
    name: str
    description: Optional[str]
    status: str
    tags: List[str]
    study_count: int
    created_at: str
    updated_at: Optional[str]

class ProjectDetailResponse(ProjectListItemResponse):
    """Extended response with full project details."""
    created_by: Optional[str]
    members: Optional[List[dict]]
    settings: Optional[dict]
    statistics: Optional[dict]
    metadata: Optional[dict]

class ProjectListResponse(BaseModel):
    """Paginated response for project list."""
    total: int
    projects: List[ProjectListItemResponse]
    page: Optional[int]
    pageSize: Optional[int]

class AddStudiesResponse(BaseModel):
    """Response for add studies operation."""
    success: bool
    added_count: int
    project_id: str
    project_name: str
```

### 4.3 Core API Endpoints (核心 API 端點)

**端點列表** (共22個):

```python
# Core CRUD
@project_router.get('', response=ProjectListResponse)
def list_projects(request, ...): pass

@project_router.post('', response=ProjectDetailResponse)
def create_project(request, payload: CreateProjectRequest): pass

@project_router.get('/{project_id}', response=ProjectDetailResponse)
def get_project(request, project_id: str): pass

@project_router.put('/{project_id}', response=ProjectDetailResponse)
def update_project(request, project_id: str, payload: UpdateProjectRequest): pass

@project_router.delete('/{project_id}')
def delete_project(request, project_id: str): pass

# Lifecycle Operations
@project_router.post('/{project_id}/archive')
def archive_project(request, project_id: str): pass

@project_router.post('/{project_id}/restore')
def restore_project(request, project_id: str): pass

@project_router.post('/{project_id}/duplicate', response=ProjectDetailResponse)
def duplicate_project(request, project_id: str): pass

# Statistics
@project_router.get('/{project_id}/statistics')
def get_statistics(request, project_id: str): pass

# Study Management
@project_router.post('/{project_id}/studies', response=AddStudiesResponse)
def add_studies(request, project_id: str, payload: AddStudiesRequest): pass

@project_router.delete('/{project_id}/studies')
def remove_studies(request, project_id: str, exam_ids: List[str]): pass

@project_router.get('/{project_id}/studies')
def get_project_studies(request, project_id: str): pass

@project_router.post('/batch-assign')
def batch_assign_studies(request, payload: dict): pass

# Member Management
@project_router.post('/{project_id}/members')
def add_member(request, project_id: str, payload: AddMemberRequest): pass

@project_router.delete('/{project_id}/members/{user_id}')
def remove_member(request, project_id: str, user_id: str): pass

@project_router.put('/{project_id}/members/{user_id}')
def update_member_role(request, project_id: str, user_id: str, role: str): pass

@project_router.get('/{project_id}/members')
def get_members(request, project_id: str): pass

# Search
@project_router.get('/search')
def search_projects(request, q: str): pass

# Cross-entity queries
# Note: This would be in study_api.py or integrated there
@study_router.get('/{study_id}/projects')
def get_study_projects(request, study_id: str): pass
```

---

## 五、Service Layer Design (服務層設計)

### 5.1 ProjectService Class (專案服務類別)

```python
# backend_django/studies/project_service.py

"""
Project Service Layer - Business Logic
Following the pattern from report_service.py
"""

from django.db import transaction
from django.db.models import Q, Count, Sum
from .models import Project, ProjectMember, StudyProjectAssignment, Study
import logging

logger = logging.getLogger(__name__)

class ProjectService:
    """
    Service class encapsulating project business logic.
    Handles complex operations, query optimization, and data validation.
    """

    @staticmethod
    def get_projects_queryset(
        user=None,
        status=None,
        tags=None,
        search=None,
        date_from=None,
        date_to=None,
        sort_by='updated_at',
        sort_order='desc'
    ):
        """
        Build optimized queryset for project listing with filters.

        Args:
            user: Filter by user (creator or member)
            status: Filter by status (list)
            tags: Filter by tags (list)
            search: Search in name/description
            date_from: Filter from date
            date_to: Filter to date
            sort_by: Sort field
            sort_order: asc or desc

        Returns:
            QuerySet: Filtered and sorted projects
        """
        queryset = Project.objects.all()

        # Apply filters
        if user:
            queryset = queryset.filter(
                Q(created_by=user) | Q(members=user)
            ).distinct()

        if status and len(status) > 0:
            queryset = queryset.filter(status__in=status)

        if tags and len(tags) > 0:
            # JSONField array overlap query
            queryset = queryset.filter(tags__overlap=tags)

        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(description__icontains=search)
            )

        if date_from:
            queryset = queryset.filter(created_at__gte=date_from)

        if date_to:
            queryset = queryset.filter(created_at__lte=date_to)

        # Apply sorting
        sort_field = sort_by
        if sort_order == 'desc':
            sort_field = f'-{sort_field}'

        queryset = queryset.order_by(sort_field)

        # Optimize with select_related for FKs
        queryset = queryset.select_related('created_by')

        return queryset

    @staticmethod
    @transaction.atomic
    def create_project(name, description='', tags=None, status='active',
                      settings=None, user=None):
        """
        Create new project with validation.
        Automatically adds creator as owner.
        """
        project = Project.objects.create(
            name=name,
            description=description,
            tags=tags or [],
            status=status,
            settings=settings or {},
            created_by=user
        )

        # Add creator as owner
        if user:
            ProjectMember.objects.create(
                project=project,
                user=user,
                role='owner'
            )

        logger.info(f'Project created: {project.id} by user {user}')
        return project

    @staticmethod
    @transaction.atomic
    def duplicate_project(project_id, user=None):
        """
        Duplicate project with new ID.
        Does NOT copy study assignments.
        """
        original = Project.objects.get(pk=project_id)

        # Create duplicate with "Copy of" prefix
        duplicate = Project.objects.create(
            name=f'Copy of {original.name}',
            description=original.description,
            tags=original.tags.copy(),
            status='draft',  # Start as draft
            settings=original.settings.copy(),
            created_by=user,
            study_count=0  # Start with zero studies
        )

        # Add creator as owner
        if user:
            ProjectMember.objects.create(
                project=duplicate,
                user=user,
                role='owner'
            )

        logger.info(f'Project duplicated: {project_id} -> {duplicate.id}')
        return duplicate

    @staticmethod
    @transaction.atomic
    def add_studies_to_project(project_id, exam_ids, user=None):
        """
        Batch add studies to project.
        Updates study_count denormalized field.

        Returns:
            dict: Result with added_count
        """
        project = Project.objects.get(pk=project_id)

        # Filter to only existing studies not already in project
        existing_studies = Study.objects.filter(exam_id__in=exam_ids)
        existing_assignments = StudyProjectAssignment.objects.filter(
            project=project,
            study__in=existing_studies
        ).values_list('study_id', flat=True)

        # Create new assignments
        new_assignments = []
        for study in existing_studies:
            if study.exam_id not in existing_assignments:
                new_assignments.append(
                    StudyProjectAssignment(
                        project=project,
                        study=study,
                        assigned_by=user
                    )
                )

        # Bulk create
        created = StudyProjectAssignment.objects.bulk_create(new_assignments)

        # Update denormalized count
        project.study_count = StudyProjectAssignment.objects.filter(
            project=project
        ).count()
        project.save(update_fields=['study_count', 'updated_at'])

        logger.info(f'Added {len(created)} studies to project {project_id}')

        return {
            'success': True,
            'added_count': len(created),
            'project_id': str(project.id),
            'project_name': project.name
        }

    @staticmethod
    def calculate_statistics(project_id):
        """
        Calculate project statistics.
        Aggregates data from assigned studies.
        """
        from django.db.models import Count, Sum

        project = Project.objects.get(pk=project_id)

        # Get assigned studies
        assignments = StudyProjectAssignment.objects.filter(project=project)

        # Calculate statistics
        stats = {
            'studiesCount': assignments.count(),
            'imagesCount': 0,  # Would need DICOM metadata
            'totalSize': 0,    # Would need file size tracking
            'lastActivity': project.updated_at.isoformat() if project.updated_at else None,
            'activeMembers': ProjectMember.objects.filter(project=project).count()
        }

        return stats
```

---

## 六、Permission System Design (權限系統設計)

### 6.1 Permission Matrix (權限矩陣)

| Operation | Owner | Admin | Editor | Viewer |
|-----------|-------|-------|--------|--------|
| View Project | ✅ | ✅ | ✅ | ✅ |
| Edit Project | ✅ | ✅ | ✅ | ❌ |
| Delete Project | ✅ | ❌ | ❌ | ❌ |
| Archive/Restore | ✅ | ✅ | ❌ | ❌ |
| Add/Remove Studies | ✅ | ✅ | ✅ | ❌ |
| Add/Remove Members | ✅ | ✅ | ❌ | ❌ |
| Change Member Roles | ✅ | ✅ (except Owner) | ❌ | ❌ |
| Modify Settings | ✅ | ✅ | ❌ | ❌ |
| Duplicate Project | ✅ | ✅ | ✅ | ✅ |
| Export Data | ✅ | ✅ | ✅ | ✅ |

### 6.2 Permission Check Implementation (權限檢查實作)

```python
# backend_django/studies/permissions.py

from django.core.exceptions import PermissionDenied
from .models import Project, ProjectMember

class ProjectPermissions:
    """
    Permission checker for project operations.
    """

    @staticmethod
    def get_user_role(project, user):
        """Get user's role in project."""
        if not user or not user.is_authenticated:
            return None

        try:
            member = ProjectMember.objects.get(project=project, user=user)
            return member.role
        except ProjectMember.DoesNotExist:
            return None

    @staticmethod
    def can_view(project, user):
        """Check if user can view project."""
        role = ProjectPermissions.get_user_role(project, user)
        return role is not None

    @staticmethod
    def can_edit(project, user):
        """Check if user can edit project."""
        role = ProjectPermissions.get_user_role(project, user)
        return role in ['owner', 'admin', 'editor']

    @staticmethod
    def can_delete(project, user):
        """Check if user can delete project."""
        role = ProjectPermissions.get_user_role(project, user)
        return role == 'owner'

    @staticmethod
    def can_manage_members(project, user):
        """Check if user can manage members."""
        role = ProjectPermissions.get_user_role(project, user)
        return role in ['owner', 'admin']

    @staticmethod
    def require_permission(project, user, action):
        """
        Raise PermissionDenied if user lacks permission.

        Args:
            project: Project instance
            user: User instance
            action: 'view', 'edit', 'delete', 'manage_members'
        """
        permission_map = {
            'view': ProjectPermissions.can_view,
            'edit': ProjectPermissions.can_edit,
            'delete': ProjectPermissions.can_delete,
            'manage_members': ProjectPermissions.can_manage_members,
        }

        check_func = permission_map.get(action)
        if not check_func:
            raise ValueError(f'Unknown permission action: {action}')

        if not check_func(project, user):
            raise PermissionDenied(
                f'User {user} does not have {action} permission for project {project.id}'
            )
```

---

## 七、Database Migration Strategy (資料庫遷移策略)

### 7.1 Migration File (遷移檔案)

```python
# backend_django/studies/migrations/000X_add_project_models.py

from django.db import migrations, models
import django.db.models.deletion
import uuid

class Migration(migrations.Migration):

    dependencies = [
        ('studies', '0001_initial'),  # Depend on Study model
        ('auth', '0012_alter_user_first_name_max_length'),
    ]

    operations = [
        # Create Project model
        migrations.CreateModel(
            name='Project',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('name', models.CharField(db_index=True, max_length=200)),
                ('description', models.TextField(blank=True, default='')),
                ('status', models.CharField(choices=[...], db_index=True, default='active', max_length=20)),
                ('tags', models.JSONField(blank=True, default=list)),
                ('study_count', models.IntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('settings', models.JSONField(blank=True, default=dict)),
                ('metadata', models.JSONField(blank=True, default=dict)),
                ('created_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='created_projects', to='auth.user')),
            ],
            options={
                'verbose_name': 'Project',
                'verbose_name_plural': 'Projects',
                'db_table': 'projects',
                'ordering': ['-updated_at'],
            },
        ),

        # Create ProjectMember model
        migrations.CreateModel(
            name='ProjectMember',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('role', models.CharField(choices=[...], default='viewer', max_length=20)),
                ('joined_at', models.DateTimeField(auto_now_add=True)),
                ('permissions', models.JSONField(blank=True, default=list)),
                ('project', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='project_members', to='studies.project')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='project_memberships', to='auth.user')),
            ],
            options={
                'verbose_name': 'Project Member',
                'verbose_name_plural': 'Project Members',
                'db_table': 'project_members',
                'unique_together': {('project', 'user')},
            },
        ),

        # Create StudyProjectAssignment model
        migrations.CreateModel(
            name='StudyProjectAssignment',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('assigned_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('metadata', models.JSONField(blank=True, default=dict)),
                ('assigned_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='auth.user')),
                ('project', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='study_assignments', to='studies.project')),
                ('study', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='project_assignments', to='studies.study', to_field='exam_id')),
            ],
            options={
                'verbose_name': 'Study-Project Assignment',
                'verbose_name_plural': 'Study-Project Assignments',
                'db_table': 'study_project_assignments',
                'unique_together': {('project', 'study')},
            },
        ),

        # Add indexes
        migrations.AddIndex(
            model_name='project',
            index=models.Index(fields=['status', '-updated_at'], name='projects_status_updated_idx'),
        ),
        migrations.AddIndex(
            model_name='project',
            index=models.Index(fields=['created_by', '-created_at'], name='projects_creator_created_idx'),
        ),
        migrations.AddIndex(
            model_name='project',
            index=models.Index(fields=['-study_count'], name='projects_study_count_idx'),
        ),

        # Add ManyToMany relationship
        migrations.AddField(
            model_name='project',
            name='members',
            field=models.ManyToManyField(related_name='projects', through='studies.ProjectMember', to='auth.user'),
        ),
    ]
```

### 7.2 Migration Execution Plan (遷移執行計畫)

```bash
# Step 1: Create migration file
python manage.py makemigrations studies

# Step 2: Review SQL (dry run)
python manage.py sqlmigrate studies 000X

# Step 3: Check for issues
python manage.py check

# Step 4: Run migration
python manage.py migrate studies

# Step 5: Verify tables created
python manage.py dbshell
\dt projects*
\dt study_project*
```

---

## 八、Testing Strategy (測試策略)

### 8.1 Unit Tests (單元測試)

```python
# backend_django/tests/test_project_api.py

import pytest
from django.test import TestCase
from django.contrib.auth.models import User
from studies.models import Project, ProjectMember
from studies.project_service import ProjectService

class ProjectModelTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='test', password='test123')

    def test_create_project(self):
        """Test project creation."""
        project = Project.objects.create(
            name='Test Project',
            description='Test description',
            created_by=self.user
        )
        self.assertEqual(project.name, 'Test Project')
        self.assertEqual(project.status, 'active')
        self.assertEqual(project.study_count, 0)

    def test_project_member_creation(self):
        """Test adding member to project."""
        project = Project.objects.create(name='Test', created_by=self.user)
        member = ProjectMember.objects.create(
            project=project,
            user=self.user,
            role='owner'
        )
        self.assertEqual(member.role, 'owner')

    def test_duplicate_project(self):
        """Test project duplication."""
        original = Project.objects.create(name='Original', created_by=self.user)
        duplicate = ProjectService.duplicate_project(original.id, self.user)

        self.assertNotEqual(original.id, duplicate.id)
        self.assertEqual(duplicate.name, 'Copy of Original')
        self.assertEqual(duplicate.study_count, 0)

class ProjectAPITestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='test', password='test123')
        self.client.force_login(self.user)

    def test_list_projects(self):
        """Test GET /api/v1/projects."""
        response = self.client.get('/api/v1/projects')
        self.assertEqual(response.status_code, 200)

    def test_create_project(self):
        """Test POST /api/v1/projects."""
        data = {
            'name': 'New Project',
            'description': 'Test description',
            'tags': ['test']
        }
        response = self.client.post('/api/v1/projects', data, content_type='application/json')
        self.assertEqual(response.status_code, 201)

    def test_permission_enforcement(self):
        """Test permission checks."""
        other_user = User.objects.create_user(username='other', password='test123')
        project = Project.objects.create(name='Private', created_by=other_user)

        response = self.client.delete(f'/api/v1/projects/{project.id}')
        self.assertEqual(response.status_code, 403)  # Forbidden
```

### 8.2 Integration Tests (整合測試)

測試完整工作流程:
1. Create project → Add studies → Get statistics
2. Add member → Update role → Remove member
3. Archive project → Restore → Verify status
4. Filter projects → Sort → Pagination

### 8.3 Performance Tests (效能測試)

```python
def test_list_projects_performance(self):
    """Test list performance with large dataset."""
    # Create 1000 projects
    projects = [
        Project(name=f'Project {i}', created_by=self.user)
        for i in range(1000)
    ]
    Project.objects.bulk_create(projects)

    # Measure query time
    import time
    start = time.time()
    response = self.client.get('/api/v1/projects?page=1&pageSize=50')
    elapsed = time.time() - start

    self.assertEqual(response.status_code, 200)
    self.assertLess(elapsed, 0.5)  # Should be < 500ms
```

---

## 九、Implementation Roadmap (實作路線圖)

### 9.1 Phase 1: Foundation (第一階段：基礎建置) - 2 days

**Day 1: Data Models**
- [ ] Define Django models (Project, ProjectMember, StudyProjectAssignment)
- [ ] Create migration file
- [ ] Run migrations and verify tables
- [ ] Write model unit tests

**Day 2: Service Layer**
- [ ] Implement ProjectService class
- [ ] Add query optimization methods
- [ ] Implement permission checks
- [ ] Write service layer tests

### 9.2 Phase 2: API Core (第二階段：核心 API) - 3 days

**Day 3: CRUD Endpoints**
- [ ] Implement list, create, get, update, delete endpoints
- [ ] Add Pydantic schemas
- [ ] Implement error handling
- [ ] Write API tests

**Day 4: Lifecycle & Study Management**
- [ ] Implement archive/restore/duplicate
- [ ] Implement add/remove studies
- [ ] Implement statistics calculation
- [ ] Write integration tests

**Day 5: Member & Search**
- [ ] Implement member management endpoints
- [ ] Implement search and filter
- [ ] Add batch operations
- [ ] Write E2E tests

### 9.3 Phase 3: Integration (第三階段：整合) - 2 days

**Day 6: Frontend Integration**
- [ ] Register router in API config
- [ ] Test all 22 endpoints with frontend
- [ ] Fix any contract mismatches
- [ ] Update API documentation

**Day 7: Polish & Deployment**
- [ ] Performance optimization
- [ ] Add logging and monitoring
- [ ] Security audit
- [ ] Production deployment

**Total Estimated Time**: 7 working days

---

## 十、Performance Optimization (效能優化)

### 10.1 Query Optimization (查詢優化)

```python
# Bad: N+1 query problem
projects = Project.objects.all()
for project in projects:
    print(project.created_by.username)  # N queries

# Good: Use select_related
projects = Project.objects.select_related('created_by').all()
for project in projects:
    print(project.created_by.username)  # 1 query
```

### 10.2 Caching Strategy (快取策略)

1. **Database Query Caching**
   - Cache expensive aggregation queries
   - TTL: 5 minutes for statistics

2. **Denormalization**
   - `study_count` field updated on assignment changes
   - Avoids COUNT queries on every list request

3. **API Response Caching**
   - Cache filter options (status list, tags)
   - Cache project list for common filters

---

## 十一、Security Considerations (安全性考量)

### 11.1 Authentication (身分驗證)

- Use Django's built-in authentication
- Require JWT/Bearer token for all API calls
- Validate token on every request

### 11.2 Authorization (授權)

- Check user permissions before operations
- Enforce role-based access control
- Prevent privilege escalation

### 11.3 Data Validation (資料驗證)

- Validate all user input with Pydantic
- Sanitize text fields to prevent XSS
- Limit array sizes to prevent DoS

### 11.4 Rate Limiting (速率限制)

- Limit API calls per user: 100 req/min
- Throttle expensive operations (duplicate, batch assign)
- Log suspicious activity

---

## 十二、Monitoring and Logging (監控與日誌)

### 12.1 Logging Strategy (日誌策略)

```python
import logging

logger = logging.getLogger(__name__)

# Log levels
logger.info('Project created: proj_123')       # Normal operations
logger.warning('Permission denied for user 456')  # Security events
logger.error('Failed to add studies: DB error')   # Errors
logger.critical('Database connection lost')       # Critical issues
```

### 12.2 Metrics to Track (追蹤指標)

| Metric | Description | Alert Threshold |
|--------|-------------|-----------------|
| API Response Time | Avg response time | > 1 second |
| Error Rate | % of failed requests | > 5% |
| Project Creation Rate | Projects/day | Unusual spike |
| Study Assignment Rate | Assignments/day | Unusual spike |
| Active Users | Daily active users | Decline > 20% |

---

## 十三、Conclusion (結論)

### 13.1 Implementation Checklist (實作檢查清單)

**Backend Components**:
- [ ] Django models (Project, ProjectMember, StudyProjectAssignment)
- [ ] Database migration file
- [ ] Service layer (ProjectService)
- [ ] Permission system (ProjectPermissions)
- [ ] API router (project_router with 22 endpoints)
- [ ] Pydantic schemas (Request/Response)
- [ ] Unit tests (models, service, permissions)
- [ ] Integration tests (API endpoints)
- [ ] E2E tests (complete workflows)

**Integration & Deployment**:
- [ ] Register router in API config
- [ ] Frontend integration testing
- [ ] Performance optimization
- [ ] Security audit
- [ ] Documentation update
- [ ] Production deployment

### 13.2 Dependencies (依賴項)

**Existing Backend Components**:
- ✅ Django 5.1 installed
- ✅ Django Ninja configured
- ✅ PostgreSQL database
- ✅ Study model exists
- ✅ Authentication system in place

**Required External Services**: None (self-contained implementation)

### 13.3 Risks and Mitigation (風險與緩解)

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Performance issues with large datasets | High | Medium | Implement proper indexing, pagination, caching |
| Permission system bugs | High | Low | Comprehensive unit tests, security audit |
| Data migration failures | High | Low | Test migrations thoroughly, have rollback plan |
| API contract mismatch | Medium | Medium | Strict Pydantic validation, integration tests |
| Concurrent update conflicts | Medium | Low | Use database transactions, optimistic locking |

### 13.4 Success Criteria (成功標準)

1. ✅ All 22 API endpoints implemented and tested
2. ✅ Frontend integration 100% functional
3. ✅ Response time < 500ms (95th percentile)
4. ✅ Test coverage ≥ 80%
5. ✅ Zero security vulnerabilities
6. ✅ Production deployment successful

### 13.5 Next Steps (下一步)

1. ✅ Frontend requirements documented
2. ✅ Backend requirements documented
3. 📝 待使用者確認需求
4. ⏳ 開始實作 Phase 1 (資料模型)
5. ⏳ 開始實作 Phase 2 (API 端點)
6. ⏳ 開始實作 Phase 3 (整合測試)

---

**Document Status**: ✅ Complete and Ready for Implementation
**Awaiting**: User confirmation to proceed with implementation
**Estimated Timeline**: 7 working days for full implementation

