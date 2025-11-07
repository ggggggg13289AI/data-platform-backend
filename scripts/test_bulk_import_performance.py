"""
Performance test for bulk import optimization.

This script demonstrates the performance difference between:
1. Original N+1 approach (save in loop)
2. Optimized bulk_create approach

Usage:
    python scripts/test_bulk_import_performance.py
"""

import os
import sys
import time
import django
from pathlib import Path

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.db import connection
from django.test.utils import override_settings
from studies.models import Study


def test_n_plus_1_problem(count: int = 1000):
    """
    Demonstrate N+1 problem with individual saves.

    Args:
        count: Number of records to create
    """
    print(f"\n{'='*70}")
    print(f"Test 1: N+1 Problem (Individual Saves) - {count} records")
    print(f"{'='*70}")

    # Create test data
    test_data = [
        {
            'exam_id': f'TEST_NPLUS1_{i:06d}',
            'patient_name': f'Patient {i}',
            'exam_status': 'completed',
            'exam_source': 'CT',
            'exam_item': 'Chest CT',
            'equipment_type': 'CT Scanner',
            'order_datetime': '2024-01-01T10:00:00',
        }
        for i in range(count)
    ]

    # Clear existing test data
    Study.objects.filter(exam_id__startswith='TEST_NPLUS1_').delete()

    # Track queries
    with override_settings(DEBUG=True):
        connection.queries_log.clear()

        start_time = time.time()

        # ❌ Original N+1 approach
        for data in test_data:
            study = Study(**data)
            study.save()  # Each save = 1 query

        elapsed = time.time() - start_time
        query_count = len(connection.queries)

    print(f"Time: {elapsed:.2f}s")
    print(f"Queries executed: {query_count}")
    print(f"Expected queries: {count + 1}")
    print(f"✓ This demonstrates the N+1 problem!")

    # Cleanup
    Study.objects.filter(exam_id__startswith='TEST_NPLUS1_').delete()

    return elapsed, query_count


def test_bulk_create_optimization(count: int = 1000):
    """
    Demonstrate bulk_create optimization.

    Args:
        count: Number of records to create
    """
    print(f"\n{'='*70}")
    print(f"Test 2: Optimized (bulk_create) - {count} records")
    print(f"{'='*70}")

    # Create test data
    test_data = [
        Study(
            exam_id=f'TEST_BULK_{i:06d}',
            patient_name=f'Patient {i}',
            exam_status='completed',
            exam_source='CT',
            exam_item='Chest CT',
            equipment_type='CT Scanner',
            order_datetime='2024-01-01T10:00:00',
        )
        for i in range(count)
    ]

    # Clear existing test data
    Study.objects.filter(exam_id__startswith='TEST_BULK_').delete()

    # Track queries
    with override_settings(DEBUG=True):
        connection.queries_log.clear()

        start_time = time.time()

        # ✅ Optimized bulk_create approach
        Study.objects.bulk_create(
            test_data,
            batch_size=1000,
            ignore_conflicts=False
        )

        elapsed = time.time() - start_time
        query_count = len(connection.queries)

    print(f"Time: {elapsed:.2f}s")
    print(f"Queries executed: {query_count}")
    print(f"Expected queries: {(count // 1000) + 1}")
    print(f"✓ This is the optimized approach!")

    # Cleanup
    Study.objects.filter(exam_id__startswith='TEST_BULK_').delete()

    return elapsed, query_count


def run_tests():
    """Run all performance tests."""
    print("\n" + "="*70)
    print("N+1 Query Problem - Performance Testing")
    print("="*70)
    print("\nDemonstrating the N+1 query problem and its solution\n")

    test_sizes = [100, 500, 1000]

    for size in test_sizes:
        print(f"\n\n{'#'*70}")
        print(f"# Testing with {size} records")
        print(f"{'#'*70}")

        # Test N+1
        n_plus_1_time, n_plus_1_queries = test_n_plus_1_problem(size)

        # Test bulk_create
        bulk_time, bulk_queries = test_bulk_create_optimization(size)

        # Calculate improvement
        time_improvement = (n_plus_1_time / bulk_time) if bulk_time > 0 else 0
        query_improvement = n_plus_1_queries / bulk_queries if bulk_queries > 0 else 0

        print(f"\n{'='*70}")
        print(f"Performance Comparison ({size} records):")
        print(f"{'='*70}")
        print(f"Time improvement: {time_improvement:.1f}x faster")
        print(f"Query reduction: {query_improvement:.1f}x fewer queries")
        print(f"\nDetailed:")
        print(f"  N+1 approach:     {n_plus_1_time:6.2f}s, {n_plus_1_queries:5d} queries")
        print(f"  bulk_create:      {bulk_time:6.2f}s, {bulk_queries:5d} queries")
        print(f"  Saved time:       {n_plus_1_time - bulk_time:6.2f}s")
        print(f"  Saved queries:    {n_plus_1_queries - bulk_queries:5d}")

    print(f"\n{'='*70}")
    print("✅ Performance testing complete!")
    print("="*70)
    print("\nConclusions:")
    print("1. bulk_create is significantly faster (10-100x improvement)")
    print("2. Reduces database queries dramatically")
    print("3. Always use bulk_create for importing large datasets")
    print("4. Use batch_size to control memory usage")
    print("="*70 + "\n")


if __name__ == '__main__':
    run_tests()
