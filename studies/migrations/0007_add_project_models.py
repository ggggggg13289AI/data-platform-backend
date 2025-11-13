# Generated manually based on Projects specification

import uuid

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('studies', '0006_remove_llmanalysisresult_study_and_more'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Project',
            fields=[
                (
                    'id',
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    'name',
                    models.CharField(
                        db_index=True,
                        max_length=200,
                        verbose_name='專案名稱',
                    ),
                ),
                (
                    'description',
                    models.TextField(
                        blank=True,
                        verbose_name='專案描述',
                    ),
                ),
                (
                    'status',
                    models.CharField(
                        choices=[
                            ('active', '進行中'),
                            ('archived', '已封存'),
                            ('completed', '已完成'),
                            ('draft', '草稿'),
                        ],
                        db_index=True,
                        default='active',
                        max_length=20,
                        verbose_name='狀態',
                    ),
                ),
                (
                    'tags',
                    models.JSONField(
                        default=list,
                        verbose_name='標籤',
                    ),
                ),
                (
                    'study_count',
                    models.IntegerField(
                        default=0,
                        verbose_name='研究數量',
                    ),
                ),
                (
                    'created_at',
                    models.DateTimeField(
                        auto_now_add=True,
                        verbose_name='建立時間',
                    ),
                ),
                (
                    'updated_at',
                    models.DateTimeField(
                        auto_now=True,
                        verbose_name='更新時間',
                    ),
                ),
                (
                    'settings',
                    models.JSONField(
                        default=dict,
                        verbose_name='設定',
                    ),
                ),
                (
                    'metadata',
                    models.JSONField(
                        default=dict,
                        verbose_name='元數據',
                    ),
                ),
                (
                    'created_by',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.RESTRICT,
                        related_name='created_projects',
                        to=settings.AUTH_USER_MODEL,
                        verbose_name='建立者',
                    ),
                ),
            ],
            options={
                'db_table': 'projects',
                'ordering': ['-updated_at'],
                'verbose_name': '專案',
                'verbose_name_plural': '專案',
                'indexes': [
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
                ],
            },
        ),
        migrations.CreateModel(
            name='ProjectMember',
            fields=[
                (
                    'id',
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    'role',
                    models.CharField(
                        choices=[
                            ('owner', '擁有者'),
                            ('admin', '管理員'),
                            ('editor', '編輯者'),
                            ('viewer', '檢視者'),
                        ],
                        default='viewer',
                        max_length=20,
                        verbose_name='角色',
                    ),
                ),
                (
                    'joined_at',
                    models.DateTimeField(
                        auto_now_add=True,
                        verbose_name='加入時間',
                    ),
                ),
                (
                    'permissions',
                    models.JSONField(
                        default=list,
                        verbose_name='自訂權限',
                    ),
                ),
                (
                    'project',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='project_members',
                        to='studies.project',
                        verbose_name='專案',
                    ),
                ),
                (
                    'user',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='project_memberships',
                        to=settings.AUTH_USER_MODEL,
                        verbose_name='使用者',
                    ),
                ),
            ],
            options={
                'db_table': 'project_members',
                'ordering': ['project', '-joined_at'],
                'verbose_name': '專案成員',
                'verbose_name_plural': '專案成員',
                'unique_together': {('project', 'user')},
                'indexes': [
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
                ],
            },
        ),
        migrations.CreateModel(
            name='StudyProjectAssignment',
            fields=[
                (
                    'id',
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    'assigned_at',
                    models.DateTimeField(
                        auto_now_add=True,
                        verbose_name='分配時間',
                    ),
                ),
                (
                    'metadata',
                    models.JSONField(
                        default=dict,
                        verbose_name='元數據',
                    ),
                ),
                (
                    'assigned_by',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.RESTRICT,
                        related_name='study_assignments',
                        to=settings.AUTH_USER_MODEL,
                        verbose_name='分配者',
                    ),
                ),
                (
                    'project',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='study_assignments',
                        to='studies.project',
                        verbose_name='專案',
                    ),
                ),
                (
                    'study',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='project_assignments',
                        to='studies.study',
                        to_field='exam_id',
                        verbose_name='研究',
                    ),
                ),
            ],
            options={
                'db_table': 'study_project_assignments',
                'ordering': ['project', '-assigned_at'],
                'verbose_name': '研究分配',
                'verbose_name_plural': '研究分配',
                'unique_together': {('project', 'study')},
                'indexes': [
                    models.Index(
                        fields=['project', '-assigned_at'],
                        name='idx_spa_proj_assigned',
                    ),
                    models.Index(
                        fields=['study', 'project'],
                        name='idx_spa_study_proj',
                    ),
                    models.Index(
                        fields=['assigned_by'],
                        name='idx_spa_assigned_by',
                    ),
                ],
            },
        ),
        migrations.AddField(
            model_name='project',
            name='members',
            field=models.ManyToManyField(
                related_name='projects',
                through='studies.ProjectMember',
                to=settings.AUTH_USER_MODEL,
                verbose_name='成員',
            ),
        ),
    ]
