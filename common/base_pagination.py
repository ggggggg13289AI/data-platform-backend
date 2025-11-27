"""
Base pagination utilities for Studies API.

Provides shared pagination logic to eliminate code duplication across
StudyPagination, ProjectPagination, and ReportPagination classes.

Related: DEBT-004 - Code duplication in pagination logic
"""

from typing import Any

from django.db import connection


class PaginationValidator:
    """
    Validation utilities for pagination parameters.

    Centralizes validation logic to ensure consistency across all pagination classes.
    """

    DEFAULT_PAGE = 1
    DEFAULT_PAGE_SIZE = 20
    MIN_PAGE = 1
    MIN_PAGE_SIZE = 1
    MAX_PAGE_SIZE = 100

    @classmethod
    def validate_page(cls, page: int) -> int:
        """
        Validate and normalize page number.

        Args:
            page: Requested page number (1-indexed)

        Returns:
            Validated page number (minimum 1)
        """
        if page < cls.MIN_PAGE:
            return cls.DEFAULT_PAGE
        return page

    @classmethod
    def validate_page_size(cls, page_size: int) -> int:
        """
        Validate and normalize page size.

        Args:
            page_size: Requested items per page

        Returns:
            Validated page size (1-100 range, default 20)
        """
        if page_size < cls.MIN_PAGE_SIZE or page_size > cls.MAX_PAGE_SIZE:
            return cls.DEFAULT_PAGE_SIZE
        return page_size

    @classmethod
    def calculate_offset(cls, page: int, page_size: int) -> int:
        """
        Calculate database offset from page number.

        Args:
            page: Page number (1-indexed)
            page_size: Items per page

        Returns:
            Offset for database query (0-indexed)
        """
        return (page - 1) * page_size


class QuerySetCounter:
    """
    Count utilities for different QuerySet types.

    Handles counting for regular QuerySet, RawQuerySet, and list data.
    """

    @staticmethod
    def count(data: Any) -> int:
        """
        Get total count from various data types.

        Handles:
        - Regular Django QuerySet (has .count() method)
        - RawQuerySet (requires separate COUNT query)
        - Lists and iterables

        Args:
            data: QuerySet, RawQuerySet, or list

        Returns:
            Total number of items
        """
        # Try QuerySet.count() first
        if hasattr(data, 'count'):
            try:
                result = data.count()
                return int(result) if result is not None else 0
            except TypeError:
                # count() exists but not callable
                pass

        # Handle RawQuerySet
        if hasattr(data, 'raw_query'):
            return QuerySetCounter._count_raw_queryset(data)

        # Fallback to list length
        if isinstance(data, list):
            return len(data)

        # Last resort: iterate and count
        return len(list(data))

    @staticmethod
    def _count_raw_queryset(queryset) -> int:
        """
        Count results from RawQuerySet.

        RawQuerySet doesn't support .count(), so we need to:
        1. Extract the raw SQL and parameters
        2. Convert SELECT * to SELECT COUNT(*)
        3. Execute the COUNT query separately

        Args:
            queryset: RawQuerySet instance

        Returns:
            Total number of rows
        """
        try:
            # Access the raw SQL and params from RawQuerySet
            raw_sql = queryset.raw_query
            query_params = queryset.params or []

            # Convert SELECT * to SELECT COUNT(*)
            count_sql = raw_sql.replace('SELECT *', 'SELECT COUNT(*)', 1)

            # Remove ORDER BY and LIMIT for count query (optimization)
            if 'ORDER BY' in count_sql:
                count_sql = count_sql[:count_sql.index('ORDER BY')]
            if 'LIMIT' in count_sql:
                count_sql = count_sql[:count_sql.index('LIMIT')]

            # Execute COUNT query
            with connection.cursor() as cursor:
                # If LIMIT/OFFSET were added by service layer, exclude those params
                count_params = query_params
                if 'LIMIT' in raw_sql:
                    # Remove last 2 params (limit and offset)
                    count_params = query_params[:-2] if len(query_params) >= 2 else query_params

                cursor.execute(count_sql, count_params)
                result = cursor.fetchone()
                return int(result[0]) if result and result[0] is not None else 0

        except (AttributeError, Exception):
            # Fallback: count by iterating (less efficient but works)
            return len(list(queryset))


class QuerySetSlicer:
    """
    Slicing utilities for different data types.

    Handles slicing for QuerySet, RawQuerySet, and list data.
    """

    @staticmethod
    def slice(data: Any, offset: int, limit: int) -> list[Any]:
        """
        Slice data with offset and limit.

        Handles:
        - Regular Django QuerySet (efficient database slicing)
        - RawQuerySet (already paginated by service layer)
        - Lists (Python slicing)

        Args:
            data: QuerySet, RawQuerySet, or list
            offset: Starting index (0-based)
            limit: Number of items to retrieve

        Returns:
            Sliced data as list
        """
        # Check if RawQuerySet (already paginated)
        if hasattr(data, 'raw_query'):
            # Service layer already applied LIMIT/OFFSET at database level
            return list(data)

        # Regular QuerySet or list - apply Python slicing
        if isinstance(data, list):
            return data[offset:offset + limit]

        # QuerySet - let Django handle efficient slicing
        return list(data[offset:offset + limit])


class BasePaginationHelper:
    """
    Base pagination helper with shared logic.

    This class provides common pagination utilities that can be used
    by all pagination classes (Report, Study, Project) to eliminate
    code duplication and ensure consistent behavior.

    Usage:
        # In your pagination class
        page = PaginationValidator.validate_page(raw_page)
        page_size = PaginationValidator.validate_page_size(raw_page_size)
        offset = PaginationValidator.calculate_offset(page, page_size)
        total = QuerySetCounter.count(queryset)
        items = QuerySetSlicer.slice(queryset, offset, page_size)
    """

    @staticmethod
    def calculate_total_pages(total_count: int, page_size: int) -> int:
        """
        Calculate total number of pages.

        Args:
            total_count: Total number of items
            page_size: Items per page

        Returns:
            Total number of pages
        """
        if page_size <= 0:
            return 1
        return (total_count + page_size - 1) // page_size

    @staticmethod
    def validate_and_paginate(
        data: Any,
        page: int,
        page_size: int,
    ) -> tuple[int, int, int, int, list[Any]]:
        """
        Complete pagination workflow: validate, count, slice.

        Args:
            data: QuerySet, RawQuerySet, or list to paginate
            page: Requested page number (1-indexed)
            page_size: Requested items per page

        Returns:
            Tuple of (validated_page, validated_page_size, total_count, offset, items)
        """
        # Validate parameters
        validated_page = PaginationValidator.validate_page(page)
        validated_page_size = PaginationValidator.validate_page_size(page_size)

        # Get total count
        total_count = QuerySetCounter.count(data)

        # Calculate offset
        offset = PaginationValidator.calculate_offset(validated_page, validated_page_size)

        # Slice data
        items = QuerySetSlicer.slice(data, offset, validated_page_size)

        return validated_page, validated_page_size, total_count, offset, items
