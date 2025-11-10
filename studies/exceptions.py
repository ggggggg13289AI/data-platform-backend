"""
Custom exception hierarchy for studies application.

This module defines domain-specific exceptions for clear error semantics
and better error handling throughout the application.

Exception Hierarchy:
    StudyServiceError (base)
    ├── StudyNotFoundError
    ├── InvalidSearchParameterError
    ├── CacheUnavailableError
    └── BulkImportError

Usage Examples:
    >>> raise StudyNotFoundError('EXAM001')
    StudyNotFoundError: Study not found: EXAM001

    >>> raise InvalidSearchParameterError('start_date', 'invalid', 'Must be YYYY-MM-DD format')
    InvalidSearchParameterError: Invalid start_date=invalid: Must be YYYY-MM-DD format
"""

from typing import Any, Optional, List, Dict


class StudyServiceError(Exception):
    """Base exception for all study service operations.

    All custom exceptions in the studies application inherit from this base class,
    allowing for easy exception catching at service boundaries.

    Example:
        try:
            result = StudyService.get_study_detail('EXAM001')
        except StudyServiceError as e:
            logger.error(f"Service error: {e}")
            return error_response(str(e))
    """
    pass


class StudyNotFoundError(StudyServiceError):
    """Raised when a study with the given exam_id cannot be found.

    This is a domain-specific exception that clearly indicates a missing resource,
    allowing API layer to return appropriate HTTP 404 responses.

    Attributes:
        exam_id: The exam ID that was not found

    Example:
        >>> try:
        ...     study = Study.objects.get(exam_id='NONEXISTENT')
        ... except Study.DoesNotExist:
        ...     raise StudyNotFoundError('NONEXISTENT')
    """

    def __init__(self, exam_id: str):
        """Initialize with the exam ID that was not found.

        Args:
            exam_id: The exam ID that could not be located
        """
        self.exam_id = exam_id
        super().__init__(f"Study not found: {exam_id}")


class InvalidSearchParameterError(StudyServiceError):
    """Raised when search parameters are invalid or malformed.

    This exception provides detailed information about validation failures,
    helping clients understand what needs to be corrected.

    Attributes:
        param: The parameter name that is invalid
        value: The invalid value that was provided
        reason: Explanation of why the value is invalid

    Example:
        >>> if not validate_date_format(start_date):
        ...     raise InvalidSearchParameterError(
        ...         'start_date',
        ...         start_date,
        ...         'Must be ISO 8601 format (YYYY-MM-DD)'
        ...     )
    """

    def __init__(self, param: str, value: Any, reason: str):
        """Initialize with parameter details.

        Args:
            param: Name of the invalid parameter
            value: The invalid value that was provided
            reason: Human-readable explanation of the validation failure
        """
        self.param = param
        self.value = value
        self.reason = reason
        super().__init__(f"Invalid {param}={value}: {reason}")


class CacheUnavailableError(StudyServiceError):
    """Raised when Redis cache is unavailable but operation continues in degraded mode.

    This exception indicates a non-fatal error where the application can continue
    operating without cache, but with potentially degraded performance.

    Attributes:
        operation: The cache operation that failed
        fallback_action: Description of fallback behavior

    Example:
        >>> try:
        ...     cache.set('key', 'value')
        ... except ConnectionError as e:
        ...     raise CacheUnavailableError(
        ...         'cache.set',
        ...         'Querying database directly'
        ...     ) from e
    """

    def __init__(self, operation: str, fallback_action: str = 'Operating without cache'):
        """Initialize with operation details.

        Args:
            operation: The cache operation that failed (e.g., 'cache.get', 'cache.set')
            fallback_action: Description of what the service will do instead
        """
        self.operation = operation
        self.fallback_action = fallback_action
        super().__init__(
            f"Cache unavailable for {operation}. Fallback: {fallback_action}"
        )


class BulkImportError(StudyServiceError):
    """Raised when bulk import from DuckDB fails or has validation errors.

    This exception aggregates multiple import failures and provides detailed
    statistics about what succeeded and what failed.

    Attributes:
        total_records: Total number of records attempted
        successful: Number of records successfully imported
        failed: Number of records that failed
        errors: List of error messages for failed records

    Example:
        >>> result = StudyService.import_studies_from_duckdb(conn)
        >>> if result['failed'] > 0:
        ...     raise BulkImportError(
        ...         total_records=1000,
        ...         successful=950,
        ...         failed=50,
        ...         errors=result['errors']
        ...     )
    """

    def __init__(
        self,
        total_records: int,
        successful: int,
        failed: int,
        errors: Optional[List[str]] = None
    ):
        """Initialize with import statistics.

        Args:
            total_records: Total number of records attempted
            successful: Number of records successfully imported
            failed: Number of records that failed validation or import
            errors: Optional list of specific error messages
        """
        self.total_records = total_records
        self.successful = successful
        self.failed = failed
        self.errors = errors or []

        error_summary = f"Bulk import completed with {failed} failures "
        error_summary += f"({successful}/{total_records} successful)"

        if errors:
            error_summary += f". First errors: {errors[:3]}"

        super().__init__(error_summary)


class DatabaseQueryError(StudyServiceError):
    """Raised when database queries fail due to connection or execution errors.

    This wraps database-level exceptions to provide consistent error handling
    at the service layer.

    Attributes:
        query_description: Human-readable description of the query
        original_error: The original database exception

    Example:
        >>> try:
        ...     result = Study.objects.raw(sql, params)
        ... except DatabaseError as e:
        ...     raise DatabaseQueryError(
        ...         'Search studies with filters',
        ...         e
        ...     ) from e
    """

    def __init__(self, query_description: str, original_error: Exception):
        """Initialize with query details.

        Args:
            query_description: What the query was trying to do
            original_error: The underlying database exception
        """
        self.query_description = query_description
        self.original_error = original_error
        super().__init__(
            f"Database query failed: {query_description}. "
            f"Error: {type(original_error).__name__}: {str(original_error)}"
        )


# Error code mapping for API responses
ERROR_CODES = {
    StudyNotFoundError: 'STUDY_NOT_FOUND',
    InvalidSearchParameterError: 'INVALID_SEARCH_PARAMETER',
    CacheUnavailableError: 'CACHE_UNAVAILABLE',
    BulkImportError: 'BULK_IMPORT_FAILED',
    DatabaseQueryError: 'DATABASE_QUERY_ERROR',
}


def get_error_code(exception: StudyServiceError) -> str:
    """Get standardized error code for an exception.

    Args:
        exception: The exception to get code for

    Returns:
        String error code suitable for API responses

    Example:
        >>> exc = StudyNotFoundError('EXAM001')
        >>> get_error_code(exc)
        'STUDY_NOT_FOUND'
    """
    return ERROR_CODES.get(type(exception), 'STUDY_SERVICE_ERROR')


def to_error_dict(exception: StudyServiceError, request_id: Optional[str] = None) -> Dict:
    """Convert exception to standardized error dictionary for API responses.

    Args:
        exception: The exception to convert
        request_id: Optional request identifier for tracking

    Returns:
        Dictionary with error details in API-friendly format

    Example:
        >>> exc = InvalidSearchParameterError('start_date', '2025-13-01', 'Invalid month')
        >>> to_error_dict(exc, 'req-123')
        {
            'error': {
                'code': 'INVALID_SEARCH_PARAMETER',
                'message': 'Invalid start_date=2025-13-01: Invalid month',
                'details': {
                    'param': 'start_date',
                    'value': '2025-13-01',
                    'reason': 'Invalid month'
                },
                'request_id': 'req-123'
            }
        }
    """
    error_dict = {
        'error': {
            'code': get_error_code(exception),
            'message': str(exception),
        }
    }

    # Add exception-specific details
    if isinstance(exception, InvalidSearchParameterError):
        error_dict['error']['details'] = {
            'param': exception.param,
            'value': str(exception.value),
            'reason': exception.reason,
        }
    elif isinstance(exception, StudyNotFoundError):
        error_dict['error']['details'] = {
            'exam_id': exception.exam_id,
        }
    elif isinstance(exception, BulkImportError):
        error_dict['error']['details'] = {
            'total_records': exception.total_records,
            'successful': exception.successful,
            'failed': exception.failed,
            'sample_errors': exception.errors[:5] if exception.errors else [],
        }

    if request_id:
        error_dict['error']['request_id'] = request_id

    return error_dict
