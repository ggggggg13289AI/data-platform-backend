"""
Import service - Business logic for data import operations.

Provides:
- Task creation and management
- Column mapping validation
- Import execution with progress tracking
- Report and Study import processors
"""

import logging
import uuid
from pathlib import Path
from threading import Thread
from typing import Any

from django.conf import settings
from django.db import connection

from .models import ImportTask
from .parsers import (
    get_target_fields,
    parse_file,
    read_file_rows,
    suggest_field_mapping,
)

logger = logging.getLogger(__name__)

# Constants
IMPORT_TEMP_DIR = Path(settings.BASE_DIR) / "temp" / "imports"
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
SYNC_THRESHOLD = 1000  # Rows below this processed synchronously
ALLOWED_EXTENSIONS = {".csv", ".xlsx", ".xls"}

# Required fields per target type
# These must match the actual model required fields
REQUIRED_FIELDS = {
    "report": ["uid", "title", "content", "report_type"],
    # Study model required fields: exam_id, patient_name, exam_status, exam_source, exam_item, equipment_type, order_datetime
    "study": [
        "exam_id",
        "patient_name",
    ],  # Minimal required for UI; service will set defaults for others
}


def ensure_temp_dir():
    """Ensure temp directory exists."""
    IMPORT_TEMP_DIR.mkdir(parents=True, exist_ok=True)


def save_uploaded_file(file, filename: str) -> str:
    """
    Save uploaded file to temp directory.

    Args:
        file: Django UploadedFile object
        filename: Original filename

    Returns:
        Path to saved file
    """
    ensure_temp_dir()

    # Generate unique filename
    ext = Path(filename).suffix.lower()
    unique_name = f"{uuid.uuid4()}_{filename}"
    file_path = IMPORT_TEMP_DIR / unique_name

    # Save file
    with open(file_path, "wb") as dest:
        for chunk in file.chunks():
            dest.write(chunk)

    return str(file_path)


def validate_file(file, filename: str) -> tuple[bool, str]:
    """
    Validate uploaded file.

    Args:
        file: Django UploadedFile object
        filename: Original filename

    Returns:
        Tuple of (is_valid, error_message)
    """
    ext = Path(filename).suffix.lower()

    # Check extension
    if ext not in ALLOWED_EXTENSIONS:
        return (
            False,
            f"Unsupported file type: {ext}. Only CSV and Excel (.xlsx) files are accepted.",
        )

    # Check size
    if file.size > MAX_FILE_SIZE:
        return False, f"File size exceeds {MAX_FILE_SIZE // (1024 * 1024)}MB limit."

    return True, ""


def create_import_task(user, filename: str, file_path: str) -> ImportTask:
    """
    Create a new import task.

    Args:
        user: User initiating the import
        filename: Original filename
        file_path: Path to saved file

    Returns:
        Created ImportTask instance
    """
    task = ImportTask.objects.create(
        user=user,
        filename=filename,
        file_path=file_path,
        status=ImportTask.Status.PENDING,
    )
    return task


def get_preview(task: ImportTask, sheet_name: str | None = None) -> dict[str, Any]:
    """
    Get preview data for an import task.

    Args:
        task: ImportTask instance
        sheet_name: Optional sheet name for Excel files

    Returns:
        Preview data dict
    """
    result = parse_file(task.file_path, sheet_name)

    # Add suggested fields for both report and study
    for column in result["columns"]:
        column["suggested_field"] = suggest_field_mapping(column["name"], "report")

    # Add available target fields
    result["target_fields"] = {
        "report": get_target_fields("report"),
        "study": get_target_fields("study"),
    }

    # Update task with total rows
    task.total_rows = result["total_rows"]
    task.save(update_fields=["total_rows", "updated_at"])

    return result


def validate_column_mapping(target_type: str, column_mapping: list[dict]) -> tuple[bool, str]:
    """
    Validate column mapping configuration.

    Args:
        target_type: 'report' or 'study'
        column_mapping: List of column mapping items

    Returns:
        Tuple of (is_valid, error_message)
    """
    if target_type not in REQUIRED_FIELDS:
        return False, f"Invalid target type: {target_type}"

    # Get mapped target fields
    mapped_fields = {m["target_field"] for m in column_mapping}

    # Check required fields
    required = REQUIRED_FIELDS[target_type]
    missing = [f for f in required if f not in mapped_fields]

    if missing:
        return False, f"Missing required fields: {', '.join(missing)}"

    # Validate target field names
    valid_fields = set(get_target_fields(target_type))
    invalid = [m["target_field"] for m in column_mapping if m["target_field"] not in valid_fields]

    if invalid:
        return False, f"Invalid target fields: {', '.join(invalid)}"

    return True, ""


def execute_import(task: ImportTask, target_type: str, column_mapping: list[dict]) -> None:
    """
    Execute import operation.

    Args:
        task: ImportTask instance
        target_type: 'report' or 'study'
        column_mapping: List of column mapping items
    """
    logger.info(f"[IMPORT] Starting execute_import for task {task.task_id}")
    logger.info(f"[IMPORT] Target type: {target_type}, total_rows: {task.total_rows}")
    logger.info(f"[IMPORT] Column mapping: {column_mapping}")

    # Update task
    task.target_type = target_type
    task.column_mapping = column_mapping
    task.status = ImportTask.Status.PROCESSING
    task.save()

    logger.info("[IMPORT] Task status updated to PROCESSING")

    # Decide sync vs async
    if task.total_rows < SYNC_THRESHOLD:
        logger.info(
            f"[IMPORT] Using sync processing (total_rows={task.total_rows} < threshold={SYNC_THRESHOLD})"
        )
        _process_import_sync(task)
    else:
        logger.info(
            f"[IMPORT] Using async processing (total_rows={task.total_rows} >= threshold={SYNC_THRESHOLD})"
        )
        # Start background thread
        thread = Thread(target=_process_import_async, args=(str(task.task_id),))
        thread.daemon = True
        thread.start()


def _process_import_sync(task: ImportTask) -> None:
    """Process import synchronously."""
    logger.info(f"[IMPORT] _process_import_sync starting for task {task.task_id}")
    try:
        _do_import(task)
        logger.info(f"[IMPORT] _process_import_sync completed successfully for task {task.task_id}")
    except Exception as e:
        logger.exception(f"[IMPORT] Import failed for task {task.task_id}: {e}")
        task.mark_failed(str(e))


def _process_import_async(task_id: str) -> None:
    """Process import asynchronously in background thread."""
    # Close existing connection to get fresh one for this thread
    connection.close()

    try:
        task = ImportTask.objects.get(task_id=task_id)
        _do_import(task)
    except Exception as e:
        logger.exception(f"Import failed for task {task_id}")
        try:
            task = ImportTask.objects.get(task_id=task_id)
            task.mark_failed(str(e))
        except Exception:
            pass
    finally:
        connection.close()


def _do_import(task: ImportTask) -> None:
    """
    Execute the actual import logic using bulk operations.

    Linus 原則：
    1. 資料結構優先 - 先批量轉換所有資料，再批量寫入
    2. 消除特殊情況 - 用資料結構設計取代條件分支
    3. 最簡單的實作 - bulk_create/bulk_update 是 Django 原生支援的最佳實踐

    Args:
        task: ImportTask instance
    """
    logger.info(f"[IMPORT] _do_import starting for task {task.task_id}")

    # 1. 批量讀取所有資料
    rows = read_file_rows(task.file_path)
    total_rows = len(rows)
    logger.info(f"[IMPORT] Read {total_rows} rows from file")

    if total_rows == 0:
        task.status = ImportTask.Status.COMPLETED
        task.progress = 100
        task.save()
        _cleanup_file(task.file_path)
        return

    # 2. 批量轉換：一次性將所有行轉換為模型實例
    mapping = {m["source_column"]: m for m in task.column_mapping}

    if task.target_type == "report":
        imported, errors, error_details = _bulk_import_reports(rows, mapping)
    else:
        imported, errors, error_details = _bulk_import_studies(rows, mapping)

    logger.info(f"[IMPORT] Import complete: {imported} imported, {errors} errors")

    # 3. 更新任務狀態
    task.imported_rows = imported
    task.error_rows = errors
    task.error_details = error_details if error_details else None
    task.progress = 100

    if errors == total_rows and total_rows > 0:
        task.status = ImportTask.Status.FAILED
        task.error_message = "All rows failed to import"
    else:
        task.status = ImportTask.Status.COMPLETED

    task.save()
    logger.info(f"[IMPORT] Task {task.task_id} finalized with status: {task.status}")

    # Cleanup temp file
    _cleanup_file(task.file_path)


def _bulk_import_studies(rows: list[dict], mapping: dict) -> tuple[int, int, list[dict]]:
    """
    批量匯入 Study 資料。

    Linus 原則應用：
    - 資料結構優先：先收集所有 exam_id，一次查詢現有記錄
    - 消除 N+1：使用 bulk_create 和 bulk_update
    - 簡單直接：分為「新增」和「更新」兩個批次

    Returns:
        Tuple of (imported_count, error_count, error_details)
    """
    from django.utils import timezone

    from study.models import Study

    # 取得 Study 模型的有效欄位
    valid_fields = {f.name for f in Study._meta.get_fields() if hasattr(f, "column")}
    error_details = []

    # 第一階段：批量轉換所有行為資料字典
    all_data = []
    for row_num, row in enumerate(rows, start=2):
        try:
            data = _transform_row_to_study_data(row, mapping, valid_fields)
            if data:
                all_data.append((row_num, data))
        except Exception as e:
            error_details.append(
                {
                    "row_number": row_num,
                    "error": str(e),
                    "field": None,
                }
            )

    if not all_data:
        return 0, len(error_details), error_details

    # 第二階段：一次查詢找出所有現有的 exam_id
    all_exam_ids = [d["exam_id"] for _, d in all_data]
    existing_ids = set(
        Study.objects.filter(exam_id__in=all_exam_ids).values_list("exam_id", flat=True)
    )
    logger.info(f"[IMPORT] Found {len(existing_ids)} existing studies out of {len(all_exam_ids)}")

    # 第三階段：分類為「新增」和「更新」
    to_create = []
    to_update = []
    update_fields = set()

    now = timezone.now()
    defaults = {
        "exam_status": "pending",
        "exam_source": "Unknown",
        "exam_item": "Unknown",
        "equipment_type": "Unknown",
        "order_datetime": now,
    }

    for row_num, data in all_data:
        exam_id = data.pop("exam_id")

        # 合併預設值（資料優先）
        final_data = {**defaults, **data}
        update_fields.update(final_data.keys())

        if exam_id in existing_ids:
            # 更新現有記錄
            study = Study(exam_id=exam_id, **final_data)
            to_update.append(study)
        else:
            # 新增記錄
            study = Study(exam_id=exam_id, **final_data)
            to_create.append(study)

    # 第四階段：批量執行資料庫操作
    created_count = 0
    updated_count = 0

    if to_create:
        Study.objects.bulk_create(to_create, ignore_conflicts=False)
        created_count = len(to_create)
        logger.info(f"[IMPORT] Bulk created {created_count} studies")

    if to_update:
        # bulk_update 需要指定要更新的欄位
        update_field_list = list(update_fields)
        Study.objects.bulk_update(to_update, update_field_list, batch_size=500)
        updated_count = len(to_update)
        logger.info(f"[IMPORT] Bulk updated {updated_count} studies")

    total_imported = created_count + updated_count
    return total_imported, len(error_details), error_details


def _transform_row_to_study_data(row: dict, mapping: dict, valid_fields: set) -> dict | None:
    """
    將單行資料轉換為 Study 資料字典。

    這是純粹的資料轉換，不涉及資料庫操作。

    Returns:
        資料字典，或 None 如果缺少必要欄位
    """
    data = {}

    for source_col, config in mapping.items():
        target_field = config["target_field"]

        # 跳過無效欄位
        if target_field not in valid_fields:
            continue

        value = row.get(source_col)
        if value is not None:
            # 應用轉換
            transform = config.get("transform")
            if transform == "trim" and isinstance(value, str):
                value = value.strip()
            data[target_field] = value

    # 驗證必要欄位
    if "exam_id" not in data or not data["exam_id"]:
        raise ValueError("exam_id is required")

    return data


def _bulk_import_reports(rows: list[dict], mapping: dict) -> tuple[int, int, list[dict]]:
    """
    批量匯入 Report 資料。

    Returns:
        Tuple of (imported_count, error_count, error_details)
    """

    error_details = []
    imported = 0

    # Report 使用 import_or_update_report 服務，目前保持逐行處理
    # TODO: 未來可改為批量操作
    for row_num, row in enumerate(rows, start=2):
        try:
            _import_report_row(row, mapping)
            imported += 1
        except Exception as e:
            error_details.append(
                {
                    "row_number": row_num,
                    "error": str(e),
                    "field": None,
                }
            )

    return imported, len(error_details), error_details


def _import_report_row(row: dict, mapping: dict) -> None:
    """Import a single report row."""
    from report.service import ReportService

    # Map columns to fields
    data = {}
    for source_col, config in mapping.items():
        target_field = config["target_field"]
        value = row.get(source_col)

        if value is not None:
            # Apply transform if specified
            transform = config.get("transform")
            if transform == "trim" and isinstance(value, str):
                value = value.strip()
            elif transform == "date" and value:
                # Try to parse date
                value = str(value)

            data[target_field] = value

    # Use existing import service
    ReportService.import_or_update_report(
        uid=data.get("uid"),
        title=data.get("title", ""),
        content=data.get("content", ""),
        report_type=data.get("report_type", "Unknown"),
        source_url=data.get("source_url", ""),
        report_id=data.get("report_id"),
        chr_no=data.get("chr_no"),
        mod=data.get("mod"),
        report_date=data.get("report_date"),
        verified_at=None,
    )


def _import_study_row(row: dict, mapping: dict) -> None:
    """Import a single study row."""
    from django.utils import timezone

    from study.models import Study

    # Get list of valid Study model fields
    valid_fields = {f.name for f in Study._meta.get_fields() if hasattr(f, "column")}
    logger.debug(f"[IMPORT] Valid Study fields: {valid_fields}")

    # Map columns to fields
    data = {}
    invalid_fields = []
    for source_col, config in mapping.items():
        target_field = config["target_field"]
        value = row.get(source_col)

        # Check if target field is valid for Study model
        if target_field not in valid_fields:
            invalid_fields.append(target_field)
            continue

        if value is not None:
            # Apply transform if specified
            transform = config.get("transform")
            if transform == "trim" and isinstance(value, str):
                value = value.strip()

            data[target_field] = value

    if invalid_fields:
        raise ValueError(
            f"Invalid field name(s) for model Study: {', '.join(repr(f) for f in invalid_fields)}."
        )

    # Create or update study
    exam_id = data.pop("exam_id", None)
    if not exam_id:
        raise ValueError("exam_id is required")

    # Set defaults for required fields that may not be mapped
    # Study model required fields: exam_status, exam_source, exam_item, equipment_type, order_datetime
    defaults_for_required = {
        "exam_status": data.get("exam_status", "pending"),
        "exam_source": data.get("exam_source", "Unknown"),
        "exam_item": data.get("exam_item", "Unknown"),
        "equipment_type": data.get("equipment_type", "Unknown"),
        "order_datetime": data.get("order_datetime", timezone.now()),
    }

    # Merge with provided data (provided data takes precedence)
    final_data = {**defaults_for_required, **data}

    Study.objects.update_or_create(
        exam_id=exam_id,
        defaults=final_data,
    )


def _cleanup_file(file_path: str) -> None:
    """Delete temporary file."""
    try:
        path = Path(file_path)
        if path.exists():
            path.unlink()
            logger.info(f"Cleaned up temp file: {file_path}")
    except Exception as e:
        logger.warning(f"Failed to cleanup file {file_path}: {e}")


def cleanup_expired_files(max_age_hours: int = 24) -> int:
    """
    Cleanup expired temporary files.

    Args:
        max_age_hours: Maximum age in hours before cleanup

    Returns:
        Number of files cleaned up
    """
    from datetime import timedelta

    from django.utils import timezone

    cutoff = timezone.now() - timedelta(hours=max_age_hours)
    cleaned = 0

    # Find expired tasks
    expired_tasks = ImportTask.objects.filter(
        created_at__lt=cutoff, status__in=[ImportTask.Status.PENDING, ImportTask.Status.PROCESSING]
    )

    for task in expired_tasks:
        _cleanup_file(task.file_path)
        task.status = ImportTask.Status.EXPIRED
        task.save(update_fields=["status", "updated_at"])
        cleaned += 1

    # Also clean orphan files
    if IMPORT_TEMP_DIR.exists():
        import time

        cutoff_timestamp = time.time() - (max_age_hours * 3600)

        for file_path in IMPORT_TEMP_DIR.iterdir():
            if file_path.is_file() and file_path.name != ".gitignore":
                if file_path.stat().st_mtime < cutoff_timestamp:
                    try:
                        file_path.unlink()
                        cleaned += 1
                    except Exception:
                        pass

    return cleaned
