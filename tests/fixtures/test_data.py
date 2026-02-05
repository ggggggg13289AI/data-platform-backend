"""
Test fixtures and data factories for studies app tests.

Provides reusable test data generation functions to avoid duplication
across test files and ensure consistency in test scenarios.
"""

from datetime import datetime, timedelta
from typing import Any


class StudyFactory:
    """
    Factory for generating Study model test data.

    Provides methods to create complete, minimal, and edge-case study records
    for comprehensive testing coverage.
    """

    @staticmethod
    def create_complete_study(exam_id: str = "TEST001", **overrides) -> dict[str, Any]:
        """
        Create a complete study record with all fields populated.

        Args:
            exam_id: Unique examination ID
            **overrides: Override any default field values

        Returns:
            Dictionary with all Study model fields

        Example:
            study = StudyFactory.create_complete_study(
                exam_id="CUSTOM001",
                patient_name="Custom Patient"
            )
        """
        defaults = {
            "exam_id": exam_id,
            "medical_record_no": f"MR{exam_id[4:]}",
            "application_order_no": f"ORDER{exam_id[4:]}",
            "patient_name": "Test Patient",
            "patient_gender": "M",
            "patient_birth_date": "1980-01-15",
            "patient_age": 44,
            "exam_status": "completed",
            "exam_source": "CT",
            "exam_item": "Chest CT",
            "exam_description": "Detailed chest CT examination",
            "exam_room": "CT-ROOM-1",
            "exam_equipment": "CT-SCANNER-01",
            "equipment_type": "CT",
            "order_datetime": datetime(2024, 11, 10, 9, 0, 0),
            "check_in_datetime": datetime(2024, 11, 10, 10, 0, 0),
            "report_certification_datetime": datetime(2024, 11, 10, 15, 0, 0),
            "certified_physician": "Dr. Smith",
            "data_load_time": datetime(2024, 11, 10, 16, 0, 0),
        }
        defaults.update(overrides)
        return defaults

    @staticmethod
    def create_minimal_study(exam_id: str = "MIN001") -> dict[str, Any]:
        """
        Create study with only required fields (minimal valid record).

        Args:
            exam_id: Unique examination ID

        Returns:
            Dictionary with required Study model fields only
        """
        return {
            "exam_id": exam_id,
            "medical_record_no": f"MR{exam_id[3:]}",
            "application_order_no": None,
            "patient_name": "Minimal Patient",
            "patient_gender": None,
            "patient_birth_date": None,
            "patient_age": None,
            "exam_status": "pending",
            "exam_source": "CT",
            "exam_item": "Basic Exam",
            "exam_description": None,
            "exam_room": None,
            "exam_equipment": None,
            "equipment_type": "CT",
            "order_datetime": datetime(2024, 11, 10, 9, 0, 0),
            "check_in_datetime": None,
            "report_certification_datetime": None,
            "certified_physician": None,
            "data_load_time": None,
        }

    @staticmethod
    def create_batch_studies(
        count: int = 10, base_exam_id: str = "BATCH", **common_fields
    ) -> list[dict[str, Any]]:
        """
        Create multiple study records for batch testing.

        Args:
            count: Number of studies to create
            base_exam_id: Prefix for exam IDs (will append numbers)
            **common_fields: Fields to apply to all studies

        Returns:
            List of study dictionaries

        Example:
            studies = StudyFactory.create_batch_studies(
                count=5,
                exam_status='completed'
            )
        """
        studies = []
        for i in range(count):
            exam_id = f"{base_exam_id}{str(i + 1).zfill(3)}"
            study = StudyFactory.create_complete_study(exam_id=exam_id, **common_fields)
            studies.append(study)
        return studies


class DateTimeHelper:
    """Helper functions for generating datetime test data."""

    @staticmethod
    def iso_format(dt: datetime) -> str:
        """
        Convert datetime to ISO 8601 format (timezone-naive).

        Args:
            dt: Datetime object

        Returns:
            ISO 8601 formatted string (YYYY-MM-DDTHH:MM:SS)
        """
        return dt.strftime("%Y-%m-%dT%H:%M:%S")

    @staticmethod
    def date_range(days: int = 7) -> tuple:
        """
        Generate start and end dates for date range testing.

        Args:
            days: Number of days in range

        Returns:
            Tuple of (start_date, end_date) as ISO strings
        """
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        return (start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d"))

    @staticmethod
    def create_datetime_sequence(
        base_date: datetime, count: int, interval_hours: int = 1
    ) -> list[datetime]:
        """
        Create sequence of datetime objects at regular intervals.

        Args:
            base_date: Starting datetime
            count: Number of datetimes to generate
            interval_hours: Hours between each datetime

        Returns:
            List of datetime objects
        """
        return [base_date + timedelta(hours=i * interval_hours) for i in range(count)]


class MockDataGenerator:
    """Generators for various mock data scenarios."""

    # Valid choice values from model
    EXAM_STATUSES = ["pending", "in_progress", "completed", "cancelled"]
    EXAM_SOURCES = ["CT", "MRI", "X-ray", "Ultrasound", "PET"]
    EXAM_EQUIPMENTS = [
        "CT-SCANNER-01",
        "CT-SCANNER-02",
        "MRI-MACHINE-01",
        "MRI-MACHINE-02",
        "X-RAY-01",
        "X-RAY-02",
    ]
    EXAM_DESCRIPTIONS = [
        "Chest CT",
        "Brain MRI",
        "Chest X-ray",
        "Abdominal CT",
        "Spine MRI",
        "Knee X-ray",
    ]
    EXAM_ROOMS = [
        "CT-ROOM-1",
        "CT-ROOM-2",
        "MRI-ROOM-1",
        "MRI-ROOM-2",
        "X-RAY-ROOM-1",
        "X-RAY-ROOM-2",
    ]
    GENDERS = ["M", "F"]

    @classmethod
    def study_with_status(cls, status: str, exam_id: str = "STATUS001") -> dict[str, Any]:
        """Create study with specific exam status."""
        return StudyFactory.create_complete_study(exam_id=exam_id, exam_status=status)

    @classmethod
    def study_with_source(cls, source: str, exam_id: str = "SOURCE001") -> dict[str, Any]:
        """Create study with specific exam source."""
        return StudyFactory.create_complete_study(exam_id=exam_id, exam_source=source)

    @classmethod
    def study_with_equipment(cls, equipment: str, exam_id: str = "EQUIP001") -> dict[str, Any]:
        """Create study with specific equipment."""
        return StudyFactory.create_complete_study(exam_id=exam_id, exam_equipment=equipment)

    @classmethod
    def study_with_gender(cls, gender: str, exam_id: str = "GENDER001") -> dict[str, Any]:
        """Create study with specific patient gender."""
        return StudyFactory.create_complete_study(exam_id=exam_id, patient_gender=gender)

    @classmethod
    def study_with_age(cls, age: int, exam_id: str = "AGE001") -> dict[str, Any]:
        """Create study with specific patient age."""
        birth_year = datetime.now().year - age
        return StudyFactory.create_complete_study(
            exam_id=exam_id, patient_age=age, patient_birth_date=f"{birth_year}-01-01"
        )

    @classmethod
    def studies_for_text_search(cls) -> list[dict[str, Any]]:
        """
        Create studies for text search testing across 9 fields.

        Returns studies with searchable text in:
        - exam_id
        - medical_record_no
        - patient_name
        - exam_source
        - exam_equipment
        - exam_description
        - exam_room
        - application_order_no
        - exam_status
        """
        return [
            # Study 1: Search term "CHEST" in multiple fields
            StudyFactory.create_complete_study(
                exam_id="CHEST001",
                exam_item="Chest CT",
                exam_description="Detailed chest examination",
                exam_room="CHEST-ROOM-1",
            ),
            # Study 2: Search term "MRI" in source and equipment
            StudyFactory.create_complete_study(
                exam_id="MRI001",
                exam_source="MRI",
                exam_equipment="MRI-MACHINE-01",
                exam_item="Brain MRI",
                equipment_type="MRI",
            ),
            # Study 3: Search term "PATIENT123" in name and medical record
            StudyFactory.create_complete_study(
                exam_id="SEARCH003",
                medical_record_no="MR-PATIENT123",
                patient_name="Patient123 Test",
            ),
            # Study 4: Search term "ORDER999" in application order
            StudyFactory.create_complete_study(
                exam_id="SEARCH004", application_order_no="ORDER999"
            ),
            # Study 5: Search term "completed" in status
            StudyFactory.create_complete_study(exam_id="SEARCH005", exam_status="completed"),
        ]

    @classmethod
    def studies_for_filter_testing(cls) -> list[dict[str, Any]]:
        """
        Create diverse studies for comprehensive filter testing.

        Returns studies covering various combinations of:
        - All exam statuses
        - All exam sources
        - Multiple equipment types
        - Different genders
        - Various age ranges
        - Different date ranges
        """
        base_date = datetime(2024, 11, 1, 9, 0, 0)
        studies = []

        # Create 20 studies with diverse characteristics
        for i in range(20):
            study = StudyFactory.create_complete_study(
                exam_id=f"FILTER{str(i + 1).zfill(3)}",
                exam_status=cls.EXAM_STATUSES[i % len(cls.EXAM_STATUSES)],
                exam_source=cls.EXAM_SOURCES[i % len(cls.EXAM_SOURCES)],
                exam_equipment=cls.EXAM_EQUIPMENTS[i % len(cls.EXAM_EQUIPMENTS)],
                equipment_type=cls.EXAM_SOURCES[i % len(cls.EXAM_SOURCES)],
                exam_item=cls.EXAM_DESCRIPTIONS[i % len(cls.EXAM_DESCRIPTIONS)],
                exam_room=cls.EXAM_ROOMS[i % len(cls.EXAM_ROOMS)],
                patient_gender=cls.GENDERS[i % len(cls.GENDERS)],
                patient_age=20 + (i * 3),  # Ages from 20 to 77
                patient_birth_date=f"{2004 - (i * 3)}-01-01",
                order_datetime=base_date + timedelta(days=i),
                check_in_datetime=base_date + timedelta(days=i, hours=1),
            )
            studies.append(study)

        return studies

    @classmethod
    def study_with_null_fields(cls, exam_id: str = "NULL001") -> dict[str, Any]:
        """Create study with NULL values for optional fields."""
        return {
            "exam_id": exam_id,
            "medical_record_no": f"MR{exam_id[4:]}",
            "application_order_no": None,
            "patient_name": "Null Fields Patient",
            "patient_gender": None,
            "patient_birth_date": None,
            "patient_age": None,
            "exam_status": "pending",
            "exam_source": "CT",
            "exam_item": "Basic Exam",
            "exam_description": None,
            "exam_room": None,
            "exam_equipment": None,
            "equipment_type": "CT",
            "order_datetime": datetime(2024, 11, 10, 9, 0, 0),
            "check_in_datetime": None,
            "report_certification_datetime": None,
            "certified_physician": None,
            "data_load_time": None,
        }

    @classmethod
    def study_with_edge_case_dates(cls, exam_id: str = "EDGE001") -> dict[str, Any]:
        """Create study with edge case datetime values."""
        return StudyFactory.create_complete_study(
            exam_id=exam_id,
            patient_birth_date="1900-01-01",  # Very old date
            patient_age=124,  # Edge case age
            order_datetime=datetime(2024, 1, 1, 0, 0, 0),  # Year boundary
            check_in_datetime=datetime(2024, 12, 31, 23, 59, 59),  # Year boundary
        )


class CacheTestHelper:
    """Helper functions for cache testing scenarios."""

    @staticmethod
    def mock_filter_options() -> dict[str, list[str]]:
        """
        Generate mock filter options data structure.

        Returns:
            Dictionary matching FilterOptions schema
        """
        return {
            "exam_statuses": ["pending", "in_progress", "completed", "cancelled"],
            "exam_sources": ["CT", "MRI", "X-ray", "Ultrasound", "PET"],
            "exam_items": MockDataGenerator.EXAM_DESCRIPTIONS,
            "equipment_types": MockDataGenerator.EXAM_EQUIPMENTS,
        }

    @staticmethod
    def mock_cache_key() -> str:
        """Return the actual cache key used in services."""
        from studies.config import ServiceConfig

        return ServiceConfig.FILTER_OPTIONS_CACHE_KEY

    @staticmethod
    def mock_cache_ttl() -> int:
        """Return the actual cache TTL used in services."""
        from studies.config import ServiceConfig

        return ServiceConfig.FILTER_OPTIONS_CACHE_TTL


class EdgeCaseGenerator:
    """Generators for edge case and boundary condition testing."""

    @staticmethod
    def empty_string_fields(exam_id: str = "EMPTY001") -> dict[str, Any]:
        """Create study with empty strings for optional text fields."""
        study = StudyFactory.create_complete_study(exam_id=exam_id)
        study.update(
            {
                "exam_equipment": "",
                "exam_description": "",
                "exam_room": "",
                "application_order_no": "",
            }
        )
        return study

    @staticmethod
    def boundary_age_cases() -> list[dict[str, Any]]:
        """Create studies with boundary age values."""
        return [
            MockDataGenerator.study_with_age(0, "AGE_ZERO"),
            MockDataGenerator.study_with_age(1, "AGE_MIN"),
            MockDataGenerator.study_with_age(120, "AGE_MAX"),
        ]

    @staticmethod
    def invalid_date_strings() -> list[str]:
        """Return list of invalid date format strings for testing."""
        return [
            "invalid-date",
            "2024-13-01",  # Invalid month
            "2024-02-30",  # Invalid day
            "20241110",  # Missing separators
            "11-10-2024",  # Wrong format
            "not-a-date",
        ]

    @staticmethod
    def special_character_names() -> list[dict[str, Any]]:
        """Create studies with special characters in name fields."""
        return [
            StudyFactory.create_complete_study(exam_id="SPEC001", patient_name="O'Brien, Patrick"),
            StudyFactory.create_complete_study(exam_id="SPEC002", patient_name="García, José"),
            StudyFactory.create_complete_study(exam_id="SPEC003", patient_name="李明 (Li Ming)"),
        ]


# Convenience exports for common test scenarios
COMPLETE_STUDY = StudyFactory.create_complete_study()
MINIMAL_STUDY = StudyFactory.create_minimal_study()
NULL_STUDY = MockDataGenerator.study_with_null_fields()
EDGE_DATE_STUDY = MockDataGenerator.study_with_edge_case_dates()
