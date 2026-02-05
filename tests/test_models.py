"""
Test cases for Study model.

Tests the foundation layer: model creation, validation, to_dict() serialization,
and queryset operations. Total: 15 test cases.

Test coverage:
- Model creation (complete and minimal)
- to_dict() serialization with ISO datetime format
- NULL handling for optional fields
- Field validation (choices, uniqueness)
- QuerySet operations (filtering, ordering)
- Edge cases (empty strings, special characters)
"""

from datetime import datetime

from django.db import IntegrityError
from django.test import TestCase

from study.models import Study
from tests.fixtures.test_data import (
    EdgeCaseGenerator,
    MockDataGenerator,
    StudyFactory,
)


class StudyModelCreationTests(TestCase):
    """Test Study model creation with various field combinations."""

    def test_create_study_with_all_fields(self):
        """Test creating study with all fields populated."""
        # Arrange
        study_data = StudyFactory.create_complete_study(exam_id="COMPLETE001")

        # Act
        study = Study.objects.create(**study_data)

        # Assert
        self.assertEqual(study.exam_id, "COMPLETE001")
        self.assertEqual(study.patient_name, "Test Patient")
        self.assertEqual(study.patient_gender, "M")
        self.assertEqual(study.patient_age, 44)
        self.assertEqual(study.exam_status, "completed")
        self.assertEqual(study.exam_source, "CT")
        self.assertEqual(study.exam_item, "Chest CT")
        self.assertEqual(study.equipment_type, "CT")
        self.assertIsNotNone(study.order_datetime)
        self.assertIsNotNone(study.check_in_datetime)
        self.assertIsNotNone(study.certified_physician)

    def test_create_study_with_minimal_required_fields(self):
        """Test creating study with only required fields (optional fields NULL)."""
        # Arrange
        study_data = StudyFactory.create_minimal_study(exam_id="MINIMAL001")

        # Act
        study = Study.objects.create(**study_data)

        # Assert
        self.assertEqual(study.exam_id, "MINIMAL001")
        self.assertEqual(study.patient_name, "Minimal Patient")
        self.assertIsNone(study.patient_gender)
        self.assertIsNone(study.patient_age)
        self.assertIsNone(study.check_in_datetime)
        self.assertIsNone(study.exam_description)
        self.assertIsNone(study.certified_physician)

    def test_create_study_with_null_optional_fields(self):
        """Test that NULL values are properly handled for optional fields."""
        # Arrange
        study_data = MockDataGenerator.study_with_null_fields(exam_id="NULL001")

        # Act
        study = Study.objects.create(**study_data)

        # Assert
        self.assertEqual(study.exam_id, "NULL001")
        self.assertIsNone(study.patient_gender)
        self.assertIsNone(study.patient_birth_date)
        self.assertIsNone(study.patient_age)
        self.assertIsNone(study.exam_equipment)
        self.assertIsNone(study.exam_description)
        self.assertIsNone(study.exam_room)
        self.assertIsNone(study.application_order_no)
        self.assertIsNone(study.check_in_datetime)

    def test_create_study_with_empty_strings(self):
        """Test handling of empty strings for optional text fields."""
        # Arrange
        study_data = EdgeCaseGenerator.empty_string_fields(exam_id="EMPTY001")

        # Act
        study = Study.objects.create(**study_data)

        # Assert
        self.assertEqual(study.exam_id, "EMPTY001")
        self.assertEqual(study.exam_equipment, "")
        self.assertEqual(study.exam_description, "")
        self.assertEqual(study.exam_room, "")
        self.assertEqual(study.application_order_no, "")


class StudyModelToDictTests(TestCase):
    """Test Study model to_dict() serialization method."""

    def test_to_dict_with_complete_data(self):
        """Test to_dict() serialization with all fields populated."""
        # Arrange
        study_data = StudyFactory.create_complete_study(exam_id="TODICT001")
        study = Study.objects.create(**study_data)

        # Act
        result = study.to_dict()

        # Assert
        self.assertEqual(result["exam_id"], "TODICT001")
        self.assertEqual(result["patient_name"], "Test Patient")
        self.assertEqual(result["exam_status"], "completed")
        self.assertIn("order_datetime", result)
        self.assertIn("check_in_datetime", result)

    def test_to_dict_datetime_iso_format(self):
        """Test that datetime fields are converted to ISO 8601 format."""
        # Arrange
        study_data = StudyFactory.create_complete_study(exam_id="ISO001")
        study = Study.objects.create(**study_data)

        # Act
        result = study.to_dict()

        # Assert - ISO format is YYYY-MM-DDTHH:MM:SS (no timezone)
        self.assertIsInstance(result["order_datetime"], str)
        self.assertRegex(result["order_datetime"], r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}")
        self.assertNotIn("+", result["order_datetime"])  # No timezone offset

        if result["check_in_datetime"]:
            self.assertIsInstance(result["check_in_datetime"], str)
            self.assertRegex(result["check_in_datetime"], r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}")

    def test_to_dict_null_datetime_handling(self):
        """Test that NULL datetime fields return None, not raise exception."""
        # Arrange
        study_data = StudyFactory.create_minimal_study(exam_id="NULLDT001")
        study = Study.objects.create(**study_data)

        # Act
        result = study.to_dict()

        # Assert
        self.assertIsNone(result["check_in_datetime"])
        self.assertIsNone(result["report_certification_datetime"])
        self.assertIsNone(result["data_load_time"])


class StudyModelValidationTests(TestCase):
    """Test Study model field validation and constraints."""

    def test_duplicate_exam_id_raises_error(self):
        """Test that duplicate exam_id (primary key) raises IntegrityError."""
        # Arrange
        study_data = StudyFactory.create_complete_study(exam_id="DUP001")
        Study.objects.create(**study_data)

        # Act & Assert
        with self.assertRaises(IntegrityError):
            Study.objects.create(**study_data)

    def test_valid_gender_choices(self):
        """Test that valid gender choices are accepted."""
        # Arrange & Act
        male_study = Study.objects.create(
            **StudyFactory.create_complete_study(exam_id="MALE001", patient_gender="M")
        )
        female_study = Study.objects.create(
            **StudyFactory.create_complete_study(exam_id="FEMALE001", patient_gender="F")
        )
        unknown_study = Study.objects.create(
            **StudyFactory.create_complete_study(exam_id="UNKNOWN001", patient_gender="U")
        )

        # Assert
        self.assertEqual(male_study.patient_gender, "M")
        self.assertEqual(female_study.patient_gender, "F")
        self.assertEqual(unknown_study.patient_gender, "U")

    def test_valid_exam_status_choices(self):
        """Test that valid exam status choices are accepted."""
        # Arrange & Act
        pending = Study.objects.create(**MockDataGenerator.study_with_status("pending", "PEND001"))
        completed = Study.objects.create(
            **MockDataGenerator.study_with_status("completed", "COMP001")
        )
        cancelled = Study.objects.create(
            **MockDataGenerator.study_with_status("cancelled", "CANC001")
        )

        # Assert
        self.assertEqual(pending.exam_status, "pending")
        self.assertEqual(completed.exam_status, "completed")
        self.assertEqual(cancelled.exam_status, "cancelled")


class StudyModelQuerySetTests(TestCase):
    """Test Study model QuerySet operations."""

    @classmethod
    def setUpTestData(cls):
        """Create test data once for all test methods in this class."""
        # Create studies with different statuses and dates
        for i in range(5):
            Study.objects.create(
                **StudyFactory.create_complete_study(
                    exam_id=f"QS{str(i + 1).zfill(3)}",
                    exam_status=["pending", "completed", "cancelled", "pending", "completed"][i],
                    order_datetime=datetime(2024, 11, i + 1, 9, 0, 0),
                )
            )

    def test_filter_by_exam_status(self):
        """Test filtering studies by exam_status."""
        # Act
        pending_studies = Study.objects.filter(exam_status="pending")
        completed_studies = Study.objects.filter(exam_status="completed")

        # Assert
        self.assertEqual(pending_studies.count(), 2)
        self.assertEqual(completed_studies.count(), 2)

    def test_default_ordering_by_order_datetime(self):
        """Test that default ordering is by -order_datetime (most recent first)."""
        # Act
        studies = Study.objects.all()

        # Assert
        self.assertEqual(studies.count(), 5)
        # First study should have latest date (Nov 5)
        self.assertEqual(studies[0].exam_id, "QS005")
        # Last study should have earliest date (Nov 1)
        self.assertEqual(studies[4].exam_id, "QS001")

    def test_filter_by_patient_name(self):
        """Test filtering by patient_name."""
        # Arrange
        Study.objects.create(
            **StudyFactory.create_complete_study(exam_id="NAMETEST001", patient_name="John Doe")
        )

        # Act
        results = Study.objects.filter(patient_name="John Doe")

        # Assert
        self.assertEqual(results.count(), 1)
        self.assertEqual(results[0].exam_id, "NAMETEST001")


class StudyModelEdgeCaseTests(TestCase):
    """Test Study model with edge cases and special scenarios."""

    def test_special_characters_in_patient_name(self):
        """Test handling of special characters in patient_name."""
        # Arrange
        special_names = EdgeCaseGenerator.special_character_names()

        # Act & Assert
        for study_data in special_names:
            study = Study.objects.create(**study_data)
            self.assertIsNotNone(study.patient_name)
            self.assertIn(
                study.patient_name, ["O'Brien, Patrick", "García, José", "李明 (Li Ming)"]
            )

    def test_edge_case_dates(self):
        """Test handling of edge case datetime values."""
        # Arrange
        study_data = MockDataGenerator.study_with_edge_case_dates(exam_id="EDGEDATE001")

        # Act
        study = Study.objects.create(**study_data)

        # Assert
        self.assertEqual(study.patient_birth_date, "1900-01-01")
        self.assertEqual(study.patient_age, 124)
        self.assertEqual(study.order_datetime.year, 2024)
        self.assertEqual(study.order_datetime.month, 1)
        self.assertEqual(study.order_datetime.day, 1)

    def test_string_representation(self):
        """Test __str__ method returns expected format."""
        # Arrange
        study_data = StudyFactory.create_complete_study(exam_id="STR001")
        study = Study.objects.create(**study_data)

        # Act
        str_repr = str(study)

        # Assert
        self.assertIn("STR001", str_repr)
        self.assertIn("Test Patient", str_repr)
        self.assertIn("Chest CT", str_repr)
