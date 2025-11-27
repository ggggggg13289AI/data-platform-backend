"""
Django management command to import ONLY id='unknown' records from legacy data.db
These are system API records (patient info, allergies, lab results, etc.)

Solution: Use MD5(original_uid) as short uid to avoid 32-char limit
Keep original uid in metadata for traceability

Usage:
    python manage.py import_unknown_reports
    python manage.py import_unknown_reports --batch-size 2000
    python manage.py import_unknown_reports --verbose
"""

import hashlib
import sqlite3
from datetime import datetime

from django.core.management.base import BaseCommand
from django.utils import timezone

from report.models import Report, ReportVersion


class Command(BaseCommand):
    help = 'Import ONLY id="unknown" records (system API data) from legacy data.db'

    def add_arguments(self, parser):
        parser.add_argument(
            '--db-path',
            type=str,
            default='./data.db',
            help='Path to legacy data.db file (default: ./data.db)',
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=1000,
            help='Number of records to process per batch (default: 1000)',
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Enable verbose output',
        )

    def handle(self, *args, **options):
        """Execute the import command for id='unknown' records only."""
        db_path = options['db_path']
        batch_size = options['batch_size']
        verbose = options['verbose']

        self.stdout.write(self.style.SUCCESS('=== Importing id="unknown" Records ==='))
        self.stdout.write(f'Database: {db_path}')
        self.stdout.write(f'Batch size: {batch_size}')
        self.stdout.write('')

        try:
            stats = self._import_unknown_records(db_path, batch_size, verbose)
            self._display_results(stats)
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'ERROR: {str(e)}'))
            raise

    def _import_unknown_records(self, db_path, batch_size, verbose):
        """Import id='unknown' records from legacy database."""
        legacy_db = sqlite3.connect(db_path)
        legacy_db.row_factory = sqlite3.Row
        cursor = legacy_db.cursor()

        # Get total count
        cursor.execute("SELECT COUNT(*) FROM one_page_text_report WHERE id = 'unknown'")
        total = cursor.fetchone()[0]
        self.stdout.write(f'Total records to import: {total:,}')
        self.stdout.write('')

        stats = {
            'total': total,
            'created': 0,
            'updated': 0,
            'duplicated': 0,
            'errors': 0,
        }

        # Process in batches
        cursor.execute("""
            SELECT id, uid, content, mod, date, chr_no
            FROM one_page_text_report
            WHERE id = 'unknown'
            ORDER BY chr_no, mod, date
        """)

        processed = 0

        while True:
            rows = cursor.fetchmany(batch_size)
            if not rows:
                break

            for row in rows:
                try:
                    processed += 1
                    original_uid = row['uid']

                    # Generate short uid using MD5
                    short_uid = hashlib.md5(original_uid.encode()).hexdigest()

                    content = row['content'] or ''
                    content_hash = hashlib.sha256(content.encode()).hexdigest()

                    # Determine report type from MOD field
                    report_type = self._determine_report_type(row['mod'])

                    # Try to get or create report
                    try:
                        report = Report.objects.get(uid=short_uid)
                        # Check if content is different
                        if report.content_hash != content_hash:
                            # Update to new version
                            report.content_raw = content
                            report.content_hash = content_hash
                            report.version_number += 1
                            report.is_latest = True
                            report.verified_at = self._parse_datetime(row['date'])
                            report.save()

                            # Create version record
                            ReportVersion.objects.create(
                                report=report,
                                version_number=report.version_number,
                                content_hash=content_hash,
                                content_raw=content,
                                change_type='update',
                                verified_at=report.verified_at,
                            )
                            stats['updated'] += 1
                        else:
                            stats['duplicated'] += 1
                    except Report.DoesNotExist:
                        # Create new report
                        report = Report.objects.create(
                            uid=short_uid,
                            title=f'{report_type} - {row["chr_no"]}',
                            report_type=report_type,
                            content_raw=content,
                            content_hash=content_hash,
                            mod=row['mod'],
                            chr_no=row['chr_no'],
                            report_date=row['date'],
                            verified_at=self._parse_datetime(row['date']),
                            metadata={
                                'legacy_id': row['id'],
                                'legacy_uid': original_uid,
                                'legacy_import': True,
                                'original_mod': row['mod'],
                            }
                        )

                        # Create initial version record
                        ReportVersion.objects.create(
                            report=report,
                            version_number=1,
                            content_hash=content_hash,
                            content_raw=content,
                            change_type='create',
                            verified_at=report.verified_at,
                        )
                        stats['created'] += 1

                    if verbose and processed % 1000 == 0:
                        self.stdout.write(f'  Processed: {processed:,}')

                except Exception as e:
                    stats['errors'] += 1
                    if verbose:
                        self.stdout.write(
                            self.style.WARNING(f'  Error on record {processed}: {str(e)}')
                        )

        legacy_db.close()
        return stats

    @staticmethod
    def _parse_datetime(date_str):
        """Parse datetime string from legacy database."""
        if not date_str:
            return timezone.now()

        try:
            return datetime.fromisoformat(date_str)
        except Exception:
            pass

        formats = [
            '%Y-%m-%dT%H:%M:%S.%fZ',
            '%Y-%m-%d %H:%M:%S',
            '%Y-%m-%d',
            '%Y%m%d',
        ]

        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except Exception:
                continue

        return timezone.now()

    @staticmethod
    def _determine_report_type(mod):
        """Determine report type from MOD field."""
        if not mod:
            return 'unknown'

        mod = mod.strip().upper()

        if 'pt.get' in mod:
            return 'patient_info'
        elif 'allergy' in mod:
            return 'allergy'
        elif 'lab' in mod:
            return 'laboratory'
        elif 'vital' in mod:
            return 'vitals'
        elif 'hcheckup' in mod:
            return 'health_checkup'
        elif 'dnr' in mod:
            return 'dnr'
        elif 'death' in mod:
            return 'death_certificate'
        else:
            return 'system_data'

    def _display_results(self, stats):
        """Display import statistics."""
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(self.style.SUCCESS('IMPORT COMPLETE'))
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write('')

        self.stdout.write('Statistics:')
        self.stdout.write(f'  Total records: {stats["total"]:,}')
        self.stdout.write(f'  Created: {self.style.SUCCESS(str(stats["created"]))}{" records" if stats["created"] > 0 else ""}')
        self.stdout.write(f'  Updated: {self.style.WARNING(str(stats["updated"]))}{" records" if stats["updated"] > 0 else ""}')
        self.stdout.write(f'  Deduplicated: {self.style.WARNING(str(stats["duplicated"]))}{" records" if stats["duplicated"] > 0 else ""}')
        self.stdout.write(f'  Errors: {self.style.ERROR(str(stats["errors"]))}{" records" if stats["errors"] > 0 else ""}')
        self.stdout.write('')

        if stats['errors'] == 0:
            self.stdout.write(self.style.SUCCESS('SUCCESS: All records imported without errors!'))
        else:
            self.stdout.write(self.style.WARNING(f'WARNING: {stats["errors"]} errors occurred'))

        self.stdout.write(self.style.SUCCESS('=' * 60))
