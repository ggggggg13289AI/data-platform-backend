"""
Data migration script: DuckDB → PostgreSQL

This script imports medical examination records from the FastAPI backend's
DuckDB database into the Django backend's PostgreSQL database.

CRITICAL: This must preserve data integrity and verify counts match.
Follows Linus principle: fail fast with explicit errors, never silent failures.

Usage:
    python scripts/migrate_from_duckdb.py

Environment variables:
    DUCKDB_PATH: Path to DuckDB database file
    DB_NAME, DB_USER, DB_PASSWORD, DB_HOST, DB_PORT: PostgreSQL connection
"""

import os
import sys
import io
import django
from pathlib import Path
from datetime import datetime
import logging

# Fix Unicode encoding for Windows
if sys.platform == 'win32':
    import locale
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from studies.models import Study
from studies.services import StudyService

logger = logging.getLogger(__name__)


def migrate_from_duckdb():
    """
    Migrate studies from DuckDB to PostgreSQL.

    This is a critical operation:
    1. Validates DuckDB connection
    2. Validates PostgreSQL connection
    3. Imports data with error handling
    4. Verifies counts match
    5. Reports results with detail
    """

    print("=" * 70)
    print("Data Migration: DuckDB → PostgreSQL")
    print("=" * 70)
    print()

    # Get DuckDB path
    duckdb_path = os.getenv('DUCKDB_PATH', '../backend/medical_imaging.duckdb')

    if not os.path.exists(duckdb_path):
        print(f"❌ ERROR: DuckDB file not found at {duckdb_path}")
        print("Please set DUCKDB_PATH environment variable to the correct location.")
        return False

    print(f"✓ DuckDB file found: {duckdb_path}")
    print()

    # Connect to DuckDB
    try:
        import duckdb
        conn = duckdb.connect(duckdb_path, read_only=True)
        print("✓ Connected to DuckDB")
    except Exception as e:
        print(f"❌ Failed to connect to DuckDB: {str(e)}")
        return False

    # Count records in DuckDB
    try:
        duckdb_count_result = conn.execute(
            'SELECT COUNT(*) as count FROM medical_examinations_fact'
        ).fetchall()
        duckdb_count = duckdb_count_result[0][0] if duckdb_count_result else 0
        print(f"✓ DuckDB contains {duckdb_count:,} examination records")
    except Exception as e:
        print(f"❌ Failed to count DuckDB records: {str(e)}")
        conn.close()
        return False

    if duckdb_count == 0:
        print("⚠️  DuckDB database is empty. Nothing to migrate.")
        conn.close()
        return True

    print()
    print("Starting import process...")
    print()

    # Import data
    try:
        result = StudyService.import_studies_from_duckdb(conn)

        imported = result.get('imported', 0)
        failed = result.get('failed', 0)
        errors = result.get('errors', [])

        print(f"✓ Import complete:")
        print(f"  - Imported: {imported:,} records")
        print(f"  - Failed: {failed:,} records")

        if errors:
            print(f"\n⚠️  Errors encountered:")
            for error in errors[:10]:  # Show first 10 errors
                print(f"  - {error}")
            if len(errors) > 10:
                print(f"  ... and {len(errors) - 10} more errors")

        print()

    except Exception as e:
        print(f"❌ Import failed: {str(e)}")
        conn.close()
        return False
    finally:
        conn.close()

    # Verify counts match
    print("Verifying data integrity...")
    print()

    try:
        postgresql_count = Study.objects.count()
        print(f"PostgreSQL now contains {postgresql_count:,} examination records")

        if postgresql_count == duckdb_count:
            print(f"✓ SUCCESS: Record counts match! ({duckdb_count:,} records)")
        else:
            difference = abs(duckdb_count - postgresql_count)
            print(f"⚠️  WARNING: Record count mismatch!")
            print(f"  - DuckDB: {duckdb_count:,} records")
            print(f"  - PostgreSQL: {postgresql_count:,} records")
            print(f"  - Difference: {difference:,} records")

            if postgresql_count < duckdb_count:
                print(f"❌ ERROR: {difference:,} records failed to import!")
                return False

    except Exception as e:
        print(f"❌ Failed to verify counts: {str(e)}")
        return False

    # Check for duplicates
    print()
    print("Checking for duplicates...")
    try:
        from django.db.models import Count
        duplicates = Study.objects.values('exam_id').annotate(
            count=Count('exam_id')
        ).filter(count__gt=1)

        duplicate_count = duplicates.count()

        if duplicate_count == 0:
            print("✓ No duplicates found")
        else:
            print(f"⚠️  WARNING: Found {duplicate_count} duplicate exam_ids:")
            for dup in duplicates[:5]:
                print(f"  - {dup['exam_id']}: {dup['count']} copies")
            if duplicate_count > 5:
                print(f"  ... and {duplicate_count - 5} more duplicates")
            return False

    except Exception as e:
        print(f"⚠️  Could not check for duplicates: {str(e)}")

    # Summary
    print()
    print("=" * 70)
    print("✓ Migration completed successfully!")
    print("=" * 70)
    print()
    print("Next steps:")
    print("1. Verify frontend API responses match FastAPI (test with curl)")
    print("2. Run automated tests to verify format compatibility")
    print("3. Switch frontend to point to Django backend on port 8001")
    print()

    return True


if __name__ == '__main__':
    success = migrate_from_duckdb()
    sys.exit(0 if success else 1)
