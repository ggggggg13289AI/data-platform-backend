"""
Import API Endpoints.

Provides REST endpoints for:
- File upload
- Preview with column detection
- Import execution
- Task status and listing
"""

import logging
from uuid import UUID

from django.http import HttpRequest
from ninja import File, Query, Router
from ninja.errors import HttpError
from ninja.files import UploadedFile

from .models import ImportTask
from .schemas import (
    ColumnInfo,
    ErrorDetail,
    ErrorResponse,
    ExecuteData,
    ExecuteRequest,
    ExecuteResponse,
    PreviewData,
    PreviewRequest,
    PreviewResponse,
    TaskListData,
    TaskListItem,
    TaskListResponse,
    TaskStatusData,
    TaskStatusResponse,
    UploadResponse,
    UploadTaskData,
)
from .services import (
    create_import_task,
    execute_import,
    get_preview,
    save_uploaded_file,
    validate_column_mapping,
    validate_file,
)

logger = logging.getLogger(__name__)

# Create router
imports_router = Router(tags=["imports"])


@imports_router.post(
    "/upload", response={200: UploadResponse, 400: ErrorResponse, 413: ErrorResponse}
)
def upload_file(request: HttpRequest, file: UploadedFile = File(...)):
    """
    Upload a CSV or Excel file for import.

    Accepts multipart/form-data with a 'file' field.
    Returns task ID for subsequent operations.
    """
    filename = file.name or "unknown"

    # Validate file
    is_valid, error_msg = validate_file(file, filename)
    if not is_valid:
        if "size exceeds" in error_msg:
            raise HttpError(413, error_msg)
        raise HttpError(400, error_msg)

    try:
        # Save file
        file_path = save_uploaded_file(file, filename)

        # Create task
        user = request.user if request.user.is_authenticated else None
        task = create_import_task(user, filename, file_path)

        return UploadResponse(
            code=200,
            message="File uploaded successfully",
            data=UploadTaskData(
                task_id=str(task.task_id),
                filename=filename,
                status=task.status,
                progress=0,
                message="File uploaded. Call /preview to see columns.",
            ),
        )
    except Exception as e:
        logger.exception("File upload failed")
        raise HttpError(500, f"Upload failed: {str(e)}") from e


@imports_router.post(
    "/preview", response={200: PreviewResponse, 400: ErrorResponse, 404: ErrorResponse}
)
def preview_file(request: HttpRequest, payload: PreviewRequest):
    """
    Preview uploaded file headers and sample data.

    Returns column information with type detection and mapping suggestions.
    """
    try:
        task_id = UUID(payload.task_id)
    except ValueError:
        raise HttpError(400, "Invalid task_id format") from None

    try:
        task = ImportTask.objects.get(task_id=task_id)
    except ImportTask.DoesNotExist:
        raise HttpError(404, "Import task not found") from None

    try:
        preview_data = get_preview(task, payload.sheet_name)

        return PreviewResponse(
            code=200,
            message="Preview generated successfully",
            data=PreviewData(
                columns=[ColumnInfo(**col) for col in preview_data["columns"]],
                preview_rows=preview_data["preview_rows"],
                total_rows=preview_data["total_rows"],
                sheet_names=preview_data.get("sheet_names"),
                target_fields=preview_data["target_fields"],
            ),
        )
    except FileNotFoundError:
        raise HttpError(404, "Uploaded file not found. It may have expired.") from None
    except Exception as e:
        logger.exception("Preview generation failed")
        raise HttpError(400, f"Preview failed: {str(e)}") from e


@imports_router.post(
    "/execute", response={200: ExecuteResponse, 400: ErrorResponse, 404: ErrorResponse}
)
def execute_import_endpoint(request: HttpRequest, payload: ExecuteRequest):
    """
    Execute import with column mapping.

    Starts the import process. For large files, returns immediately
    and processes in background. Poll /tasks/{task_id} for progress.
    """
    logger.info(f"[IMPORT API] Execute endpoint called with task_id: {payload.task_id}")
    logger.info(f"[IMPORT API] Target type: {payload.target_type}")
    logger.info(f"[IMPORT API] Column mapping count: {len(payload.column_mapping)}")

    try:
        task_id = UUID(payload.task_id)
    except ValueError:
        logger.error(f"[IMPORT API] Invalid task_id format: {payload.task_id}")
        raise HttpError(400, "Invalid task_id format") from None

    try:
        task = ImportTask.objects.get(task_id=task_id)
    except ImportTask.DoesNotExist:
        logger.error(f"[IMPORT API] Task not found: {task_id}")
        raise HttpError(404, "Import task not found") from None

    logger.info(f"[IMPORT API] Found task: status={task.status}, total_rows={task.total_rows}")

    # Check task status
    if task.status not in [ImportTask.Status.PENDING]:
        logger.warning(f"[IMPORT API] Task status not PENDING: {task.status}")
        raise HttpError(400, f"Task cannot be executed. Current status: {task.status}")

    # Validate column mapping
    mapping_list = [m.dict() for m in payload.column_mapping]
    is_valid, error_msg = validate_column_mapping(payload.target_type, mapping_list)
    if not is_valid:
        logger.error(f"[IMPORT API] Column mapping validation failed: {error_msg}")
        raise HttpError(400, error_msg)

    logger.info("[IMPORT API] Column mapping validated, starting import...")

    try:
        # Start import
        execute_import(task, payload.target_type, mapping_list)

        # Refresh task
        task.refresh_from_db()

        logger.info(
            f"[IMPORT API] Import started/completed. Status: {task.status}, Progress: {task.progress}"
        )

        return ExecuteResponse(
            code=200,
            message="Import started"
            if task.status == ImportTask.Status.PROCESSING
            else "Import completed",
            data=ExecuteData(
                task_id=str(task.task_id),
                status=task.status,
                progress=task.progress,
                total_rows=task.total_rows,
                message="Processing..."
                if task.status == ImportTask.Status.PROCESSING
                else "Import completed",
            ),
        )
    except Exception as e:
        logger.exception("[IMPORT API] Import execution failed")
        raise HttpError(500, f"Import failed: {str(e)}") from e


@imports_router.get("/tasks/{task_id}", response={200: TaskStatusResponse, 404: ErrorResponse})
def get_task_status(request: HttpRequest, task_id: str):
    """
    Get import task status and progress.

    Poll this endpoint to track progress of large imports.
    """
    try:
        task_uuid = UUID(task_id)
    except ValueError:
        raise HttpError(400, "Invalid task_id format") from None

    try:
        task = ImportTask.objects.get(task_id=task_uuid)
    except ImportTask.DoesNotExist:
        raise HttpError(404, "Import task not found") from None

    # Build error details if present
    error_details = None
    if task.error_details:
        error_details = [ErrorDetail(**e) for e in task.error_details]

    return TaskStatusResponse(
        code=200,
        message="Success",
        data=TaskStatusData(
            task_id=str(task.task_id),
            filename=task.filename,
            target_type=task.target_type,
            status=task.status,
            progress=task.progress,
            total_rows=task.total_rows,
            imported_rows=task.imported_rows,
            error_rows=task.error_rows,
            error_message=task.error_message,
            error_details=error_details,
            created_at=task.created_at,
            updated_at=task.updated_at,
        ),
    )


@imports_router.get("/tasks", response={200: TaskListResponse})
def list_tasks(
    request: HttpRequest,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """
    List import tasks for the current user.

    Returns paginated list of tasks ordered by creation date (newest first).
    """
    # Build queryset
    queryset = ImportTask.objects.all()

    # Filter by user if authenticated
    if request.user.is_authenticated:
        queryset = queryset.filter(user=request.user)
    else:
        # For anonymous users, show only recent tasks (last 24 hours)
        from datetime import timedelta

        from django.utils import timezone

        cutoff = timezone.now() - timedelta(hours=24)
        queryset = queryset.filter(created_at__gte=cutoff, user__isnull=True)

    # Get total count
    total = queryset.count()

    # Paginate
    offset = (page - 1) * page_size
    tasks = queryset[offset : offset + page_size]

    # Build response
    task_items = [
        TaskListItem(
            task_id=str(t.task_id),
            filename=t.filename,
            target_type=t.target_type,
            status=t.status,
            progress=t.progress,
            imported_rows=t.imported_rows,
            error_rows=t.error_rows,
            created_at=t.created_at,
        )
        for t in tasks
    ]

    return TaskListResponse(
        code=200,
        message="Success",
        data=TaskListData(
            tasks=task_items,
            total=total,
            page=page,
            page_size=page_size,
        ),
    )
