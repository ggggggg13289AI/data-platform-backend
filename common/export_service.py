"""
Export service for generating CSV and Excel exports of study data.

PRAGMATIC DESIGN: Direct export functions without complex abstractions.
Follows Linus principles - built for current needs (5 users, 5K records).
"""

import logging
from collections.abc import Callable
from datetime import datetime
from io import BytesIO
from typing import Any

import pandas as pd
from django.db.models import QuerySet

logger = logging.getLogger(__name__)


class ExportService:
    """Service for exporting study data to various formats.

    Direct, simple implementation without over-engineering.
    Each method is self-contained and testable.
    """

    @staticmethod
    def prepare_export_data(
        queryset: QuerySet,
        progress_callback: Callable[[int], None] | None = None,
    ) -> list[dict[str, Any]]:
        """
        Convert queryset to list of dictionaries for export.

        Args:
            queryset: Django QuerySet or RawQuerySet of Study objects

        Returns:
            List of dictionaries with study data ready for export

        Note: For RawQuerySet, we iterate and convert each object to dict.
        For regular QuerySet, we could use values() but we keep it consistent.
        """
        export_data = []

        try:
            for idx, study in enumerate(queryset, start=1):
                # Convert model instance to dict, handling None values
                study_dict = {
                    "exam_id": study.exam_id,
                    "medical_record_no": study.medical_record_no or "",
                    "application_order_no": study.application_order_no or "",
                    "patient_name": study.patient_name or "",
                    "patient_gender": study.patient_gender or "",
                    "patient_birth_date": study.patient_birth_date or "",
                    "patient_age": study.patient_age if study.patient_age is not None else "",
                    "exam_status": study.exam_status or "",
                    "exam_source": study.exam_source or "",
                    "exam_item": study.exam_item or "",
                    "exam_description": study.exam_description or "",
                    "exam_room": study.exam_room or "",
                    "exam_equipment": study.exam_equipment or "",
                    "equipment_type": study.equipment_type or "",
                    "order_datetime": study.order_datetime.isoformat()
                    if study.order_datetime
                    else "",
                    "check_in_datetime": study.check_in_datetime.isoformat()
                    if study.check_in_datetime
                    else "",
                    "report_certification_datetime": study.report_certification_datetime.isoformat()
                    if study.report_certification_datetime
                    else "",
                    "certified_physician": study.certified_physician or "",
                }
                export_data.append(study_dict)

                # Check export size limit to prevent memory issues
                if len(export_data) >= ExportConfig.MAX_EXPORT_RECORDS:
                    logger.warning(
                        f"Export limit reached: {ExportConfig.MAX_EXPORT_RECORDS} records"
                    )
                    if progress_callback:
                        progress_callback(len(export_data))
                    break

                if progress_callback and idx % ExportConfig.EXPORT_BATCH_SIZE == 0:
                    progress_callback(len(export_data))

        except Exception as e:
            logger.error(f"Error preparing export data: {str(e)}")
            raise

        if progress_callback:
            progress_callback(len(export_data))

        return export_data

    @staticmethod
    def export_to_csv(
        queryset: QuerySet,
        progress_callback: Callable[[int], None] | None = None,
    ) -> bytes:
        """
        Export queryset to CSV format.

        Args:
            queryset: Django QuerySet or RawQuerySet of Study objects

        Returns:
            CSV file content as bytes

        OPTIMIZATION: Uses pandas for efficient CSV generation.
        UTF-8 with BOM for Excel compatibility.
        """
        try:
            # Prepare data
            export_data = ExportService.prepare_export_data(queryset, progress_callback)

            if not export_data:
                # Return empty CSV with headers only
                df = pd.DataFrame(columns=ExportConfig.CSV_COLUMNS)
            else:
                # Create DataFrame from export data
                df = pd.DataFrame(export_data)

                # Reorder columns to match expected output
                df = df[ExportConfig.CSV_COLUMNS]

            # Convert to CSV with UTF-8 BOM for Excel
            output = BytesIO()
            df.to_csv(
                output,
                index=False,
                encoding=ExportConfig.CSV_ENCODING,
                date_format="%Y-%m-%d %H:%M:%S",
            )

            return output.getvalue()

        except Exception as e:
            logger.error(f"Error generating CSV export: {str(e)}")
            raise

    @staticmethod
    def export_to_excel(
        queryset: QuerySet,
        progress_callback: Callable[[int], None] | None = None,
    ) -> bytes:
        """
        Export queryset to Excel (XLSX) format.

        Args:
            queryset: Django QuerySet or RawQuerySet of Study objects

        Returns:
            Excel file content as bytes

        OPTIMIZATION: Uses openpyxl engine for Excel generation.
        Includes formatting and auto-column width adjustment.
        """
        try:
            # Prepare data
            export_data = ExportService.prepare_export_data(queryset, progress_callback)

            if not export_data:
                # Create empty DataFrame with headers
                df = pd.DataFrame(columns=ExportConfig.CSV_COLUMNS)
            else:
                # Create DataFrame from export data
                df = pd.DataFrame(export_data)

                # Reorder columns to match expected output
                df = df[ExportConfig.CSV_COLUMNS]

            # Create Excel file in memory
            output = BytesIO()

            # Use ExcelWriter for more control over formatting
            engine: str = ExportConfig.EXCEL_ENGINE
            with pd.ExcelWriter(
                output,
                engine=engine,  # type: ignore[arg-type]
                datetime_format="YYYY-MM-DD HH:MM:SS",
                date_format="YYYY-MM-DD",
            ) as writer:
                # Write DataFrame to Excel
                df.to_excel(
                    writer,
                    sheet_name="Studies Export",
                    index=False,
                    freeze_panes=(1, 0),  # Freeze header row
                )

                # Apply formatting
                ExportService._adjust_excel_column_widths(writer.sheets["Studies Export"], df)

            return output.getvalue()

        except Exception as e:
            logger.error(f"Error generating Excel export: {str(e)}")
            raise

    @staticmethod
    def _adjust_excel_column_widths(worksheet, df):
        """Helper to adjust Excel column widths based on content."""
        from openpyxl.utils import get_column_letter

        for column in df.columns:
            # Calculate max length of data in column
            if not df.empty:
                max_length = df[column].astype(str).map(len).max()
            else:
                max_length = 0

            column_length = max(max_length, len(column)) + 2  # Add padding

            # Cap maximum width for readability
            column_length = min(column_length, 50)

            col_idx = df.columns.get_loc(column) + 1  # openpyxl is 1-indexed
            column_letter = get_column_letter(col_idx)
            worksheet.column_dimensions[column_letter].width = column_length

    @staticmethod
    def generate_export_filename(format: str) -> str:
        """
        Generate filename for export with timestamp.

        Args:
            format: Export format ('csv' or 'xlsx')

        Returns:
            Filename string with timestamp

        Example: studies_export_20251111_143022.csv
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        extension = "xlsx" if format == "xlsx" else "csv"
        return f"studies_export_{timestamp}.{extension}"

    @staticmethod
    def get_content_type(format: str) -> str:
        """
        Get appropriate content type for export format.

        Args:
            format: Export format ('csv' or 'xlsx')

        Returns:
            MIME content type string
        """
        if format == "xlsx":
            return "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        else:
            return "text/csv; charset=utf-8"


class ExportConfig:
    """Export-specific configuration constants.

    Centralized configuration for export functionality.
    Follows DRY principle - all export settings in one place.
    """

    # Export limits
    MAX_EXPORT_RECORDS: int = 10000
    """Maximum records to export (prevent memory issues)."""

    EXPORT_BATCH_SIZE: int = 1000
    """Batch size for processing large exports."""

    # CSV configuration
    CSV_ENCODING: str = "utf-8-sig"
    """UTF-8 with BOM for Excel compatibility."""

    CSV_COLUMNS: list[str] = [
        "exam_id",
        "medical_record_no",
        "application_order_no",
        "patient_name",
        "patient_gender",
        "patient_birth_date",
        "patient_age",
        "exam_status",
        "exam_source",
        "exam_item",
        "exam_description",
        "exam_room",
        "exam_equipment",
        "equipment_type",
        "order_datetime",
        "check_in_datetime",
        "report_certification_datetime",
        "certified_physician",
    ]
    """Column order for CSV/Excel export."""

    # Excel configuration
    EXCEL_ENGINE: str = "openpyxl"
    """Excel writer engine."""

    # Export formats
    DEFAULT_EXPORT_FORMAT: str = "csv"
    """Default format when not specified."""

    ALLOWED_EXPORT_FORMATS: list[str] = ["csv", "xlsx"]
    """Supported export formats."""
