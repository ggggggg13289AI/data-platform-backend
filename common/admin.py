"""
Django Admin configuration for Medical Imaging Management System.
Registers Study model with default admin interface.
"""

from django.contrib import admin

from study.models import Study


@admin.register(Study)
class StudyAdmin(admin.ModelAdmin):
    """Admin interface for Study model."""

    # Display columns in list view
    list_display = [
        'exam_id',
        'patient_name',
        'exam_source',
        'exam_item',
        'exam_status',
        'order_datetime',
        'certified_physician',
    ]

    # Filters on the right sidebar
    list_filter = [
        'exam_status',
        'exam_source',
        'equipment_type',
        'order_datetime',
    ]

    # Search fields
    search_fields = [
        'exam_id',
        'patient_name',
        'medical_record_no',
        'application_order_no',
    ]

    # Read-only fields (cannot be edited)
    readonly_fields = [
        'exam_id',
        'order_datetime',
        'check_in_datetime',
        'report_certification_datetime',
        'data_load_time',
    ]

    # Fieldsets for detailed view
    fieldsets = (
        ('Examination Identifiers', {
            'fields': ('exam_id', 'medical_record_no', 'application_order_no')
        }),
        ('Patient Information', {
            'fields': ('patient_name', 'patient_gender', 'patient_birth_date', 'patient_age')
        }),
        ('Examination Details', {
            'fields': (
                'exam_status',
                'exam_source',
                'exam_item',
                'exam_description',
                'exam_room',
                'exam_equipment',
                'equipment_type',
            )
        }),
        ('Timeline', {
            'fields': (
                'order_datetime',
                'check_in_datetime',
                'report_certification_datetime',
                'data_load_time',
            )
        }),
        ('Reporting', {
            'fields': ('certified_physician',)
        }),
    )

    # Ordering
    ordering = ['-order_datetime']

    # Pagination
    list_per_page = 50

    # Allow sorting by these fields
    sortable_by = [
        'exam_id',
        'patient_name',
        'exam_status',
        'exam_source',
        'order_datetime',
    ]
