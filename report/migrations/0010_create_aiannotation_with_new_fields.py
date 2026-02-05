# Generated manually for AI workflow feature
# Adds new fields to AIAnnotation for batch analysis and review workflow
# Uses conditional operations to handle partial database state

import uuid
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def column_exists(connection, table_name, column_name):
    """Check if a column exists in a table."""
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.columns
                WHERE table_schema = 'public'
                AND table_name = %s
                AND column_name = %s
            )
        """, [table_name, column_name])
        return cursor.fetchone()[0]


def index_exists(connection, index_name):
    """Check if an index exists in the database."""
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM pg_indexes
                WHERE indexname = %s
            )
        """, [index_name])
        return cursor.fetchone()[0]


class ConditionalAddField(migrations.AddField):
    """AddField that skips if column already exists."""

    def database_forwards(self, app_label, schema_editor, from_state, to_state):
        model = to_state.apps.get_model(app_label, self.model_name)
        table_name = model._meta.db_table
        if column_exists(schema_editor.connection, table_name, self.name):
            return
        super().database_forwards(app_label, schema_editor, from_state, to_state)


class ConditionalAddIndex(migrations.AddIndex):
    """AddIndex that skips if index already exists."""

    def database_forwards(self, app_label, schema_editor, from_state, to_state):
        if index_exists(schema_editor.connection, self.index.name):
            return
        super().database_forwards(app_label, schema_editor, from_state, to_state)


class Migration(migrations.Migration):

    dependencies = [
        ('ai', '0001_initial'),
        ('report', '0009_rename_report_ai_a_report__b98221_idx_idx_report_annotation_type_and_more'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # Add new fields to AIAnnotation model
        ConditionalAddField(
            model_name='aiannotation',
            name='batch_task',
            field=models.ForeignKey(
                blank=True,
                help_text='關聯的批次分析任務',
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='annotations',
                to='ai.batchanalysistask'
            ),
        ),
        ConditionalAddField(
            model_name='aiannotation',
            name='confidence_score',
            field=models.FloatField(
                blank=True,
                help_text='AI 分類的信心度分數 (0.0-1.0)',
                null=True
            ),
        ),
        ConditionalAddField(
            model_name='aiannotation',
            name='deprecated_at',
            field=models.DateTimeField(
                blank=True,
                help_text='廢棄時間戳',
                null=True
            ),
        ),
        ConditionalAddField(
            model_name='aiannotation',
            name='deprecated_reason',
            field=models.CharField(
                blank=True,
                default='',
                help_text="廢棄原因說明，如 'Re-analyzed with guideline v2'",
                max_length=255
            ),
        ),
        ConditionalAddField(
            model_name='aiannotation',
            name='guideline',
            field=models.ForeignKey(
                blank=True,
                help_text='關聯的分類指南，用於批次分析',
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='annotations',
                to='ai.classificationguideline'
            ),
        ),
        ConditionalAddField(
            model_name='aiannotation',
            name='guideline_version',
            field=models.IntegerField(
                blank=True,
                help_text='建立時的指南版本號，用於追蹤版本',
                null=True
            ),
        ),
        ConditionalAddField(
            model_name='aiannotation',
            name='is_deprecated',
            field=models.BooleanField(
                db_index=True,
                default=False,
                help_text='是否已廢棄，重新分析後舊結果會被標記為廢棄'
            ),
        ),
        # Add new indexes
        ConditionalAddIndex(
            model_name='aiannotation',
            index=models.Index(
                fields=['guideline', '-created_at'],
                name='idx_annotation_guideline'
            ),
        ),
        ConditionalAddIndex(
            model_name='aiannotation',
            index=models.Index(
                fields=['is_deprecated', '-created_at'],
                name='idx_annotation_deprecated'
            ),
        ),
        ConditionalAddIndex(
            model_name='aiannotation',
            index=models.Index(
                fields=['batch_task'],
                name='idx_annotation_batch_task'
            ),
        ),
    ]
