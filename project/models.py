"""
Project Models - Project management.
"""

import uuid

from django.conf import settings
from django.db import models


class Project(models.Model):
    """專案模型"""

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

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name='專案ID',
    )
    name = models.CharField(
        max_length=200,
        verbose_name='專案名稱',
        db_index=True,
    )
    description = models.TextField(
        blank=True,
        verbose_name='專案描述',
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_ACTIVE,
        verbose_name='狀態',
        db_index=True,
    )
    tags = models.JSONField(
        default=list,
        verbose_name='標籤',
    )
    study_count = models.IntegerField(
        default=0,
        verbose_name='研究數量',
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.RESTRICT,
        related_name='created_projects',
        verbose_name='建立者',
    )
    members = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        through='ProjectMember',
        related_name='projects',
        verbose_name='成員',
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='建立時間',
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='更新時間',
    )
    settings = models.JSONField(
        default=dict,
        verbose_name='設定',
    )
    metadata = models.JSONField(
        default=dict,
        verbose_name='元數據',
    )

    class Meta:
        db_table = 'projects'
        verbose_name = '專案'
        verbose_name_plural = '專案'
        ordering = ['-updated_at']
        indexes = [
            models.Index(
                fields=['status', '-updated_at'],
                name='idx_proj_status_updated',
            ),
            models.Index(
                fields=['created_by', '-created_at'],
                name='idx_proj_creator_created',
            ),
            models.Index(
                fields=['-study_count'],
                name='idx_proj_study_count',
            ),
        ]

    def __str__(self) -> str:
        return f'{self.name} ({self.get_status_display()})'

    def to_dict(self) -> dict:
        """轉換為字典格式（API 序列化）"""
        return {
            'id': str(self.id),
            'name': self.name,
            'description': self.description,
            'status': self.status,
            'tags': self.tags,
            'study_count': self.study_count,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'created_by': {
                'id': str(self.created_by.id),
                'name': self.created_by.get_full_name() or self.created_by.get_username(),
                'email': self.created_by.email,
            },
            'settings': self.settings,
            'metadata': self.metadata,
        }

    def get_user_role(self, user) -> str | None:
        """取得使用者在專案中的角色"""
        try:
            member = self.project_members.get(user=user)
            return member.role
        except ProjectMember.DoesNotExist:
            return None

    def get_user_permissions(self, user) -> list[str]:
        """取得使用者在專案中的權限列表"""
        role = self.get_user_role(user)
        if not role:
            return []

        permissions_map = {
            'owner': ['view', 'edit', 'delete', 'manage_members', 'manage_studies'],
            'admin': ['view', 'edit', 'manage_members', 'manage_studies'],
            'editor': ['view', 'edit', 'manage_studies'],
            'viewer': ['view'],
        }
        return permissions_map.get(role, [])

    def increment_study_count(self, count: int = 1) -> None:
        """增加研究計數"""
        self.study_count = models.F('study_count') + count
        self.save(update_fields=['study_count'])
        self.refresh_from_db(fields=['study_count'])

    def decrement_study_count(self, count: int = 1) -> None:
        """減少研究計數"""
        self.study_count = models.F('study_count') - count
        self.save(update_fields=['study_count'])
        self.refresh_from_db(fields=['study_count'])


class ProjectMember(models.Model):
    """專案成員模型（Through Model）"""

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

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    project = models.ForeignKey(
        'Project',
        on_delete=models.CASCADE,
        related_name='project_members',
        verbose_name='專案',
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='project_memberships',
        verbose_name='使用者',
    )
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default=ROLE_VIEWER,
        verbose_name='角色',
    )
    joined_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='加入時間',
    )
    permissions = models.JSONField(
        default=list,
        verbose_name='自訂權限',
    )

    class Meta:
        db_table = 'project_members'
        verbose_name = '專案成員'
        verbose_name_plural = '專案成員'
        unique_together = [['project', 'user']]
        ordering = ['project', '-joined_at']
        indexes = [
            models.Index(
                fields=['project'],
                name='idx_pm_project',
            ),
            models.Index(
                fields=['user'],
                name='idx_pm_user',
            ),
            models.Index(
                fields=['project', 'role'],
                name='idx_pm_proj_role',
            ),
        ]

    def __str__(self) -> str:
        return f'{self.user.get_username()} - {self.project.name} ({self.get_role_display()})'

    def to_dict(self) -> dict:
        """轉換為字典格式"""
        return {
            'user_id': str(self.user.id),
            'name': self.user.get_full_name() or self.user.get_username(),
            'email': self.user.email,
            'role': self.role,
            'joined_at': self.joined_at.isoformat() if self.joined_at else None,
            'permissions': self.permissions,
        }

