"""
Import Task Model - Tracks data import jobs and their progress.

This model provides:
- Task status tracking (pending, processing, completed, failed)
- Progress monitoring for large file imports
- Column mapping configuration storage
- Error collection for partial imports
"""

import uuid

from django.conf import settings
from django.db import models


class ImportTask(models.Model):
    """
    Import task tracking model.

    Stores the state and progress of a data import operation,
    supporting both synchronous and asynchronous processing.

    Attributes:
        task_id: Unique identifier for the import task
        user: User who initiated the import (optional for anonymous imports)
        filename: Original uploaded filename
        target_type: Type of data being imported ('report' or 'study')
        status: Current task status
        progress: Progress percentage (0-100)
        total_rows: Total number of rows in the file
        imported_rows: Number of successfully imported rows
        error_rows: Number of rows that failed to import
        column_mapping: JSON configuration for column-to-field mapping
        error_details: JSON array of error information for failed rows
        file_path: Path to temporary uploaded file
        created_at: Task creation timestamp
        updated_at: Last update timestamp
    """

    class TargetType(models.TextChoices):
        """Target data type for import."""

        REPORT = "report", "Report"
        STUDY = "study", "Study"

    class Status(models.TextChoices):
        """Import task status."""

        PENDING = "pending", "Pending"
        PROCESSING = "processing", "Processing"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"
        EXPIRED = "expired", "Expired"

    # Primary key
    task_id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text="Unique identifier for the import task",
    )

    # User reference (nullable for system imports)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="import_tasks",
        help_text="User who initiated the import",
    )

    # File information
    filename = models.CharField(max_length=255, help_text="Original uploaded filename")
    file_path = models.CharField(max_length=500, help_text="Path to temporary uploaded file")

    # Target configuration
    target_type = models.CharField(
        max_length=20,
        choices=TargetType.choices,
        default=TargetType.REPORT,
        help_text="Type of data being imported",
    )

    # Status and progress
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
        help_text="Current task status",
    )
    progress = models.IntegerField(default=0, help_text="Progress percentage (0-100)")

    # Row statistics
    total_rows = models.IntegerField(default=0, help_text="Total number of rows in the file")
    imported_rows = models.IntegerField(default=0, help_text="Number of successfully imported rows")
    error_rows = models.IntegerField(default=0, help_text="Number of rows that failed to import")

    # Configuration and errors
    column_mapping = models.JSONField(
        null=True, blank=True, help_text="JSON configuration for column-to-field mapping"
    )
    error_details = models.JSONField(
        null=True, blank=True, help_text="JSON array of error information for failed rows"
    )
    error_message = models.TextField(
        null=True, blank=True, help_text="General error message if task failed"
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, help_text="Task creation timestamp")
    updated_at = models.DateTimeField(auto_now=True, help_text="Last update timestamp")

    class Meta:
        db_table = "import_tasks"
        ordering = ["-created_at"]
        verbose_name = "Import Task"
        verbose_name_plural = "Import Tasks"
        indexes = [
            models.Index(fields=["user", "-created_at"], name="idx_import_user_created"),
            models.Index(fields=["status", "-created_at"], name="idx_import_status_created"),
        ]

    def __str__(self):
        return f"ImportTask({self.task_id}, {self.filename}, {self.status})"

    def update_progress(self, imported: int, errors: int, total: int):
        """Update task progress statistics."""
        self.imported_rows = imported
        self.error_rows = errors
        self.total_rows = total
        if total > 0:
            self.progress = int((imported + errors) / total * 100)
        self.save(
            update_fields=["imported_rows", "error_rows", "total_rows", "progress", "updated_at"]
        )

    def mark_completed(self):
        """Mark task as completed."""
        self.status = self.Status.COMPLETED
        self.progress = 100
        self.save(update_fields=["status", "progress", "updated_at"])

    def mark_failed(self, error_message: str):
        """Mark task as failed with error message."""
        self.status = self.Status.FAILED
        self.error_message = error_message
        self.save(update_fields=["status", "error_message", "updated_at"])
