#!/usr/bin/env python3
"""
Migration runner script with proper environment setup.
This script runs the migration with the correct DuckDB path.
"""
import os
import sys

# Set the DuckDB path before importing Django
os.environ['DUCKDB_PATH'] = "../medical_exams_streaming.duckdb"

# Now import and run the migration
from migrate_from_duckdb import migrate_from_duckdb

if __name__ == '__main__':
    success = migrate_from_duckdb()
    sys.exit(0 if success else 1)
