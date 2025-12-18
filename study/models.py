"""
Study Model - Medical examination records.

This module provides the data model for medical examination studies stored in PostgreSQL.

PRAGMATIC DESIGN: Flat structure, minimal relationships.
All fields needed for search, no speculation about future uses.

Design Principles:
    - Single denormalized table ('medical_examinations_fact')
    - No FK relationships or signals, only direct field references
    - Follows Linus Torvalds principle: eliminate special cases through better data structures
    - Optimized for query performance with targeted indexes
    - All datetime fields stored in UTC without timezone info
"""

from django.db import models
from django.contrib.postgres.search import SearchVectorField
from django.contrib.postgres.indexes import GinIndex


class Study(models.Model):
    """
    Medical examination study record.

    Represents a single medical examination with complete patient and exam information.
    Stores all data required for search, filtering, and display without external relationships.

    Flat Design Rationale:
        - Eliminates N+1 query problems by storing all needed data in one record
        - No relationships or signals, only direct field references
        - Simplifies caching strategies (single record = single cache entry)
        - Reduces query complexity and improves database performance
        - Makes schema evolution straightforward without migration complexity

    Data Organization:
        1. Primary identification (exam_id, medical_record_no, application_order_no)
        2. Patient demographics (name, gender, birth_date, age)
        3. Exam specifications (status, source, item, description, room, equipment)
        4. Temporal information (order_datetime, check_in_datetime, etc.)
        5. Authorization (certified_physician)
        6. Full-text search support (search_vector)

    See Also:
        - API Contract: ../docs/api/API_CONTRACT.md
        - Service Layer: study.services.StudyService
        - API Endpoints: study.api
    """

    # ========== PRIMARY KEY AND IDENTIFIERS ==========
    # Composite identification: exam_id is primary key, medical_record_no is natural key
    
    exam_id = models.CharField(
        max_length=100, 
        primary_key=True, 
        db_index=True,
        help_text='Unique examination identifier - used as primary key'
    )
    # Indexed for fast lookup by medical record number
    medical_record_no = models.CharField(
        max_length=100, 
        null=True, 
        blank=True, 
        db_index=True,
        help_text='Patient medical record number from source system'
    )
    # Application order number for reference
    application_order_no = models.CharField(
        max_length=100, 
        null=True, 
        blank=True,
        help_text='Application order number - used for ordering tracking'
    )

    # ========== PATIENT INFORMATION ==========
    # Core patient demographics indexed for search performance
    
    # Patient name - indexed for text search (name-based lookups are common)
    patient_name = models.CharField(
        max_length=200, 
        db_index=True,
        help_text='Patient full name for display and search'
    )
    # Gender with enumerated choices for consistency
    patient_gender = models.CharField(
        max_length=10,
        null=True,
        blank=True,
        choices=[('M', 'Male'), ('F', 'Female'), ('U', 'Unknown')],
        help_text='Patient gender (M/F/U)'
    )
    # Birth date as string to support various formats from source systems
    patient_birth_date = models.CharField(
        max_length=20, 
        null=True, 
        blank=True,
        help_text='Patient date of birth (format: YYYY-MM-DD)'
    )
    # Calculated patient age at time of examination
    patient_age = models.IntegerField(
        null=True, 
        blank=True,
        help_text='Patient age in years at examination time'
    )

    # ========== EXAMINATION DETAILS ==========
    # Complete information about the examination procedure
    
    # Exam status with enumerated choices for data consistency
    exam_status = models.CharField(
        max_length=20,
        db_index=True,
        choices=[('pending', 'Pending'), ('completed', 'Completed'), ('cancelled', 'Cancelled')],
        help_text='Current status of the examination'
    )
    # Exam source (modality type) - indexed for common filtering
    exam_source = models.CharField(
        max_length=50, 
        db_index=True,
        help_text='Examination modality/source (CT, MRI, X-ray, Ultrasound, etc.)'
    )
    # Specific exam procedure type - indexed for filtering and search
    exam_item = models.CharField(
        max_length=200, 
        db_index=True,
        help_text='Specific exam procedure (e.g., Chest CT, Spine MRI, Head CT)'
    )
    # Detailed exam description
    exam_description = models.TextField(
        null=True, 
        blank=True,
        help_text='Detailed description of examination procedure and findings'
    )
    # Examination room/location
    exam_room = models.CharField(
        max_length=100, 
        null=True, 
        blank=True,
        help_text='Hospital room or facility where exam was performed'
    )
    # Specific equipment used
    exam_equipment = models.CharField(
        max_length=200, 
        null=True, 
        blank=True,
        help_text='Specific equipment/scanner name used (e.g., GE LightSpeed 16)'
    )
    # Equipment type classification (required field)
    equipment_type = models.CharField(
        max_length=100,
        help_text='Equipment type classification (CT Scanner, MRI Scanner, X-ray, etc.)'
    )

    # ========== TEMPORAL INFORMATION ==========
    # All datetime fields stored in UTC without timezone - converted to ISO format in API
    # CRITICAL: Must be ISO 8601 format without timezone in API responses
    
    # Order date/time - when examination was ordered (indexed for sorting/filtering)
    order_datetime = models.DateTimeField(
        db_index=True,
        help_text='Date/time when examination was ordered'
    )
    # Check-in date/time - when patient checked in for exam
    check_in_datetime = models.DateTimeField(
        null=True, 
        blank=True,
        help_text='Date/time when patient checked in for examination'
    )
    # Report certification date/time - when report was finalized
    report_certification_datetime = models.DateTimeField(
        null=True, 
        blank=True,
        help_text='Date/time when examination report was certified'
    )

    # ========== REPORTING AND AUTHORIZATION ==========
    # Information about who certified the results
    
    # Physician who certified the report
    certified_physician = models.CharField(
        max_length=200, 
        null=True, 
        blank=True,
        help_text='Name of physician who certified the examination report'
    )
    # When data was loaded into this system
    data_load_time = models.DateTimeField(
        null=True, 
        blank=True,
        help_text='Date/time when record was imported/loaded into system'
    )

    # ========== FULL-TEXT SEARCH SUPPORT ==========
    # PostgreSQL search vector for fast full-text search queries
    
    # Search Vector - Populated via signals or periodic tasks (or migration)
    search_vector = SearchVectorField(
        null=True, 
        blank=True,
        help_text='PostgreSQL search vector for full-text search acceleration'
    )

    class Meta:
        """
        Model metadata configuration.

        Configures database table behavior, default ordering, indexes, and display names.
        """
        
        # Default ordering: most recent examinations first (users expect this)
        # This ordering is used when no explicit sort is provided
        ordering = ['-order_datetime']

        # Database indexes for common query patterns
        # Each index is optimized for specific search scenarios:
        # 1. Status + time: Common filtering by status with date sorting
        # 2. Source + time: Common filtering by modality with date sorting
        # 3. Patient name: Text search and name-based lookups
        # 4. Exam item: Procedure type filtering
        # 5. Search vector: Full-text search acceleration
        indexes = [
            # Compound index for status filtering with date sorting
            models.Index(fields=['exam_status', '-order_datetime']),
            # Compound index for modality filtering with date sorting
            models.Index(fields=['exam_source', '-order_datetime']),
            # Simple index for patient name search
            models.Index(fields=['patient_name']),
            # Simple index for exam item (procedure type) filtering
            models.Index(fields=['exam_item']),
            # GIN (Generalized Inverted Index) for PostgreSQL full-text search
            GinIndex(fields=['search_vector']),
        ]

        # Explicit table name for production database
        # This allows version control and explicit schema management
        db_table = 'medical_examinations_fact'

        # Display names for Django admin (if enabled)
        # Chinese translations for administrative interface
        verbose_name = '医疗研究'
        verbose_name_plural = '医疗研究'

    def __str__(self) -> str:
        """
        Return string representation of the Study record.
        
        Format: 'exam_id: patient_name - exam_item'
        Example: 'EXAM_001: 张三 - 胸部CT'
        
        Used by Django admin and logging for human-readable display.
        """
        return f'{self.exam_id}: {self.patient_name} - {self.exam_item}'

    def to_dict(self) -> dict[str, any]:
        """
        Convert Study model to dictionary for API response.

        This method serializes the Study model instance into a dictionary suitable
        for API responses and JSON serialization. All datetime fields are converted
        to ISO 8601 format without timezone information.

        DateTime Conversion:
            All datetime fields are converted using isoformat(), which produces
            ISO 8601 format (YYYY-MM-DDTHH:MM:SS). Timezone information is NOT
            included as all times are stored in UTC in the database.

            CRITICAL: This format must match FastAPI response format exactly.
            Ensures consistency across backend services (Django and FastAPI).

        Returns:
            dict[str, Any]: Dictionary with all study fields serialized for API response
                - All string fields preserved as-is
                - All integer fields (age) preserved as-is
                - All optional fields may be None
                - All datetime fields converted to ISO format strings (or None)

        Example:
            >>> study = Study.objects.get(exam_id='EXAM_001')
            >>> data = study.to_dict()
            >>> data['order_datetime']
            '2024-01-15T14:30:00'
            >>> data['patient_name']
            '张三'

        Note:
            This method is used by the API layer (study.api) to convert
            queryset results to JSON responses via StudyDetail and StudyListItem schemas.
        """
        return {
            'exam_id': self.exam_id,
            'medical_record_no': self.medical_record_no,
            'application_order_no': self.application_order_no,
            'patient_name': self.patient_name,
            'patient_gender': self.patient_gender,
            'patient_birth_date': self.patient_birth_date,
            'patient_age': self.patient_age,
            'exam_status': self.exam_status,
            'exam_source': self.exam_source,
            'exam_item': self.exam_item,
            'exam_description': self.exam_description,
            'exam_room': self.exam_room,
            'exam_equipment': self.exam_equipment,
            'equipment_type': self.equipment_type,
            # Convert datetime to ISO format (YYYY-MM-DDTHH:MM:SS) without timezone
            'order_datetime': self.order_datetime.isoformat() if self.order_datetime else None,
            'check_in_datetime': self.check_in_datetime.isoformat() if self.check_in_datetime else None,
            'report_certification_datetime': self.report_certification_datetime.isoformat() if self.report_certification_datetime else None,
            'certified_physician': self.certified_physician,
            'data_load_time': self.data_load_time.isoformat() if self.data_load_time else None,
        }

