"""
Project permissions and decorators.

Implements a role-based access control system for Projects with four roles:
- owner
- admin
- editor
- viewer
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from functools import wraps
from typing import TypeVar

from django.core.exceptions import PermissionDenied
from django.core.handlers.wsgi import WSGIRequest
from django.http import Http404

from project.models import Project, ProjectMember

F = TypeVar('F', bound=Callable[..., object])
logger = logging.getLogger(__name__)

class ProjectPermissions:
    """專案權限檢查類別"""

    PERMISSION_VIEW = 'view'
    PERMISSION_EDIT = 'edit'
    PERMISSION_DELETE = 'delete'
    PERMISSION_MANAGE_MEMBERS = 'manage_members'
    PERMISSION_MANAGE_STUDIES = 'manage_studies'

    ROLE_OWNER = 'owner'
    ROLE_ADMIN = 'admin'
    ROLE_EDITOR = 'editor'
    ROLE_VIEWER = 'viewer'

    ROLE_PERMISSIONS = {
        ROLE_OWNER: [
            PERMISSION_VIEW,
            PERMISSION_EDIT,
            PERMISSION_DELETE,
            PERMISSION_MANAGE_MEMBERS,
            PERMISSION_MANAGE_STUDIES,
        ],
        ROLE_ADMIN: [
            PERMISSION_VIEW,
            PERMISSION_EDIT,
            PERMISSION_MANAGE_MEMBERS,
            PERMISSION_MANAGE_STUDIES,
        ],
        ROLE_EDITOR: [
            PERMISSION_VIEW,
            PERMISSION_EDIT,
            PERMISSION_MANAGE_STUDIES,
        ],
        ROLE_VIEWER: [
            PERMISSION_VIEW,
        ],
    }

    @classmethod
    def get_user_role(cls, project: Project, user) -> str | None:
        """取得使用者在專案中的角色"""
        if user is None or not getattr(user, 'is_authenticated', False):
            return None

        try:
            member = ProjectMember.objects.get(project=project, user=user)
            role: str | None = member.role if hasattr(member, 'role') else None
            return role
        except ProjectMember.DoesNotExist:
            return None

    @classmethod
    def get_user_permissions(cls, project: Project, user) -> list[str]:
        """取得使用者的權限列表"""
        role = cls.get_user_role(project, user)
        if not role:
            return []
        return cls.ROLE_PERMISSIONS.get(role, [])

    @classmethod
    def get_permission_flags(cls, project: Project, user) -> dict[str, bool]:
        """取得布林化的權限旗標，便於前端 gating"""
        permissions = cls.get_user_permissions(project, user)
        return {
            'can_manage_members': cls.PERMISSION_MANAGE_MEMBERS in permissions,
            'can_assign_studies': cls.PERMISSION_MANAGE_STUDIES in permissions,
            'can_archive': cls.PERMISSION_EDIT in permissions,
        }

    @classmethod
    def check_permission(cls, project: Project, user, permission: str) -> bool:
        """檢查使用者是否擁有特定權限"""
        return permission in cls.get_user_permissions(project, user)

    @classmethod
    def require_permission(cls, permission: str) -> Callable[[F], F]:
        """權限檢查裝飾器"""

        def decorator(func: F) -> F:
            @wraps(func)
            def wrapper(request:WSGIRequest, project_id: str, *args, **kwargs):
                try:
                    project = Project.objects.select_related('created_by').get(id=project_id)
                except Project.DoesNotExist as exc:
                    raise Http404('專案不存在') from exc

                if not cls.check_permission(project, request.user, permission):
                    raise PermissionDenied(f"您沒有 '{permission}' 權限")

                kwargs['project'] = project
                return func(request, project_id, *args, **kwargs)

            return wrapper  # type: ignore[return-value]

        return decorator

    @classmethod
    def can_manage_member(cls, project: Project, operator, target_user) -> bool:
        """檢查是否可管理特定成員"""
        operator_role = cls.get_user_role(project, operator)
        target_role = cls.get_user_role(project, target_user)

        if target_role == cls.ROLE_OWNER:
            return False

        if operator_role not in {cls.ROLE_OWNER, cls.ROLE_ADMIN}:
            return False

        if operator_role == cls.ROLE_ADMIN and target_role == cls.ROLE_ADMIN:
            return False

        return True


# 便捷裝飾器
require_view = ProjectPermissions.require_permission(ProjectPermissions.PERMISSION_VIEW)
require_edit = ProjectPermissions.require_permission(ProjectPermissions.PERMISSION_EDIT)
require_delete = ProjectPermissions.require_permission(ProjectPermissions.PERMISSION_DELETE)
require_manage_members = ProjectPermissions.require_permission(ProjectPermissions.PERMISSION_MANAGE_MEMBERS)
require_manage_studies = ProjectPermissions.require_permission(ProjectPermissions.PERMISSION_MANAGE_STUDIES)
