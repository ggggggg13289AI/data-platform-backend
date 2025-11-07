"""
Study Model - Medical examination records.
PRAGMATIC DESIGN: Flat structure, minimal relationships.
All fields needed for search, no speculation about future uses.
"""

from django.db import models


class Study(models.Model):
    """
    Medical examination study record.
    
    Flat design - all data in one table for simplicity.
    No relationships or signals, only direct field references.
    This follows Linus Torvalds principle: eliminate special cases through better data structures.
    """
    
    # Primary key and identifiers
    exam_id = models.CharField(max_length=100, primary_key=True, db_index=True)
    medical_record_no = models.CharField(max_length=100, null=True, blank=True, db_index=True)
    application_order_no = models.CharField(max_length=100, null=True, blank=True)
    
    # Patient information
    patient_name = models.CharField(max_length=200, db_index=True)
    patient_gender = models.CharField(
        max_length=10,
        null=True,
        blank=True,
        choices=[('M', 'Male'), ('F', 'Female'), ('U', 'Unknown')]
    )
    patient_birth_date = models.CharField(max_length=20, null=True, blank=True)
    patient_age = models.IntegerField(null=True, blank=True)
    
    # Examination details
    exam_status = models.CharField(
        max_length=20,
        db_index=True,
        choices=[('pending', 'Pending'), ('completed', 'Completed'), ('cancelled', 'Cancelled')]
    )
    exam_source = models.CharField(max_length=50, db_index=True)  # CT, MRI, X-ray, etc.
    exam_item = models.CharField(max_length=200, db_index=True)  # Chest CT, Spine MRI, etc.
    exam_description = models.TextField(null=True, blank=True)
    exam_room = models.CharField(max_length=100, null=True, blank=True)
    exam_equipment = models.CharField(max_length=200, null=True, blank=True)
    equipment_type = models.CharField(max_length=100)
    
    # Time fields - CRITICAL: Must be ISO format in API
    order_datetime = models.DateTimeField(db_index=True)
    check_in_datetime = models.DateTimeField(null=True, blank=True)
    report_certification_datetime = models.DateTimeField(null=True, blank=True)
    
    # Reporting
    certified_physician = models.CharField(max_length=200, null=True, blank=True)
    data_load_time = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        # Ordering - most recent first (users expect this)
        ordering = ['-order_datetime']
        
        # Indexes for common queries
        indexes = [
            models.Index(fields=['exam_status', '-order_datetime']),
            models.Index(fields=['exam_source', '-order_datetime']),
            models.Index(fields=['patient_name']),
            models.Index(fields=['exam_item']),
        ]
        
        # Table name
        db_table = 'medical_examinations_fact'
        
        # No admin, no signals, no special handling
        verbose_name = '医疗研究'
        verbose_name_plural = '医疗研究'
    
    def __str__(self):
        return f'{self.exam_id}: {self.patient_name} - {self.exam_item}'
    
    def to_dict(self):
        """Convert to dictionary for API response.
        
        CRITICAL: DateTime format must be ISO 8601 without timezone.
        This matches FastAPI response format exactly.
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
            'order_datetime': self.order_datetime.isoformat() if self.order_datetime else None,
            'check_in_datetime': self.check_in_datetime.isoformat() if self.check_in_datetime else None,
            'report_certification_datetime': self.report_certification_datetime.isoformat() if self.report_certification_datetime else None,
            'certified_physician': self.certified_physician,
            'data_load_time': self.data_load_time.isoformat() if self.data_load_time else None,
        }
