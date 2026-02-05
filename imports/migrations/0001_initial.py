# Generated manually for imports module

import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="ImportTask",
            fields=[
                (
                    "task_id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        help_text="Unique identifier for the import task",
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "filename",
                    models.CharField(help_text="Original uploaded filename", max_length=255),
                ),
                (
                    "file_path",
                    models.CharField(help_text="Path to temporary uploaded file", max_length=500),
                ),
                (
                    "target_type",
                    models.CharField(
                        choices=[("report", "Report"), ("study", "Study")],
                        default="report",
                        help_text="Type of data being imported",
                        max_length=20,
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "Pending"),
                            ("processing", "Processing"),
                            ("completed", "Completed"),
                            ("failed", "Failed"),
                            ("expired", "Expired"),
                        ],
                        db_index=True,
                        default="pending",
                        help_text="Current task status",
                        max_length=20,
                    ),
                ),
                (
                    "progress",
                    models.IntegerField(default=0, help_text="Progress percentage (0-100)"),
                ),
                (
                    "total_rows",
                    models.IntegerField(default=0, help_text="Total number of rows in the file"),
                ),
                (
                    "imported_rows",
                    models.IntegerField(
                        default=0, help_text="Number of successfully imported rows"
                    ),
                ),
                (
                    "error_rows",
                    models.IntegerField(
                        default=0, help_text="Number of rows that failed to import"
                    ),
                ),
                (
                    "column_mapping",
                    models.JSONField(
                        blank=True,
                        help_text="JSON configuration for column-to-field mapping",
                        null=True,
                    ),
                ),
                (
                    "error_details",
                    models.JSONField(
                        blank=True,
                        help_text="JSON array of error information for failed rows",
                        null=True,
                    ),
                ),
                (
                    "error_message",
                    models.TextField(
                        blank=True, help_text="General error message if task failed", null=True
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True, help_text="Task creation timestamp"),
                ),
                (
                    "updated_at",
                    models.DateTimeField(auto_now=True, help_text="Last update timestamp"),
                ),
                (
                    "user",
                    models.ForeignKey(
                        blank=True,
                        help_text="User who initiated the import",
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="import_tasks",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Import Task",
                "verbose_name_plural": "Import Tasks",
                "db_table": "import_tasks",
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="importtask",
            index=models.Index(fields=["user", "-created_at"], name="idx_import_user_created"),
        ),
        migrations.AddIndex(
            model_name="importtask",
            index=models.Index(fields=["status", "-created_at"], name="idx_import_status_created"),
        ),
    ]
