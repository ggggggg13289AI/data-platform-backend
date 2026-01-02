"""
Add imaging_findings and impression fields to Django model state.

These fields were created as PostgreSQL GENERATED COLUMNS in migration 0005.
This migration only updates Django's internal model state to recognize the fields,
WITHOUT actually creating them in the database (they already exist).

This allows Django ORM to filter on these fields while PostgreSQL manages their values.
"""
from django.db import migrations, models


class Migration(migrations.Migration):
    """
    State-only migration: Update Django model state without database changes.

    The SeparateDatabaseAndState operation is used because:
    - state_operations: Tells Django these fields now exist in the model
    - database_operations: Empty list = no actual database changes

    This is necessary because:
    1. Migration 0005 created the columns as PostgreSQL GENERATED COLUMNS via raw SQL
    2. Django doesn't know about these columns (FieldError when filtering)
    3. We need Django to recognize them for ORM operations
    4. But we must NOT try to ALTER TABLE again (columns already exist)
    """

    dependencies = [
        ('report', '0006_add_gin_trigram_indexes'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AddField(
                    model_name='report',
                    name='imaging_findings',
                    field=models.TextField(
                        blank=True,
                        editable=False,
                        help_text='影像發現區塊，由 PostgreSQL GENERATED COLUMN 自動從 content_raw 解析',
                        null=True,
                    ),
                ),
                migrations.AddField(
                    model_name='report',
                    name='impression',
                    field=models.TextField(
                        blank=True,
                        editable=False,
                        help_text='診斷意見區塊，由 PostgreSQL GENERATED COLUMN 自動從 content_raw 解析',
                        null=True,
                    ),
                ),
            ],
            database_operations=[
                # No database operations - columns already exist from migration 0005
            ],
        ),
    ]
