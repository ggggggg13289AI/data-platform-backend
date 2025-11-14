"""
Unit tests for base_pagination module.

Tests the shared pagination utilities created for DEBT-004 refactoring.
"""

from django.test import TestCase
from studies.base_pagination import (
    PaginationValidator,
    QuerySetCounter,
    QuerySetSlicer,
    BasePaginationHelper,
)


class TestPaginationValidator(TestCase):
    """Test pagination parameter validation."""

    def test_validate_page_with_valid_input(self):
        """Valid page numbers should pass through."""
        assert PaginationValidator.validate_page(1) == 1
        assert PaginationValidator.validate_page(10) == 10
        assert PaginationValidator.validate_page(999) == 999

    def test_validate_page_with_zero(self):
        """Page 0 should default to 1."""
        assert PaginationValidator.validate_page(0) == PaginationValidator.DEFAULT_PAGE

    def test_validate_page_with_negative(self):
        """Negative page numbers should default to 1."""
        assert PaginationValidator.validate_page(-1) == PaginationValidator.DEFAULT_PAGE
        assert PaginationValidator.validate_page(-100) == PaginationValidator.DEFAULT_PAGE

    def test_validate_page_size_with_valid_input(self):
        """Valid page sizes should pass through."""
        assert PaginationValidator.validate_page_size(1) == 1
        assert PaginationValidator.validate_page_size(20) == 20
        assert PaginationValidator.validate_page_size(100) == 100

    def test_validate_page_size_with_zero(self):
        """Page size 0 should default to 20."""
        assert PaginationValidator.validate_page_size(0) == PaginationValidator.DEFAULT_PAGE_SIZE

    def test_validate_page_size_with_negative(self):
        """Negative page sizes should default to 20."""
        assert PaginationValidator.validate_page_size(-1) == PaginationValidator.DEFAULT_PAGE_SIZE
        assert PaginationValidator.validate_page_size(-50) == PaginationValidator.DEFAULT_PAGE_SIZE

    def test_validate_page_size_exceeds_maximum(self):
        """Page sizes over 100 should default to 20."""
        assert PaginationValidator.validate_page_size(101) == PaginationValidator.DEFAULT_PAGE_SIZE
        assert PaginationValidator.validate_page_size(1000) == PaginationValidator.DEFAULT_PAGE_SIZE

    def test_calculate_offset_first_page(self):
        """First page (page 1) should have offset 0."""
        assert PaginationValidator.calculate_offset(1, 20) == 0

    def test_calculate_offset_second_page(self):
        """Second page should have offset equal to page_size."""
        assert PaginationValidator.calculate_offset(2, 20) == 20
        assert PaginationValidator.calculate_offset(2, 50) == 50

    def test_calculate_offset_arbitrary_page(self):
        """Offset calculation should follow (page - 1) * page_size formula."""
        assert PaginationValidator.calculate_offset(5, 20) == 80
        assert PaginationValidator.calculate_offset(10, 15) == 135


class TestQuerySetCounter(TestCase):
    """Test count utilities for different data types."""

    def test_count_list(self):
        """Should count list items correctly."""
        data = [1, 2, 3, 4, 5]
        assert QuerySetCounter.count(data) == 5

    def test_count_empty_list(self):
        """Should count empty list as 0."""
        assert QuerySetCounter.count([]) == 0

    def test_count_iterable(self):
        """Should count iterable items."""
        data = range(10)
        assert QuerySetCounter.count(data) == 10


class TestQuerySetSlicer(TestCase):
    """Test slicing utilities for different data types."""

    def test_slice_list_first_page(self):
        """Should slice first page correctly."""
        data = list(range(100))
        result = QuerySetSlicer.slice(data, offset=0, limit=20)
        assert result == list(range(20))

    def test_slice_list_second_page(self):
        """Should slice second page correctly."""
        data = list(range(100))
        result = QuerySetSlicer.slice(data, offset=20, limit=20)
        assert result == list(range(20, 40))

    def test_slice_list_partial_page(self):
        """Should handle partial pages at end of data."""
        data = list(range(25))
        result = QuerySetSlicer.slice(data, offset=20, limit=20)
        assert result == list(range(20, 25))

    def test_slice_list_beyond_data(self):
        """Should return empty list when offset exceeds data length."""
        data = list(range(10))
        result = QuerySetSlicer.slice(data, offset=20, limit=20)
        assert result == []


class TestBasePaginationHelper(TestCase):
    """Test complete pagination workflow."""

    def test_calculate_total_pages_exact_division(self):
        """Should calculate total pages when items divide evenly."""
        # 100 items, 20 per page = 5 pages
        assert BasePaginationHelper.calculate_total_pages(100, 20) == 5

    def test_calculate_total_pages_with_remainder(self):
        """Should round up when items don't divide evenly."""
        # 95 items, 20 per page = 5 pages (last page has 15 items)
        assert BasePaginationHelper.calculate_total_pages(95, 20) == 5

    def test_calculate_total_pages_single_item(self):
        """Should return 1 page for single item."""
        assert BasePaginationHelper.calculate_total_pages(1, 20) == 1

    def test_calculate_total_pages_zero_items(self):
        """Should return 0 pages for zero items."""
        # Formula: (0 + 20 - 1) // 20 = 19 // 20 = 0
        assert BasePaginationHelper.calculate_total_pages(0, 20) == 0

    def test_validate_and_paginate_list_first_page(self):
        """Should validate and paginate list correctly."""
        data = list(range(100))
        page, page_size, total, offset, items = (
            BasePaginationHelper.validate_and_paginate(data, page=1, page_size=20)
        )

        assert page == 1
        assert page_size == 20
        assert total == 100
        assert offset == 0
        assert items == list(range(20))

    def test_validate_and_paginate_with_invalid_params(self):
        """Should correct invalid parameters and paginate."""
        data = list(range(100))
        page, page_size, total, offset, items = (
            BasePaginationHelper.validate_and_paginate(data, page=-1, page_size=1000)
        )

        assert page == 1  # Corrected from -1
        assert page_size == 20  # Corrected from 1000
        assert total == 100
        assert offset == 0
        assert items == list(range(20))

    def test_validate_and_paginate_empty_list(self):
        """Should handle empty lists correctly."""
        data = []
        page, page_size, total, offset, items = (
            BasePaginationHelper.validate_and_paginate(data, page=1, page_size=20)
        )

        assert page == 1
        assert page_size == 20
        assert total == 0
        assert offset == 0
        assert items == []


class TestPaginationConstants(TestCase):
    """Test pagination constants match expected values."""

    def test_default_values(self):
        """Should have correct default values."""
        assert PaginationValidator.DEFAULT_PAGE == 1
        assert PaginationValidator.DEFAULT_PAGE_SIZE == 20
        assert PaginationValidator.MIN_PAGE == 1
        assert PaginationValidator.MIN_PAGE_SIZE == 1
        assert PaginationValidator.MAX_PAGE_SIZE == 100


class TestEdgeCases(TestCase):
    """Test edge cases and boundary conditions."""

    def test_large_page_number(self):
        """Should handle very large page numbers."""
        page = PaginationValidator.validate_page(999999)
        assert page == 999999

    def test_offset_calculation_large_numbers(self):
        """Should calculate offset correctly for large numbers."""
        offset = PaginationValidator.calculate_offset(1000, 100)
        assert offset == 99900

    def test_total_pages_with_one_item_per_page(self):
        """Should handle page_size of 1."""
        total_pages = BasePaginationHelper.calculate_total_pages(50, 1)
        assert total_pages == 50

    def test_total_pages_with_max_page_size(self):
        """Should handle maximum page_size."""
        total_pages = BasePaginationHelper.calculate_total_pages(1000, 100)
        assert total_pages == 10
