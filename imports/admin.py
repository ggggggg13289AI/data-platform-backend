"""Django admin configuration for imports module."""

from django.contrib import admin

from .models import ImportTask


@admin.register(ImportTask)
class ImportTaskAdmin(admin.ModelAdmin):
    """Admin interface for ImportTask model."""

    list_display = [
        "task_id",
        "filename",
        "target_type",
        "status",
        "progress",
        "imported_rows",
        "error_rows",
        "created_at",
    ]
    list_filter = ["status", "target_type", "created_at"]
    search_fields = ["filename", "task_id"]
    readonly_fields = [
        "task_id",
        "created_at",
        "updated_at",
        "progress",
        "imported_rows",
        "error_rows",
        "total_rows",
    ]
    ordering = ["-created_at"]

    fieldsets = [
        (
            "Task Information",
            {"fields": ["task_id", "user", "filename", "file_path", "target_type"]},
        ),
        ("Status", {"fields": ["status", "progress", "error_message"]}),
        ("Statistics", {"fields": ["total_rows", "imported_rows", "error_rows"]}),
        ("Configuration", {"fields": ["column_mapping", "error_details"], "classes": ["collapse"]}),
        ("Timestamps", {"fields": ["created_at", "updated_at"]}),
    ]
