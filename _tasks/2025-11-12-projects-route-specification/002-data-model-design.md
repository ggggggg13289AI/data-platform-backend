# Projects Route 資料模型設計文件

**文件版本**：1.0  
**建立日期**：2025-11-12  
**文件狀態**：✅ 設計完成  
**作者**：Claude Code  
**專案**：醫學影像資料管理平台

---

## 📋 文件目的

本文件定義 Projects 功能的完整資料模型設計，包含：

1. 資料庫 Schema 設計
2. ER 圖與關聯說明
3. 索引策略
4. Django 模型實作規格
5. 資料遷移計畫

---

## 🗂️ 資料庫架構總覽

### 核心表格

| 表名 | 用途 | 記錄數預估 | 增長速度 |
|------|------|-----------|---------|
| **projects** | 專案主表 | 1,000-10,000 | 中等 |
| **project_members** | 專案成員關聯 | 5,000-50,000 | 快速 |
| **study_project_assignments** | 研究-專案關聯 | 10,000-100,000 | 快速 |

### 關聯圖（文字版ER圖）

```
┌─────────────────┐
│   auth_user     │
│   (現有表格)    │
└────────┬────────┘
         │ 1
         │ created_by
         │
         │ N
┌────────┴────────┐
│    projects     │◄────┐
│                 │     │
│ id (PK)         │     │
│ name            │     │
│ description     │     │
│ status          │     │
│ tags            │     │
│ study_count     │     │ 1
│ created_by_id   │     │
│ created_at      │     │
│ updated_at      │     │
│ settings        │     │
│ metadata        │     │
└────────┬────────┘     │
         │              │
         │ 1            │
         │              │
         │ N            │
    ┌────┴──────────────┴────┐
    │   project_members      │
    │                        │
    │ id (PK)                │
    │ project_id (FK)        │
    │ user_id (FK)           │
    │ role                   │
    │ joined_at              │
    │ permissions            │
    │                        │
    │ UNIQUE(project, user)  │
    └────────────────────────┘


┌──────────────────────┐
│      projects        │
└──────────┬───────────┘
           │ 1
           │
           │ N
    ┌──────┴───────────────────────┐
    │ study_project_assignments    │
    │                              │
    │ id (PK)                      │
    │ project_id (FK)              │
    │ study_id (FK→exam_id)        │
    │ assigned_by_id (FK)          │
    │ assigned_at                  │
    │ metadata                     │
    │                              │
    │ UNIQUE(project, study)       │
    └──────────┬───────────────────┘
               │ N
               │
               │ 1
      ┌────────┴──────────┐
      │      studies      │
      │    (現有表格)     │
      │                   │
      │ exam_id (PK)      │
      │ patient_name      │
      │ exam_date         │
      │ modality          │
      │ ...               │
      └───────────────────┘
```

---

## 📊 表格詳細設計

### 表 1：projects（專案主表）

#### 用途
儲存專案的基本資訊與元數據

#### Schema 設計

| 欄位名 | 資料型別 | 約束 | 預設值 | 說明 |
|--------|---------|------|--------|------|
| **id** | UUID | PRIMARY KEY | uuid_generate_v4() | 專案唯一識別碼 |
| **name** | VARCHAR(200) | NOT NULL | - | 專案名稱 |
| **description** | TEXT | NULL | - | 專案描述 |
| **status** | VARCHAR(20) | NOT NULL | 'active' | 專案狀態 |
| **tags** | JSONB | NOT NULL | '[]' | 標籤陣列 |
| **study_count** | INTEGER | NOT NULL | 0 | 研究數量（denormalized） |
| **created_by_id** | UUID | NOT NULL, FK | - | 建立者 ID |
| **created_at** | TIMESTAMPTZ | NOT NULL | NOW() | 建立時間 |
| **updated_at** | TIMESTAMPTZ | NOT NULL | NOW() | 更新時間 |
| **settings** | JSONB | NOT NULL | '{}' | 專案設定 |
| **metadata** | JSONB | NOT NULL | '{}' | 擴充元數據 |

#### 約束定義

```sql
-- 主鍵
CONSTRAINT pk_projects PRIMARY KEY (id)

-- 外鍵
CONSTRAINT fk_projects_created_by 
    FOREIGN KEY (created_by_id) 
    REFERENCES auth_user(id) 
    ON DELETE RESTRICT

-- 檢查約束
CONSTRAINT chk_projects_status 
    CHECK (status IN ('active', 'archived', 'completed', 'draft'))

CONSTRAINT chk_projects_study_count 
    CHECK (study_count >= 0)

CONSTRAINT chk_projects_name_not_empty 
    CHECK (LENGTH(TRIM(name)) > 0)
```

#### 索引策略

```sql
-- 主鍵索引（自動建立）
CREATE UNIQUE INDEX pk_projects_id ON projects(id);

-- 複合索引：狀態 + 更新時間（列表查詢優化）
CREATE INDEX idx_projects_status_updated 
    ON projects(status, updated_at DESC);

-- 複合索引：建立者 + 建立時間（使用者的專案查詢）
CREATE INDEX idx_projects_created_by_created 
    ON projects(created_by_id, created_at DESC);

-- 單欄索引：研究數量（排序優化）
CREATE INDEX idx_projects_study_count 
    ON projects(study_count DESC);

-- GIN 索引：標籤搜尋
CREATE INDEX idx_projects_tags 
    ON projects USING GIN(tags);

-- 全文搜尋索引（選用）
CREATE INDEX idx_projects_name_trgm 
    ON projects USING gin(name gin_trgm_ops);
```

#### 範例資料

```sql
INSERT INTO projects (id, name, description, status, tags, study_count, created_by_id) VALUES
    ('123e4567-e89b-12d3-a456-426614174000', 
     '肺癌研究專案', 
     '針對早期肺癌診斷的影像研究', 
     'active', 
     '["肺癌", "診斷", "CT"]'::jsonb, 
     15, 
     'user-uuid-001');
```

---

### 表 2：project_members（專案成員關聯表）

#### 用途
管理專案成員及其角色權限

#### Schema 設計

| 欄位名 | 資料型別 | 約束 | 預設值 | 說明 |
|--------|---------|------|--------|------|
| **id** | UUID | PRIMARY KEY | uuid_generate_v4() | 成員記錄 ID |
| **project_id** | UUID | NOT NULL, FK | - | 專案 ID |
| **user_id** | UUID | NOT NULL, FK | - | 使用者 ID |
| **role** | VARCHAR(20) | NOT NULL | 'viewer' | 成員角色 |
| **joined_at** | TIMESTAMPTZ | NOT NULL | NOW() | 加入時間 |
| **permissions** | JSONB | NOT NULL | '[]' | 自訂權限陣列 |

#### 約束定義

```sql
-- 主鍵
CONSTRAINT pk_project_members PRIMARY KEY (id)

-- 外鍵
CONSTRAINT fk_project_members_project 
    FOREIGN KEY (project_id) 
    REFERENCES projects(id) 
    ON DELETE CASCADE

CONSTRAINT fk_project_members_user 
    FOREIGN KEY (user_id) 
    REFERENCES auth_user(id) 
    ON DELETE CASCADE

-- 唯一性約束
CONSTRAINT uq_project_members_project_user 
    UNIQUE (project_id, user_id)

-- 檢查約束
CONSTRAINT chk_project_members_role 
    CHECK (role IN ('owner', 'admin', 'editor', 'viewer'))
```

#### 索引策略

```sql
-- 主鍵索引（自動建立）
CREATE UNIQUE INDEX pk_project_members_id ON project_members(id);

-- 唯一複合索引（確保不重複成員）
CREATE UNIQUE INDEX uq_project_members_project_user 
    ON project_members(project_id, user_id);

-- 單欄索引：專案查詢
CREATE INDEX idx_project_members_project 
    ON project_members(project_id);

-- 單欄索引：使用者查詢
CREATE INDEX idx_project_members_user 
    ON project_members(user_id);

-- 複合索引：專案 + 角色（權限查詢優化）
CREATE INDEX idx_project_members_project_role 
    ON project_members(project_id, role);
```

#### 範例資料

```sql
INSERT INTO project_members (id, project_id, user_id, role, joined_at) VALUES
    ('223e4567-e89b-12d3-a456-426614174000', 
     '123e4567-e89b-12d3-a456-426614174000', 
     'user-uuid-001', 
     'owner', 
     '2025-11-01 10:00:00+00'),
    ('323e4567-e89b-12d3-a456-426614174000', 
     '123e4567-e89b-12d3-a456-426614174000', 
     'user-uuid-002', 
     'editor', 
     '2025-11-05 14:30:00+00');
```

---

### 表 3：study_project_assignments（研究-專案關聯表）

#### 用途
管理研究與專案之間的多對多關係

#### Schema 設計

| 欄位名 | 資料型別 | 約束 | 預設值 | 說明 |
|--------|---------|------|--------|------|
| **id** | UUID | PRIMARY KEY | uuid_generate_v4() | 分配記錄 ID |
| **project_id** | UUID | NOT NULL, FK | - | 專案 ID |
| **study_id** | VARCHAR(255) | NOT NULL, FK | - | 研究 ID (exam_id) |
| **assigned_by_id** | UUID | NOT NULL, FK | - | 分配者 ID |
| **assigned_at** | TIMESTAMPTZ | NOT NULL | NOW() | 分配時間 |
| **metadata** | JSONB | NOT NULL | '{}' | 擴充元數據 |

#### 約束定義

```sql
-- 主鍵
CONSTRAINT pk_study_project_assignments PRIMARY KEY (id)

-- 外鍵
CONSTRAINT fk_spa_project 
    FOREIGN KEY (project_id) 
    REFERENCES projects(id) 
    ON DELETE CASCADE

CONSTRAINT fk_spa_study 
    FOREIGN KEY (study_id) 
    REFERENCES studies(exam_id) 
    ON DELETE CASCADE

CONSTRAINT fk_spa_assigned_by 
    FOREIGN KEY (assigned_by_id) 
    REFERENCES auth_user(id) 
    ON DELETE RESTRICT

-- 唯一性約束
CONSTRAINT uq_spa_project_study 
    UNIQUE (project_id, study_id)
```

#### 索引策略

```sql
-- 主鍵索引（自動建立）
CREATE UNIQUE INDEX pk_study_project_assignments_id 
    ON study_project_assignments(id);

-- 唯一複合索引（確保不重複分配）
CREATE UNIQUE INDEX uq_spa_project_study 
    ON study_project_assignments(project_id, study_id);

-- 複合索引：專案 + 分配時間（專案研究列表查詢）
CREATE INDEX idx_spa_project_assigned 
    ON study_project_assignments(project_id, assigned_at DESC);

-- 複合索引：研究 + 專案（研究所屬專案查詢）
CREATE INDEX idx_spa_study_project 
    ON study_project_assignments(study_id, project_id);

-- 單欄索引：分配者（審計查詢）
CREATE INDEX idx_spa_assigned_by 
    ON study_project_assignments(assigned_by_id);
```

#### 範例資料

```sql
INSERT INTO study_project_assignments 
    (id, project_id, study_id, assigned_by_id, assigned_at) 
VALUES
    ('423e4567-e89b-12d3-a456-426614174000', 
     '123e4567-e89b-12d3-a456-426614174000', 
     'exam_001', 
     'user-uuid-001', 
     '2025-11-10 10:00:00+00'),
    ('523e4567-e89b-12d3-a456-426614174000', 
     '123e4567-e89b-12d3-a456-426614174000', 
     'exam_002', 
     'user-uuid-001', 
     '2025-11-10 10:05:00+00');
```

---

## 🔧 Django 模型實作規格

### Model 1: Project

```python
from django.db import models
from django.contrib.auth.models import User
import uuid

class Project(models.Model):
    """專案模型"""
    
    # Status choices
    STATUS_ACTIVE = 'active'
    STATUS_ARCHIVED = 'archived'
    STATUS_COMPLETED = 'completed'
    STATUS_DRAFT = 'draft'
    
    STATUS_CHOICES = [
        (STATUS_ACTIVE, '進行中'),
        (STATUS_ARCHIVED, '已封存'),
        (STATUS_COMPLETED, '已完成'),
        (STATUS_DRAFT, '草稿'),
    ]
    
    # Primary Key
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name='專案ID'
    )
    
    # Basic Information
    name = models.CharField(
        max_length=200,
        verbose_name='專案名稱',
        db_index=True
    )
    
    description = models.TextField(
        blank=True,
        verbose_name='專案描述'
    )
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_ACTIVE,
        verbose_name='狀態',
        db_index=True
    )
    
    # Tags
    tags = models.JSONField(
        default=list,
        verbose_name='標籤'
    )
    
    # Denormalized Fields
    study_count = models.IntegerField(
        default=0,
        verbose_name='研究數量'
    )
    
    # Relationships
    created_by = models.ForeignKey(
        User,
        on_delete=models.RESTRICT,
        related_name='created_projects',
        verbose_name='建立者'
    )
    
    members = models.ManyToManyField(
        User,
        through='ProjectMember',
        related_name='projects',
        verbose_name='成員'
    )
    
    # Timestamps
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='建立時間'
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='更新時間'
    )
    
    # Flexible Fields
    settings = models.JSONField(
        default=dict,
        verbose_name='設定'
    )
    
    metadata = models.JSONField(
        default=dict,
        verbose_name='元數據'
    )
    
    class Meta:
        db_table = 'projects'
        verbose_name = '專案'
        verbose_name_plural = '專案'
        ordering = ['-updated_at']
        indexes = [
            models.Index(fields=['status', '-updated_at'], 
                        name='idx_proj_status_updated'),
            models.Index(fields=['created_by', '-created_at'], 
                        name='idx_proj_creator_created'),
            models.Index(fields=['-study_count'], 
                        name='idx_proj_study_count'),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.get_status_display()})"
    
    def to_dict(self):
        """轉換為字典格式（API 序列化）"""
        return {
            'id': str(self.id),
            'name': self.name,
            'description': self.description,
            'status': self.status,
            'tags': self.tags,
            'study_count': self.study_count,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'created_by': {
                'id': str(self.created_by.id),
                'name': self.created_by.get_full_name() or self.created_by.username,
            },
            'settings': self.settings,
            'metadata': self.metadata,
        }
    
    def get_user_role(self, user):
        """取得使用者在專案中的角色"""
        try:
            member = self.project_members.get(user=user)
            return member.role
        except ProjectMember.DoesNotExist:
            return None
    
    def get_user_permissions(self, user):
        """取得使用者在專案中的權限列表"""
        role = self.get_user_role(user)
        if not role:
            return []
        
        # 權限映射（依角色定義）
        permissions_map = {
            'owner': ['view', 'edit', 'delete', 'manage_members', 'manage_studies'],
            'admin': ['view', 'edit', 'manage_members', 'manage_studies'],
            'editor': ['view', 'edit', 'manage_studies'],
            'viewer': ['view'],
        }
        
        return permissions_map.get(role, [])
    
    def increment_study_count(self, count=1):
        """增加研究計數"""
        self.study_count = models.F('study_count') + count
        self.save(update_fields=['study_count'])
        self.refresh_from_db()
    
    def decrement_study_count(self, count=1):
        """減少研究計數"""
        self.study_count = models.F('study_count') - count
        self.save(update_fields=['study_count'])
        self.refresh_from_db()
```

### Model 2: ProjectMember

```python
class ProjectMember(models.Model):
    """專案成員模型（Through Model）"""
    
    # Role choices
    ROLE_OWNER = 'owner'
    ROLE_ADMIN = 'admin'
    ROLE_EDITOR = 'editor'
    ROLE_VIEWER = 'viewer'
    
    ROLE_CHOICES = [
        (ROLE_OWNER, '擁有者'),
        (ROLE_ADMIN, '管理員'),
        (ROLE_EDITOR, '編輯者'),
        (ROLE_VIEWER, '檢視者'),
    ]
    
    # Primary Key
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    
    # Relationships
    project = models.ForeignKey(
        'Project',
        on_delete=models.CASCADE,
        related_name='project_members',
        verbose_name='專案'
    )
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='project_memberships',
        verbose_name='使用者'
    )
    
    # Role
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default=ROLE_VIEWER,
        verbose_name='角色'
    )
    
    # Timestamps
    joined_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='加入時間'
    )
    
    # Custom Permissions (Optional)
    permissions = models.JSONField(
        default=list,
        verbose_name='自訂權限'
    )
    
    class Meta:
        db_table = 'project_members'
        verbose_name = '專案成員'
        verbose_name_plural = '專案成員'
        unique_together = [['project', 'user']]
        ordering = ['project', '-joined_at']
        indexes = [
            models.Index(fields=['project'], name='idx_pm_project'),
            models.Index(fields=['user'], name='idx_pm_user'),
            models.Index(fields=['project', 'role'], name='idx_pm_proj_role'),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.project.name} ({self.get_role_display()})"
    
    def to_dict(self):
        """轉換為字典格式"""
        return {
            'user_id': str(self.user.id),
            'name': self.user.get_full_name() or self.user.username,
            'email': self.user.email,
            'role': self.role,
            'joined_at': self.joined_at.isoformat(),
            'permissions': self.permissions,
        }
```

### Model 3: StudyProjectAssignment

```python
class StudyProjectAssignment(models.Model):
    """研究-專案分配模型"""
    
    # Primary Key
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    
    # Relationships
    project = models.ForeignKey(
        'Project',
        on_delete=models.CASCADE,
        related_name='study_assignments',
        verbose_name='專案'
    )
    
    study = models.ForeignKey(
        'Study',  # 引用現有的 Study 模型
        to_field='exam_id',  # 使用 exam_id 作為外鍵
        on_delete=models.CASCADE,
        related_name='project_assignments',
        verbose_name='研究'
    )
    
    assigned_by = models.ForeignKey(
        User,
        on_delete=models.RESTRICT,
        related_name='study_assignments',
        verbose_name='分配者'
    )
    
    # Timestamps
    assigned_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='分配時間'
    )
    
    # Metadata
    metadata = models.JSONField(
        default=dict,
        verbose_name='元數據'
    )
    
    class Meta:
        db_table = 'study_project_assignments'
        verbose_name = '研究分配'
        verbose_name_plural = '研究分配'
        unique_together = [['project', 'study']]
        ordering = ['project', '-assigned_at']
        indexes = [
            models.Index(fields=['project', '-assigned_at'], 
                        name='idx_spa_proj_assigned'),
            models.Index(fields=['study', 'project'], 
                        name='idx_spa_study_proj'),
            models.Index(fields=['assigned_by'], 
                        name='idx_spa_assigned_by'),
        ]
    
    def __str__(self):
        return f"{self.study.exam_id} → {self.project.name}"
    
    def to_dict(self):
        """轉換為字典格式"""
        return {
            'id': str(self.id),
            'project_id': str(self.project.id),
            'study_id': self.study.exam_id,
            'assigned_by': {
                'id': str(self.assigned_by.id),
                'name': self.assigned_by.get_full_name() or self.assigned_by.username,
            },
            'assigned_at': self.assigned_at.isoformat(),
            'metadata': self.metadata,
        }
```

---

## 📈 索引效能分析

### 索引覆蓋率分析

| 查詢類型 | 使用索引 | 效能影響 |
|---------|---------|---------|
| **列出使用者的專案** | idx_projects_created_by_created | 🟢 優秀 |
| **列出活躍專案** | idx_projects_status_updated | 🟢 優秀 |
| **搜尋專案（關鍵字）** | idx_projects_name_trgm (GIN) | 🟡 良好 |
| **搜尋專案（標籤）** | idx_projects_tags (GIN) | 🟢 優秀 |
| **查詢專案成員** | idx_pm_project | 🟢 優秀 |
| **查詢使用者所屬專案** | idx_pm_user | 🟢 優秀 |
| **列出專案的研究** | idx_spa_proj_assigned | 🟢 優秀 |
| **查詢研究所屬專案** | idx_spa_study_proj | 🟢 優秀 |

### 索引大小預估

假設資料規模：
- 10,000 專案
- 50,000 專案成員記錄
- 100,000 研究分配記錄

| 表格 | 資料大小 | 索引大小 | 總大小 |
|------|---------|---------|--------|
| projects | ~5 MB | ~3 MB | ~8 MB |
| project_members | ~10 MB | ~8 MB | ~18 MB |
| study_project_assignments | ~20 MB | ~15 MB | ~35 MB |
| **總計** | **~35 MB** | **~26 MB** | **~61 MB** |

---

## 🔄 資料遷移計畫

### Migration 001: 建立基礎表格

```python
# studies/migrations/000X_add_project_models.py

from django.db import migrations, models
import django.db.models.deletion
import uuid

class Migration(migrations.Migration):

    dependencies = [
        ('studies', '000X_previous_migration'),
        ('auth', '0012_alter_user_first_name_max_length'),
    ]

    operations = [
        # 建立 projects 表
        migrations.CreateModel(
            name='Project',
            fields=[
                ('id', models.UUIDField(
                    default=uuid.uuid4, 
                    editable=False, 
                    primary_key=True, 
                    serialize=False
                )),
                ('name', models.CharField(max_length=200)),
                ('description', models.TextField(blank=True)),
                ('status', models.CharField(
                    choices=[
                        ('active', '進行中'),
                        ('archived', '已封存'),
                        ('completed', '已完成'),
                        ('draft', '草稿')
                    ],
                    default='active',
                    max_length=20
                )),
                ('tags', models.JSONField(default=list)),
                ('study_count', models.IntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('settings', models.JSONField(default=dict)),
                ('metadata', models.JSONField(default=dict)),
                ('created_by', models.ForeignKey(
                    on_delete=django.db.models.deletion.RESTRICT,
                    related_name='created_projects',
                    to='auth.user'
                )),
            ],
            options={
                'db_table': 'projects',
                'verbose_name': '專案',
                'verbose_name_plural': '專案',
                'ordering': ['-updated_at'],
            },
        ),
        
        # 建立 project_members 表
        migrations.CreateModel(
            name='ProjectMember',
            fields=[
                ('id', models.UUIDField(
                    default=uuid.uuid4,
                    editable=False,
                    primary_key=True,
                    serialize=False
                )),
                ('role', models.CharField(
                    choices=[
                        ('owner', '擁有者'),
                        ('admin', '管理員'),
                        ('editor', '編輯者'),
                        ('viewer', '檢視者')
                    ],
                    default='viewer',
                    max_length=20
                )),
                ('joined_at', models.DateTimeField(auto_now_add=True)),
                ('permissions', models.JSONField(default=list)),
                ('project', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='project_members',
                    to='studies.project'
                )),
                ('user', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='project_memberships',
                    to='auth.user'
                )),
            ],
            options={
                'db_table': 'project_members',
                'verbose_name': '專案成員',
                'verbose_name_plural': '專案成員',
                'ordering': ['project', '-joined_at'],
            },
        ),
        
        # 建立 study_project_assignments 表
        migrations.CreateModel(
            name='StudyProjectAssignment',
            fields=[
                ('id', models.UUIDField(
                    default=uuid.uuid4,
                    editable=False,
                    primary_key=True,
                    serialize=False
                )),
                ('assigned_at', models.DateTimeField(auto_now_add=True)),
                ('metadata', models.JSONField(default=dict)),
                ('assigned_by', models.ForeignKey(
                    on_delete=django.db.models.deletion.RESTRICT,
                    related_name='study_assignments',
                    to='auth.user'
                )),
                ('project', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='study_assignments',
                    to='studies.project'
                )),
                ('study', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='project_assignments',
                    to='studies.study',
                    to_field='exam_id'
                )),
            ],
            options={
                'db_table': 'study_project_assignments',
                'verbose_name': '研究分配',
                'verbose_name_plural': '研究分配',
                'ordering': ['project', '-assigned_at'],
            },
        ),
        
        # 新增唯一性約束
        migrations.AddConstraint(
            model_name='projectmember',
            constraint=models.UniqueConstraint(
                fields=['project', 'user'],
                name='uq_project_members_project_user'
            ),
        ),
        migrations.AddConstraint(
            model_name='studyprojectassignment',
            constraint=models.UniqueConstraint(
                fields=['project', 'study'],
                name='uq_spa_project_study'
            ),
        ),
        
        # 新增索引
        migrations.AddIndex(
            model_name='project',
            index=models.Index(
                fields=['status', '-updated_at'],
                name='idx_proj_status_updated'
            ),
        ),
        migrations.AddIndex(
            model_name='project',
            index=models.Index(
                fields=['created_by', '-created_at'],
                name='idx_proj_creator_created'
            ),
        ),
        migrations.AddIndex(
            model_name='project',
            index=models.Index(
                fields=['-study_count'],
                name='idx_proj_study_count'
            ),
        ),
        migrations.AddIndex(
            model_name='projectmember',
            index=models.Index(
                fields=['project'],
                name='idx_pm_project'
            ),
        ),
        migrations.AddIndex(
            model_name='projectmember',
            index=models.Index(
                fields=['user'],
                name='idx_pm_user'
            ),
        ),
        migrations.AddIndex(
            model_name='projectmember',
            index=models.Index(
                fields=['project', 'role'],
                name='idx_pm_proj_role'
            ),
        ),
        migrations.AddIndex(
            model_name='studyprojectassignment',
            index=models.Index(
                fields=['project', '-assigned_at'],
                name='idx_spa_proj_assigned'
            ),
        ),
        migrations.AddIndex(
            model_name='studyprojectassignment',
            index=models.Index(
                fields=['study', 'project'],
                name='idx_spa_study_proj'
            ),
        ),
        migrations.AddIndex(
            model_name='studyprojectassignment',
            index=models.Index(
                fields=['assigned_by'],
                name='idx_spa_assigned_by'
            ),
        ),
    ]
```

### 遷移回滾計畫

```python
# 回滾操作（自動生成）
# python manage.py migrate studies 000X_previous_migration

# 手動回滾 SQL（如需要）
DROP TABLE IF EXISTS study_project_assignments CASCADE;
DROP TABLE IF EXISTS project_members CASCADE;
DROP TABLE IF EXISTS projects CASCADE;
```

---

## 🔍 查詢優化範例

### 查詢 1：列出使用者的活躍專案

```python
# 不佳的查詢（N+1 問題）
projects = Project.objects.filter(
    project_members__user=user,
    status='active'
)
for project in projects:
    print(project.created_by.username)  # N+1 查詢
```

```python
# 優化後的查詢
projects = Project.objects.filter(
    project_members__user=user,
    status='active'
).select_related('created_by').prefetch_related('project_members__user')

# 使用索引：idx_pm_user, idx_projects_status_updated
# 查詢次數：2-3 次（不論專案數量）
```

### 查詢 2：取得專案及其成員

```python
# 優化查詢
project = Project.objects.select_related('created_by').prefetch_related(
    models.Prefetch(
        'project_members',
        queryset=ProjectMember.objects.select_related('user').order_by('role')
    )
).get(id=project_id)

# 使用索引：pk_projects_id, idx_pm_project
# 查詢次數：2 次（固定）
```

### 查詢 3：列出專案的研究（分頁）

```python
# 優化查詢
assignments = StudyProjectAssignment.objects.filter(
    project_id=project_id
).select_related('study', 'assigned_by').order_by('-assigned_at')[offset:offset+limit]

# 使用索引：idx_spa_proj_assigned
# 查詢次數：1 次
```

---

## 📊 資料完整性檢查

### 檢查腳本

```python
# scripts/check_project_data_integrity.py

from django.db import connection
from studies.models import Project, ProjectMember, StudyProjectAssignment

def check_study_count_integrity():
    """檢查 study_count 是否與實際分配數量一致"""
    
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT p.id, p.name, p.study_count, COUNT(spa.id) as actual_count
            FROM projects p
            LEFT JOIN study_project_assignments spa ON spa.project_id = p.id
            GROUP BY p.id, p.name, p.study_count
            HAVING p.study_count != COUNT(spa.id)
        """)
        
        inconsistent_projects = cursor.fetchall()
        
        if inconsistent_projects:
            print(f"發現 {len(inconsistent_projects)} 個專案的 study_count 不一致：")
            for project_id, name, recorded, actual in inconsistent_projects:
                print(f"  - {name}: 記錄={recorded}, 實際={actual}")
        else:
            print("✅ 所有專案的 study_count 一致")

def check_orphaned_members():
    """檢查是否有孤立的成員記錄（專案已刪除但成員未刪除）"""
    
    orphaned_count = ProjectMember.objects.filter(
        project__isnull=True
    ).count()
    
    if orphaned_count > 0:
        print(f"⚠️ 發現 {orphaned_count} 筆孤立的成員記錄")
    else:
        print("✅ 無孤立的成員記錄")

def check_owner_exists():
    """檢查每個專案是否至少有一個 Owner"""
    
    projects_without_owner = Project.objects.exclude(
        project_members__role='owner'
    ).count()
    
    if projects_without_owner > 0:
        print(f"❌ 發現 {projects_without_owner} 個專案沒有 Owner")
    else:
        print("✅ 所有專案都有 Owner")

# 執行檢查
if __name__ == '__main__':
    print("=== 開始資料完整性檢查 ===\n")
    check_study_count_integrity()
    check_orphaned_members()
    check_owner_exists()
    print("\n=== 檢查完成 ===")
```

---

## 🔒 安全性考量

### SQL 注入防護

**✅ 正確做法**（使用 ORM）：
```python
Project.objects.filter(name__icontains=user_input)
```

**❌ 錯誤做法**（原始 SQL）：
```python
# 危險！不要這樣做
cursor.execute(f"SELECT * FROM projects WHERE name LIKE '%{user_input}%'")
```

### 權限檢查

```python
def check_project_permission(user, project, required_permission):
    """檢查使用者是否有特定權限"""
    
    permissions = project.get_user_permissions(user)
    return required_permission in permissions

# 使用範例
if not check_project_permission(request.user, project, 'edit'):
    raise PermissionDenied("您沒有編輯此專案的權限")
```

---

## 📝 總結

### 設計要點

1. **三個核心表格**：projects, project_members, study_project_assignments
2. **UUID 主鍵**：安全性考量，避免可預測的 ID
3. **Denormalized study_count**：效能優化，減少 COUNT 查詢
4. **完整索引策略**：覆蓋所有常見查詢模式
5. **外鍵約束**：確保資料完整性（CASCADE DELETE）

### 效能預估

- 列出專案（100 項）：< 100ms
- 查詢專案詳情：< 50ms
- 批量新增研究（100 筆）：< 500ms
- 搜尋專案（全文搜尋）：< 200ms

### 下一步

- ✅ 資料模型設計完成
- ⏭️ 接續：API 端點設計文件
- ⏭️ 接續：權限系統設計文件
- ⏭️ 接續：實作計畫文件

---

**文件狀態**：✅ 設計完成  
**審查狀態**：待審查  
**實作狀態**：等待 pagination 分支合併