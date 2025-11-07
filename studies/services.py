"""
Business logic for studies.
PRAGMATIC DESIGN: Direct function calls, no signals, no complex managers.
All logic in services that can be tested and understood.
"""

from typing import Optional, List, Dict, Any
from django.db.models import Q, QuerySet, Count
from django.db import connection
from django.utils import timezone
from django.core.cache import cache
from .models import Study
from .schemas import StudySearchResponse, StudyListItem, FilterOptions
import logging

logger = logging.getLogger(__name__)


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
        Get filtered queryset for studies - OPTIMIZED with Raw SQL.

        OPTIMIZATION: Uses raw SQL with proper parameterization instead of ORM
        to leverage database query planner and avoid N+1 problems.

        The @paginate decorator will still handle pagination by:
        1. Getting the count of matching records via COUNT(*)
        2. Applying LIMIT/OFFSET to paginate results

        Args:
            q: Text search in patient_name, exam_description, exam_item
            exam_status: Filter by status (pending, completed, cancelled)
            exam_source: Filter by source (CT, MRI, X-ray, etc.)
            exam_item: Filter by exam type
            start_date: Check-in datetime from (ISO format)
            end_date: Check-in datetime to (ISO format)
            sort: Sort order (order_datetime_desc, order_datetime_asc, patient_name_asc)

        Returns:
            Filtered and sorted QuerySet (pagination applied by @paginate decorator)
        """
        # OPTIMIZATION: Use raw SQL with parameterization for better query planning
        # and to match the user's reference SQL which performs well (~500ms for full scan)

        # Build WHERE clause conditions
        conditions = []
        params = []

        # Text search: search in 3 fields with OR
        if q and q.strip():
            search_term = f"%{q}%"
            conditions.append(
                "(patient_name ILIKE %s OR exam_description ILIKE %s OR exam_item ILIKE %s)"
            )
            params.extend([search_term, search_term, search_term])

        # Filters
        if exam_status:
            conditions.append("exam_status = %s")
            params.append(exam_status)

        if exam_source:
            conditions.append("exam_source = %s")
            params.append(exam_source)

        if exam_item:
            conditions.append("exam_item = %s")
            params.append(exam_item)

        # Date range: filter on check_in_datetime (matches user's reference SQL)
        if start_date:
            try:
                from datetime import datetime
                start_dt = datetime.fromisoformat(start_date)
                conditions.append("check_in_datetime >= %s")
                params.append(start_dt)
            except (ValueError, TypeError):
                pass

        if end_date:
            try:
                from datetime import datetime
                end_dt = datetime.fromisoformat(end_date)
                conditions.append("check_in_datetime <= %s")
                params.append(end_dt)
            except (ValueError, TypeError):
                pass

        # Build complete WHERE clause
        where_clause = " AND ".join(conditions) if conditions else "1=1"

        # Determine ORDER BY
        if sort == 'order_datetime_asc':
            order_by = "ORDER BY order_datetime ASC"
        elif sort == 'patient_name_asc':
            order_by = "ORDER BY patient_name ASC"
        else:  # Default: order_datetime_desc
            order_by = "ORDER BY order_datetime DESC"

        # Build and execute raw SQL query
        sql = f"""
            SELECT * FROM medical_examinations_fact
            WHERE {where_clause}
            {order_by}
        """

        # Use queryset.raw() to maintain compatibility with @paginate decorator
        # This returns a RawQuerySet which the paginator can iterate over
        queryset = Study.objects.raw(sql, params)

        # Log the query for debugging (can be disabled in production)
        logger.debug(f"Search Query: {sql} | Params: {params}")

        return queryset
    
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
    
    # Cache key for filter options (24 hour TTL)
    FILTER_OPTIONS_CACHE_KEY = 'study_filter_options'
    FILTER_OPTIONS_CACHE_TTL = 24 * 60 * 60  # 24 hours

    @staticmethod
    def _get_filter_options_from_db() -> FilterOptions:
        """
        Get all available filter options directly from database.

        OPTIMIZATION: Called only on cache miss, using optimized queries.
        Uses raw SQL for better performance on DISTINCT operations.

        CRITICAL: Must return distinct, sorted values with no duplicates.
        This matches ../docs/api/API_CONTRACT.md specification.

        Returns:
            FilterOptions with all available filter values
        """
        # OPTIMIZATION: Use raw SQL for DISTINCT queries (faster than ORM)
        with connection.cursor() as cursor:
            # Get distinct exam_statuses
            cursor.execute(
                "SELECT DISTINCT exam_status FROM medical_examinations_fact "
                "WHERE exam_status IS NOT NULL AND exam_status != '' "
                "ORDER BY exam_status"
            )
            exam_statuses = [row[0] for row in cursor.fetchall()]

            # Get distinct exam_sources
            cursor.execute(
                "SELECT DISTINCT exam_source FROM medical_examinations_fact "
                "WHERE exam_source IS NOT NULL AND exam_source != '' "
                "ORDER BY exam_source"
            )
            exam_sources = [row[0] for row in cursor.fetchall()]

            # Get distinct exam_items
            cursor.execute(
                "SELECT DISTINCT exam_item FROM medical_examinations_fact "
                "WHERE exam_item IS NOT NULL AND exam_item != '' "
                "ORDER BY exam_item"
            )
            exam_items = [row[0] for row in cursor.fetchall()]

            # Get distinct equipment_types
            cursor.execute(
                "SELECT DISTINCT equipment_type FROM medical_examinations_fact "
                "WHERE equipment_type IS NOT NULL AND equipment_type != '' "
                "ORDER BY equipment_type"
            )
            equipment_types = [row[0] for row in cursor.fetchall()]

        return FilterOptions(
            exam_statuses=exam_statuses,
            exam_sources=exam_sources,
            exam_items=exam_items,
            equipment_types=equipment_types,
        )

    @staticmethod
    def get_filter_options() -> FilterOptions:
        """
        Get filter options with Redis caching - OPTIMIZED.

        OPTIMIZATION:
        - First check: Redis cache (5-10ms)
        - Cache miss: Query database (50-100ms) + cache result
        - TTL: 24 hours - filters change infrequently
        - Cache key: 'study_filter_options'

        Returns FilterOptions from cache or database.
        """
        # Try to get from cache first (Redis or Django's configured cache backend)
        cached_options = cache.get(StudyService.FILTER_OPTIONS_CACHE_KEY)

        if cached_options is not None:
            logger.debug("Filter options served from cache")
            return cached_options

        # Cache miss: Query database
        logger.debug("Filter options cache miss - querying database")
        filter_options = StudyService._get_filter_options_from_db()

        # Store in cache for next 24 hours
        cache.set(
            StudyService.FILTER_OPTIONS_CACHE_KEY,
            filter_options,
            StudyService.FILTER_OPTIONS_CACHE_TTL
        )

        return filter_options
    
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
