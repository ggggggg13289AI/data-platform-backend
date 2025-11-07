"""
Business logic for studies.
PRAGMATIC DESIGN: Direct function calls, no signals, no complex managers.
All logic in services that can be tested and understood.
"""

from typing import Optional, List, Dict, Any
from django.db.models import Q, QuerySet, Count
from django.utils import timezone
from .models import Study
from .schemas import StudySearchResponse, StudyListItem, FilterOptions


class StudyService:
    """Service for study operations.
    
    Direct, testable logic without Django signals or managers.
    Each method is explicit and can be understood in isolation.
    """
    
    @staticmethod
    def get_studies_queryset(
        q: Optional[str] = None,
        exam_status: Optional[str] = None,
        exam_source: Optional[str] = None,
        exam_item: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        sort: str = 'order_datetime_desc',
    ) -> QuerySet:
        """
        Get filtered queryset for studies.
        
        This method returns a QuerySet with all filters applied but without pagination.
        Pagination is handled by the @paginate decorator in the API layer.
        
        Args:
            q: Text search in patient_name, exam_description, exam_item
            exam_status: Filter by status (pending, completed, cancelled)
            exam_source: Filter by source (CT, MRI, X-ray, etc.)
            exam_item: Filter by exam type
            start_date: Order datetime from (ISO format)
            end_date: Order datetime to (ISO format)
            sort: Sort order (order_datetime_desc, order_datetime_asc, patient_name_asc)
        
        Returns:
            Filtered and sorted QuerySet (pagination applied by @paginate decorator)
        """
        # Start with all studies, most recent first
        queryset = Study.objects.all()
        
        # Apply text search
        if q and q.strip():
            queryset = queryset.filter(
                Q(patient_name__icontains=q) |
                Q(exam_description__icontains=q) |
                Q(exam_item__icontains=q)
            )
        
        # Apply filters
        if exam_status:
            queryset = queryset.filter(exam_status=exam_status)
        
        if exam_source:
            queryset = queryset.filter(exam_source=exam_source)
        
        if exam_item:
            queryset = queryset.filter(exam_item=exam_item)
        
        # Apply date range
        if start_date:
            try:
                from datetime import datetime
                start_dt = datetime.fromisoformat(start_date)
                queryset = queryset.filter(order_datetime__gte=start_dt)
            except (ValueError, TypeError):
                pass  # Ignore invalid dates
        
        if end_date:
            try:
                from datetime import datetime
                end_dt = datetime.fromisoformat(end_date)
                queryset = queryset.filter(order_datetime__lte=end_dt)
            except (ValueError, TypeError):
                pass  # Ignore invalid dates
        
        # Apply sorting
        if sort == 'order_datetime_asc':
            queryset = queryset.order_by('order_datetime')
        elif sort == 'patient_name_asc':
            queryset = queryset.order_by('patient_name')
        else:  # Default: order_datetime_desc
            queryset = queryset.order_by('-order_datetime')
        
        # Return QuerySet - pagination is handled by @paginate decorator
        return queryset
    
    @staticmethod
    def search_studies(
        q: Optional[str] = None,
        exam_status: Optional[str] = None,
        exam_source: Optional[str] = None,
        exam_item: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
        sort: str = 'order_datetime_desc',
    ) -> StudySearchResponse:
        """
        DEPRECATED: Use get_studies_queryset() instead.
        
        This method is kept for backward compatibility but should not be used
        in new code. The API layer now uses @paginate decorator.
        
        TODO: Remove in next refactor when all endpoints are updated.
        """
        # Get filtered queryset
        queryset = StudyService.get_studies_queryset(
            q=q,
            exam_status=exam_status,
            exam_source=exam_source,
            exam_item=exam_item,
            start_date=start_date,
            end_date=end_date,
            sort=sort,
        )
        
        # Get total count
        total = queryset.count()
        
        # Apply pagination manually (for backward compatibility)
        offset = (page - 1) * page_size
        studies = queryset[offset:offset + page_size]
        
        # Convert to schemas
        study_list = [
            StudyListItem(
                exam_id=study.exam_id,
                medical_record_no=study.medical_record_no,
                application_order_no=study.application_order_no,
                patient_name=study.patient_name,
                patient_gender=study.patient_gender,
                patient_age=study.patient_age,
                exam_status=study.exam_status,
                exam_source=study.exam_source,
                exam_item=study.exam_item,
                exam_description=study.exam_description,
                order_datetime=study.order_datetime,
                check_in_datetime=study.check_in_datetime,
                report_certification_datetime=study.report_certification_datetime,
                certified_physician=study.certified_physician,
            )
            for study in studies
        ]
        
        # Get filter options
        filters = StudyService._get_filter_options()
        
        return StudySearchResponse(
            items=study_list,
            count=total,
            filters=filters,
        )
    
    @staticmethod
    def get_study_detail(exam_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a single study by exam_id.
        
        Args:
            exam_id: The exam ID
        
        Returns:
            Study details dict or None if not found
        """
        try:
            study = Study.objects.get(exam_id=exam_id)
            return study.to_dict()
        except Study.DoesNotExist:
            return None
    
    @staticmethod
    def _get_filter_options() -> FilterOptions:
        """
        Get all available filter options from database.
        
        CRITICAL: Must return distinct, sorted values with no duplicates.
        This matches ../docs/api/API_CONTRACT.md specification.
        
        Returns:
            FilterOptions with all available filter values
        """
        # Get distinct values, sorted alphabetically
        exam_statuses = sorted(
            Study.objects.values_list('exam_status', flat=True)
            .distinct()
            .exclude(exam_status__isnull=True)
            .exclude(exam_status='')
        )
        
        exam_sources = sorted(
            Study.objects.values_list('exam_source', flat=True)
            .distinct()
            .exclude(exam_source__isnull=True)
            .exclude(exam_source='')
        )
        
        exam_items = sorted(
            Study.objects.values_list('exam_item', flat=True)
            .distinct()
            .exclude(exam_item__isnull=True)
            .exclude(exam_item='')
        )
        
        equipment_types = sorted(
            Study.objects.values_list('equipment_type', flat=True)
            .distinct()
            .exclude(equipment_type__isnull=True)
            .exclude(equipment_type='')
        )
        
        return FilterOptions(
            exam_statuses=list(exam_statuses),
            exam_sources=list(exam_sources),
            exam_items=list(exam_items),
            equipment_types=list(equipment_types),
        )
    
    @staticmethod
    def get_filter_options() -> FilterOptions:
        """Public method to get filter options."""
        return StudyService._get_filter_options()
    
    @staticmethod
    def import_studies_from_duckdb(duckdb_connection) -> Dict[str, Any]:
        """
        Import studies from DuckDB to PostgreSQL.

        CRITICAL: This is for data migration. Must verify counts match.
        OPTIMIZATION: Uses bulk_create to avoid N+1 query problem.

        Args:
            duckdb_connection: DuckDB connection object

        Returns:
            Import statistics
        """
        # Fetch from DuckDB
        try:
            # Execute query and get results
            query_result = duckdb_connection.execute(
                'SELECT * FROM medical_examinations_fact'
            )
            result = query_result.fetchall()

            if not result:
                return {'imported': 0, 'failed': 0, 'errors': []}

            # Get column names from DuckDB using DESCRIBE
            columns_result = duckdb_connection.execute(
                'DESCRIBE medical_examinations_fact'
            ).fetchall()
            columns = [col[0] for col in columns_result]
            
            # Convert DuckDB rows to Study objects
            studies_to_create = []
            failed = 0
            errors = []
            
            for idx, row in enumerate(result):
                try:
                    row_dict = dict(zip(columns, row))
                    
                    # Create Study object (not saving yet)
                    study = Study(
                        exam_id=row_dict.get('exam_id'),
                        medical_record_no=row_dict.get('medical_record_no'),
                        application_order_no=row_dict.get('application_order_no'),
                        patient_name=row_dict.get('patient_name'),
                        patient_gender=row_dict.get('patient_gender'),
                        patient_birth_date=row_dict.get('patient_birth_date'),
                        patient_age=row_dict.get('patient_age'),
                        exam_status=row_dict.get('exam_status'),
                        exam_source=row_dict.get('exam_source'),
                        exam_item=row_dict.get('exam_item'),
                        exam_description=row_dict.get('exam_description'),
                        exam_room=row_dict.get('exam_room'),
                        exam_equipment=row_dict.get('exam_equipment'),
                        equipment_type=row_dict.get('equipment_type'),
                        order_datetime=row_dict.get('order_datetime'),
                        check_in_datetime=row_dict.get('check_in_datetime'),
                        report_certification_datetime=row_dict.get('report_certification_datetime'),
                        certified_physician=row_dict.get('certified_physician'),
                        data_load_time=row_dict.get('data_load_time'),
                    )
                    
                    studies_to_create.append(study)
                
                except Exception as e:
                    failed += 1
                    errors.append(f'Row {idx + 1}: {str(e)}')
            
            # OPTIMIZATION: Use bulk_create to insert all at once (1 query instead of N queries)
            # ignore_conflicts=True allows skipping duplicates without error
            try:
                created_studies = Study.objects.bulk_create(
                    studies_to_create,
                    batch_size=1000,  # Insert in batches to avoid memory issues
                    ignore_conflicts=True  # Skip duplicate exam_ids
                )
                imported = len(created_studies)
            except Exception as e:
                imported = 0
                errors.append(f'Bulk insert failed: {str(e)}')
            
            return {
                'imported': imported,
                'failed': failed,
                'errors': errors,
                'total': imported + failed,
            }
        
        except Exception as e:
            return {
                'imported': 0,
                'failed': 0,
                'errors': [f'Import failed: {str(e)}'],
            }
