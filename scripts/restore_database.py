#!/usr/bin/env python3
"""
Database restore script for medical imaging platform.

Supports restoring from two backup formats:
1. Django JSON backups (created with dumpdata)
2. PostgreSQL SQL backups (created with pg_dump)

⚠️  WARNING: This will REPLACE existing data in the database!
Always backup current data before restoring.

Usage:
  # Restore from Django JSON backup
  python scripts/restore_database.py backups/backup_20250125_143000.json

  # Restore from compressed backup
  python scripts/restore_database.py backups/backup_20250125_143000.json.gz

  # Restore from PostgreSQL SQL backup
  python scripts/restore_database.py backups/backup_20250125_143000.sql

  # Dry run (show what would be restored without applying)
  python scripts/restore_database.py backups/backup_20250125_143000.json --dry-run

Exit codes:
  0 on success, non-zero on failure.
"""
from __future__ import annotations

import argparse
import gzip
import os
import shutil
import subprocess
import sys
from pathlib import Path

# Add Django project root to Python path
REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

# Django setup
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()

from django.conf import settings
from django.core.management import call_command


def get_db_config() -> dict[str, str]:
    """Extract database configuration from Django settings."""
    db_config = settings.DATABASES['default']
    return {
        'engine': db_config['ENGINE'],
        'name': db_config['NAME'],
        'user': db_config['USER'],
        'password': db_config['PASSWORD'],
        'host': db_config['HOST'],
        'port': db_config['PORT'],
    }


def detect_backup_type(backup_path: Path) -> str:
    """Detect backup type from file extension."""
    # Handle compressed files
    if backup_path.suffix == '.gz':
        base_ext = backup_path.stem.split('.')[-1]
    else:
        base_ext = backup_path.suffix[1:]  # Remove leading dot

    if base_ext == 'json':
        return 'django'
    elif base_ext == 'sql':
        return 'postgres'
    else:
        raise ValueError(
            f"Unknown backup type: {backup_path.suffix}\n"
            f"Supported: .json, .json.gz, .sql, .sql.gz"
        )


def is_compressed(backup_path: Path) -> bool:
    """Check if backup file is gzip compressed."""
    return backup_path.suffix == '.gz'


def restore_django(backup_path: Path, dry_run: bool) -> None:
    """Restore from Django JSON backup."""
    print(f"Restoring from Django JSON backup...")

    if dry_run:
        print("[DRY RUN] Would execute: python manage.py loaddata")
        return

    # Decompress if needed
    if is_compressed(backup_path):
        print("Decompressing backup...")
        temp_file = backup_path.with_suffix('')
        with gzip.open(backup_path, 'rb') as f_in:
            with open(temp_file, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)
        backup_path = temp_file

    try:
        # Flush existing data (optional - can be dangerous!)
        # call_command('flush', '--no-input')

        # Load data
        call_command('loaddata', str(backup_path))

    finally:
        # Clean up temp file
        if is_compressed(backup_path):
            temp_file.unlink(missing_ok=True)


def restore_postgres(backup_path: Path, dry_run: bool) -> None:
    """Restore from PostgreSQL SQL backup."""
    print(f"Restoring from PostgreSQL SQL backup...")

    db_config = get_db_config()

    # Check if psql is available
    if not shutil.which('psql'):
        raise RuntimeError(
            "psql command not found. Please install PostgreSQL client tools.\n"
            "Download from: https://www.postgresql.org/download/"
        )

    if dry_run:
        print("[DRY RUN] Would execute: psql < backup.sql")
        return

    # Build psql command
    cmd = [
        'psql',
        '--host', db_config['host'],
        '--port', db_config['port'],
        '--username', db_config['user'],
        '--dbname', db_config['name'],
        '--no-password',
    ]

    # Set PostgreSQL password in environment
    env = os.environ.copy()
    env['PGPASSWORD'] = db_config['password']

    # Prepare input
    if is_compressed(backup_path):
        print("Decompressing backup...")
        # For compressed files, decompress on-the-fly
        with gzip.open(backup_path, 'rt', encoding='utf-8') as f:
            sql_content = f.read()
    else:
        with open(backup_path, 'r', encoding='utf-8') as f:
            sql_content = f.read()

    # Execute psql
    try:
        result = subprocess.run(
            cmd,
            env=env,
            input=sql_content,
            capture_output=True,
            text=True,
            check=True
        )

        if result.stdout:
            print(result.stdout)

    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"psql failed: {e.stderr}")


def confirm_restore(backup_path: Path, db_name: str) -> bool:
    """Ask user to confirm destructive restore operation."""
    print(f"\n{'!'*60}")
    print(f"⚠️  WARNING: DESTRUCTIVE OPERATION")
    print(f"{'!'*60}")
    print(f"This will REPLACE data in database: {db_name}")
    print(f"Backup file: {backup_path.name}")
    print(f"{'!'*60}\n")

    response = input("Type 'yes' to confirm restore: ").strip().lower()
    return response == 'yes'


def format_size(size_bytes: int) -> str:
    """Format file size in human-readable format."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.2f} TB"


def main() -> int:
    parser = argparse.ArgumentParser(
        description='Restore medical imaging platform database from backup'
    )
    parser.add_argument(
        'backup_file',
        type=Path,
        help='Path to backup file (.json, .json.gz, .sql, .sql.gz)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be restored without applying changes'
    )
    parser.add_argument(
        '--force',
        action='store_true',
        help='Skip confirmation prompt (use with caution!)'
    )

    args = parser.parse_args()

    try:
        # Validate backup file
        if not args.backup_file.exists():
            raise FileNotFoundError(f"Backup file not found: {args.backup_file}")

        # Detect backup type
        backup_type = detect_backup_type(args.backup_file)
        compressed = is_compressed(args.backup_file)

        # Get database config
        db_config = get_db_config()
        file_size = args.backup_file.stat().st_size

        # Display configuration
        print(f"\n{'='*60}")
        print(f"Database Restore")
        print(f"{'='*60}")
        print(f"Type:     {backup_type}")
        print(f"File:     {args.backup_file.name}")
        print(f"Size:     {format_size(file_size)}")
        print(f"Compress: {'Yes' if compressed else 'No'}")
        print(f"Database: {db_config['name']}")
        print(f"Host:     {db_config['host']}:{db_config['port']}")
        if args.dry_run:
            print(f"Mode:     DRY RUN (no changes will be made)")
        print(f"{'='*60}\n")

        # Confirm restore (unless force or dry-run)
        if not args.dry_run and not args.force:
            if not confirm_restore(args.backup_file, db_config['name']):
                print("Restore cancelled by user.")
                return 0

        # Perform restore
        if backup_type == 'django':
            restore_django(args.backup_file, args.dry_run)
        else:
            restore_postgres(args.backup_file, args.dry_run)

        # Display summary
        if not args.dry_run:
            print(f"\n{'='*60}")
            print(f"Restore Completed Successfully")
            print(f"{'='*60}")
            print(f"Database: {db_config['name']}")
            print(f"From:     {args.backup_file.name}")
            print(f"{'='*60}\n")

        return 0

    except Exception as e:
        print(f"\n❌ Restore failed: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
