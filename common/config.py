"""
Configuration constants for studies application.

This module centralizes all magic numbers, strings, and configuration values
used throughout the studies application, making them easy to find, understand,
and modify.

Design Principle:
    "Don't Repeat Yourself" - All configuration in one place
    "Self-Documenting Code" - Constants with clear names and documentation

Usage:
    >>> from studies.config import ServiceConfig
    >>> cache_ttl = ServiceConfig.FILTER_OPTIONS_CACHE_TTL
    >>> max_size = ServiceConfig.MAX_PAGE_SIZE
"""


class ServiceConfig:
    """Service layer configuration constants.

    These values control business logic behavior in the StudyService class.
    Modify these to tune performance, caching, and query behavior.
    """

    # ========== Cache Configuration ==========

    FILTER_OPTIONS_CACHE_KEY: str = "study_filter_options"
    """Redis cache key for filter options.

    Filter options (exam statuses, sources, equipment types, etc.) are cached
    to avoid repeated database DISTINCT queries.
    """

    FILTER_OPTIONS_CACHE_TTL: int = 24 * 60 * 60  # 24 hours
    """Time-to-live for filter options cache in seconds.

    Filter options change infrequently (new equipment added, new statuses, etc.)
    so a 24-hour cache is appropriate. Increase if your data is more static,
    decrease if you need fresher filter options.
    """

    # ========== Bulk Operations Configuration ==========

    BULK_CREATE_BATCH_SIZE: int = 1000
    """Batch size for bulk_create operations.

    When importing studies from DuckDB, records are inserted in batches to
    balance memory usage and performance. Larger batches are faster but use
    more memory. Smaller batches are more memory-efficient but slower.

    Recommended range: 500-2000
    """

    # ========== Pagination Configuration ==========

    DEFAULT_PAGE_SIZE: int = 20
    """Default number of items per page when limit not specified.

    This is the Django Ninja pagination default. A reasonable balance between
    response size and number of requests needed to view all data.
    """

    MAX_PAGE_SIZE: int = 100
    """Maximum allowed page size (limit parameter).

    Protects against excessive memory usage and slow queries from very large
    page sizes. If clients request limit > MAX_PAGE_SIZE, it will be capped.

    Note: 100 items * ~1KB per item = ~100KB response, reasonable for API.
    """

    MIN_PAGE_SIZE: int = 1
    """Minimum allowed page size.

    Enforces at least one item per page. Values less than 1 will use
    DEFAULT_PAGE_SIZE instead.
    """

    # ========== Search Configuration ==========

    TEXT_SEARCH_FIELD_COUNT: int = 9
    """Number of fields searched in text search (q parameter).

    Current fields: exam_id, medical_record_no, application_order_no,
    patient_name, exam_description, exam_item, exam_room,
    exam_equipment, certified_physician

    This constant documents the search breadth. If you add/remove search
    fields, update this constant and the corresponding SQL.
    """

    EXAM_DESCRIPTION_LIMIT: int = 100
    """Maximum number of exam descriptions returned in filter options.

    Exam descriptions can have thousands of unique values. To keep the filter
    options response size reasonable, we limit to the most common N descriptions.

    Increase if you want more description options, decrease for faster queries
    and smaller responses.
    """

    # ========== Query Timeout Configuration ==========

    DATABASE_QUERY_TIMEOUT: int = 30
    """Maximum seconds to wait for database queries.

    Protects against runaway queries that could lock up the application.
    Django will raise an exception if a query takes longer than this.

    Note: Set via django.db.backends.postgresql.base.DatabaseWrapper.get_new_connection
    """

    # ========== Import Configuration ==========

    MAX_IMPORT_ERRORS_TO_LOG: int = 100
    """Maximum number of import errors to store in error list.

    During bulk import, we collect error messages. To prevent memory issues
    with very large imports, we cap the number of errors stored.

    All errors are still logged, but only the first MAX_IMPORT_ERRORS_TO_LOG
    are returned in the import result.
    """


class DatabaseConfig:
    """Database-specific configuration constants.

    These values are used for database operations and query construction.
    """

    TABLE_NAME: str = "medical_examinations_fact"
    """Primary table name for medical examination records.

    This table uses a data warehouse-style naming convention ('_fact' suffix)
    indicating it contains factual transactional data.

    WARNING: Changing this requires database migration.
    """

    # ========== Index Configuration ==========

    INDEXED_FIELDS: list[str] = [
        "exam_id",  # Primary key
        "medical_record_no",  # Common lookup
        "patient_name",  # Search field
        "exam_status",  # Filter field
        "exam_source",  # Filter field
        "order_datetime",  # Sort field
    ]
    """Fields with database indexes for query optimization.

    These indexes speed up WHERE clauses, JOIN operations, and ORDER BY.
    Each index uses disk space and slows down INSERT/UPDATE, so only index
    frequently queried fields.

    See models.py Meta.indexes for actual index definitions.
    """


class APIConfig:
    """API endpoint configuration constants.

    These values control API behavior and response formatting.
    """

    # ========== Response Format ==========

    DATETIME_FORMAT: str = "iso8601"
    """Datetime serialization format.

    All datetime fields are serialized to ISO 8601 format without timezone:
    Example: "2025-11-10T10:30:00"

    This matches FastAPI default behavior for API contract compatibility.
    """

    DATETIME_EXAMPLE: str = "2025-11-10T10:30:00"
    """Example datetime string for documentation.

    Used in API documentation and validation error messages to show
    expected format.
    """

    # ========== Sort Options ==========

    DEFAULT_SORT_ORDER: str = "order_datetime_desc"
    """Default sort order when not specified in request.

    Most recent examinations first is the expected user behavior.
    """

    VALID_SORT_OPTIONS: list[str] = [
        "order_datetime_desc",  # Most recent first (default)
        "order_datetime_asc",  # Oldest first
        "patient_name_asc",  # Alphabetical by patient
    ]
    """Valid sort parameter values.

    These correspond to different ORDER BY clauses in the database query.
    Add new sort options here and implement in services.py.
    """

    # ========== Filter Options ==========

    REQUIRED_FILTER_FIELDS: list[str] = [
        "exam_statuses",
        "exam_sources",
        "equipment_types",
        "exam_rooms",
        "exam_equipments",
        "exam_descriptions",
    ]
    """Required fields in filter options response.

    These are the multi-select filter options shown to users in the UI.
    Each field should return a sorted list of distinct values from the database.
    """


class CacheConfig:
    """Cache behavior configuration.

    Controls how caching degrades gracefully when Redis is unavailable.
    """

    ENABLE_CACHE_CIRCUIT_BREAKER: bool = True
    """Enable circuit breaker pattern for cache operations.

    When enabled, after N consecutive cache failures, the circuit opens and
    cache operations are skipped for a timeout period. This prevents cascade
    failures when Redis is down.

    Set to False to disable circuit breaker (not recommended for production).
    """

    CIRCUIT_BREAKER_FAILURE_THRESHOLD: int = 5
    """Number of consecutive failures before circuit opens.

    After this many cache operation failures, stop attempting cache operations
    for CIRCUIT_BREAKER_TIMEOUT seconds.

    Recommended range: 3-10
    """

    CIRCUIT_BREAKER_TIMEOUT: int = 60
    """Seconds to wait before retrying cache after circuit opens.

    After the circuit opens due to failures, wait this long before attempting
    to use cache again (half-open state).

    Recommended range: 30-300 seconds
    """

    CACHE_OPERATION_TIMEOUT: int = 1
    """Maximum seconds to wait for cache operations.

    Prevents slow cache operations from blocking API responses. If cache
    operation takes longer than this, treat as failure and continue without cache.

    Recommended: 0.5-2 seconds
    """


# ========== Validation Constants ==========


class ValidationConfig:
    """Input validation configuration.

    These constants define validation rules for user inputs.
    """

    # Date format validation
    DATE_FORMAT_REGEX: str = r"^\d{4}-\d{2}-\d{2}$"
    """Regex pattern for date validation (YYYY-MM-DD).

    Used to validate start_date and end_date parameters before parsing.
    """

    DATE_FORMAT_EXAMPLE: str = "2025-11-10"
    """Example date string for error messages."""

    # Text search validation
    MAX_SEARCH_QUERY_LENGTH: int = 200
    """Maximum length for text search query (q parameter).

    Prevents excessively long search queries that could impact performance.
    """

    # Age range validation
    MIN_PATIENT_AGE: int = 0
    """Minimum valid patient age."""

    MAX_PATIENT_AGE: int = 150
    """Maximum valid patient age (realistic upper bound)."""

    # Application order validation
    MAX_ORDER_NO_LENGTH: int = 100
    """Maximum length for application order number."""


# ========== Export Configuration Dictionary ==========


def get_all_config() -> dict:
    """Get all configuration as dictionary for debugging/logging.

    Returns:
        Dictionary with all configuration constants organized by category

    Example:
        >>> config = get_all_config()
        >>> print(f"Cache TTL: {config['service']['cache_ttl']}")
    """
    return {
        "service": {
            "cache_key": ServiceConfig.FILTER_OPTIONS_CACHE_KEY,
            "cache_ttl": ServiceConfig.FILTER_OPTIONS_CACHE_TTL,
            "batch_size": ServiceConfig.BULK_CREATE_BATCH_SIZE,
            "default_page_size": ServiceConfig.DEFAULT_PAGE_SIZE,
            "max_page_size": ServiceConfig.MAX_PAGE_SIZE,
            "search_field_count": ServiceConfig.TEXT_SEARCH_FIELD_COUNT,
        },
        "database": {
            "table_name": DatabaseConfig.TABLE_NAME,
            "indexed_fields": DatabaseConfig.INDEXED_FIELDS,
        },
        "api": {
            "datetime_format": APIConfig.DATETIME_FORMAT,
            "default_sort": APIConfig.DEFAULT_SORT_ORDER,
            "valid_sorts": APIConfig.VALID_SORT_OPTIONS,
        },
        "cache": {
            "circuit_breaker_enabled": CacheConfig.ENABLE_CACHE_CIRCUIT_BREAKER,
            "failure_threshold": CacheConfig.CIRCUIT_BREAKER_FAILURE_THRESHOLD,
            "circuit_timeout": CacheConfig.CIRCUIT_BREAKER_TIMEOUT,
        },
        "validation": {
            "date_format": ValidationConfig.DATE_FORMAT_EXAMPLE,
            "max_query_length": ValidationConfig.MAX_SEARCH_QUERY_LENGTH,
            "age_range": (ValidationConfig.MIN_PATIENT_AGE, ValidationConfig.MAX_PATIENT_AGE),
        },
    }
