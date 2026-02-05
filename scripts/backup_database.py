#!/usr/bin/env python3
"""
Database backup script for medical imaging platform.

Supports two backup modes:
1. Django mode: Uses Django's dumpdata command (JSON format)
   - Portable across databases
   - Includes all data with relations
   - Suitable for migration and version control

2. Postgres mode: Uses PostgreSQL's pg_dump command (SQL format)
   - Native PostgreSQL format
   - More efficient for large databases
   - Requires PostgreSQL client tools

Features:
- Automatic timestamped backup files
- Optional gzip compression
- Automatic cleanup of old backups
- Detailed backup summary

Usage:
  # Django JSON backup (default)
  python scripts/backup_database.py

  # PostgreSQL SQL backup
  python scripts/backup_database.py --mode postgres

  # With compression
  python scripts/backup_database.py --compress

  # Keep only last 7 backups
  python scripts/backup_database.py --keep-last 7

  # Custom output directory
  python scripts/backup_database.py --output backups/manual

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
from datetime import datetime
from pathlib import Path

# Add Django project root to Python path
REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

# Django setup (must be before Django imports, hence E402 is expected)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
import django  # noqa: E402

django.setup()

from django.conf import settings  # noqa: E402
from django.core.management import call_command  # noqa: E402


def get_db_config() -> dict[str, str]:
    """Extract database configuration from Django settings."""
    db_config = settings.DATABASES["default"]
    return {
        "engine": db_config["ENGINE"],
        "name": db_config["NAME"],
        "user": db_config["USER"],
        "password": db_config["PASSWORD"],
        "host": db_config["HOST"],
        "port": db_config["PORT"],
    }


def create_backup_filename(mode: str, compress: bool = False) -> str:
    """Generate timestamped backup filename."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    extension = "json" if mode == "django" else "sql"
    if compress:
        extension += ".gz"
    return f"backup_{timestamp}.{extension}"


def backup_django(output_path: Path, compress: bool) -> None:
    """Create backup using Django's dumpdata command."""
    print("Creating Django JSON backup...")

    # Use temporary file if compression is needed
    temp_file = output_path.with_suffix(".tmp") if compress else output_path

    # Run dumpdata command
    with open(temp_file, "w", encoding="utf-8") as f:
        call_command(
            "dumpdata",
            "--natural-foreign",
            "--natural-primary",
            "--indent",
            "2",
            stdout=f,
            exclude=[
                "contenttypes",
                "auth.permission",
                "sessions.session",
                "admin.logentry",
            ],
        )

    # Compress if requested
    if compress:
        print("Compressing backup...")
        with open(temp_file, "rb") as f_in:
            with gzip.open(output_path, "wb") as f_out:
                shutil.copyfileobj(f_in, f_out)
        temp_file.unlink()


def backup_postgres(output_path: Path, compress: bool) -> None:
    """Create backup using PostgreSQL's pg_dump command."""
    print("Creating PostgreSQL SQL backup...")

    db_config = get_db_config()

    # Check if pg_dump is available
    if not shutil.which("pg_dump"):
        raise RuntimeError(
            "pg_dump command not found. Please install PostgreSQL client tools.\n"
            "Download from: https://www.postgresql.org/download/"
        )

    # Build pg_dump command
    cmd = [
        "pg_dump",
        "--host",
        db_config["host"],
        "--port",
        db_config["port"],
        "--username",
        db_config["user"],
        "--dbname",
        db_config["name"],
        "--no-password",  # Use PGPASSWORD environment variable
        "--clean",  # Drop objects before creating
        "--if-exists",  # Use IF EXISTS when dropping
        "--create",  # Include CREATE DATABASE statement
    ]

    # Set PostgreSQL password in environment
    env = os.environ.copy()
    env["PGPASSWORD"] = db_config["password"]

    # Execute pg_dump
    try:
        result = subprocess.run(cmd, env=env, capture_output=True, text=True, check=True)

        # Write output
        if compress:
            with gzip.open(output_path, "wt", encoding="utf-8") as f:
                f.write(result.stdout)
        else:
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(result.stdout)

    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"pg_dump failed: {e.stderr}") from e


def cleanup_old_backups(backup_dir: Path, keep_last: int) -> list[Path]:
    """Remove old backup files, keeping only the most recent ones."""
    if keep_last <= 0:
        return []

    # Find all backup files
    backup_files = sorted(
        backup_dir.glob("backup_*.json*") + backup_dir.glob("backup_*.sql*"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,  # Newest first
    )

    # Delete old backups
    deleted = []
    for backup_file in backup_files[keep_last:]:
        backup_file.unlink()
        deleted.append(backup_file)

    return deleted


def format_size(size_bytes: int) -> str:
    """Format file size in human-readable format."""
    for unit in ["B", "KB", "MB", "GB"]:
        if size_bytes < 1024:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.2f} TB"


def main() -> int:
    parser = argparse.ArgumentParser(description="Backup medical imaging platform database")
    parser.add_argument(
        "--mode",
        choices=["django", "postgres"],
        default="django",
        help="Backup mode (default: django)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=REPO_ROOT / "backups",
        help="Output directory (default: backups/)",
    )
    parser.add_argument("--compress", action="store_true", help="Compress backup with gzip")
    parser.add_argument(
        "--keep-last", type=int, default=0, help="Keep only N most recent backups (0 = keep all)"
    )

    args = parser.parse_args()

    try:
        # Ensure output directory exists
        args.output.mkdir(parents=True, exist_ok=True)

        # Create backup filename
        filename = create_backup_filename(args.mode, args.compress)
        output_path = args.output / filename

        # Display configuration
        db_config = get_db_config()
        print(f"\n{'=' * 60}")
        print("Database Backup")
        print(f"{'=' * 60}")
        print(f"Mode:     {args.mode}")
        print(f"Database: {db_config['name']}")
        print(f"Host:     {db_config['host']}:{db_config['port']}")
        print(f"Output:   {output_path.relative_to(REPO_ROOT)}")
        print(f"Compress: {'Yes' if args.compress else 'No'}")
        print(f"{'=' * 60}\n")

        # Create backup
        if args.mode == "django":
            backup_django(output_path, args.compress)
        else:
            backup_postgres(output_path, args.compress)

        # Get file size
        file_size = output_path.stat().st_size

        # Cleanup old backups
        deleted_files = []
        if args.keep_last > 0:
            print(f"\nCleaning up old backups (keeping last {args.keep_last})...")
            deleted_files = cleanup_old_backups(args.output, args.keep_last)

        # Display summary
        print(f"\n{'=' * 60}")
        print("Backup Completed Successfully")
        print(f"{'=' * 60}")
        print(f"File:     {output_path.name}")
        print(f"Size:     {format_size(file_size)}")
        print(f"Location: {output_path.absolute()}")
        if deleted_files:
            print(f"\nDeleted {len(deleted_files)} old backup(s):")
            for f in deleted_files:
                print(f"  - {f.name}")
        print(f"{'=' * 60}\n")

        return 0

    except Exception as e:
        print(f"\n❌ Backup failed: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
