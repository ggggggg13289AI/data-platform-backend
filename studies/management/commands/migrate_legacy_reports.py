"""
Django management command to migrate reports from legacy data.db to new Report model.

Usage:
    python manage.py migrate_legacy_reports
    python manage.py migrate_legacy_reports --db-path /path/to/data.db
    python manage.py migrate_legacy_reports --skip-patient-info
    python manage.py migrate_legacy_reports --batch-size 1000
"""

import os
import logging
from django.core.management.base import BaseCommand, CommandError
from studies.report_service import ReportService

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Migrate reports from legacy SQLite database (data.db) to new Report model'

    def add_arguments(self, parser):
        """Define command-line arguments."""
        parser.add_argument(
            '--db-path',
            type=str,
            default='./data.db',
            help='Path to legacy data.db file (default: ./data.db)',
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=500,
            help='Number of records to process per batch (default: 500)',
        )
        parser.add_argument(
            '--skip-patient-info',
            action='store_true',
            help='Skip pt.get patient info records and only import image reports',
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Enable verbose output',
        )

    def handle(self, *args, **options):
        """Execute the migration command."""
        # Configure logging
        if options['verbose']:
            logging.basicConfig(level=logging.DEBUG)
        else:
            logging.basicConfig(level=logging.INFO)

        db_path = options['db_path']
        batch_size = options['batch_size']
        skip_patient_info = options['skip_patient_info']

        # Validate database path
        if not os.path.exists(db_path):
            raise CommandError(f'Database file not found: {db_path}')

        self.stdout.write(self.style.SUCCESS(f'Starting migration from: {db_path}'))
        self.stdout.write(f'Skip patient info: {skip_patient_info}')
        self.stdout.write(f'Batch size: {batch_size}')
        self.stdout.write('')

        try:
            # Run migration
            stats = ReportService.migrate_from_legacy_db(
                legacy_db_path=db_path,
                batch_size=batch_size,
                skip_patient_info=skip_patient_info,
            )

            # Display results
            self._display_results(stats)

        except Exception as e:
            raise CommandError(f'Migration failed: {str(e)}')

    def _display_results(self, stats):
        """Display migration statistics."""
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(self.style.SUCCESS('MIGRATION COMPLETE'))
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write('')

        # Overall statistics
        self.stdout.write(self.style.WARNING('📊 Overall Statistics'))
        self.stdout.write(f'  Total records in database: {stats["total"]:,}')
        self.stdout.write(f'  Records created: {self.style.SUCCESS(str(stats["created"]))}{" records" if stats["created"] > 0 else ""}')
        self.stdout.write(f'  Records updated: {self.style.WARNING(str(stats["updated"]))}{" records" if stats["updated"] > 0 else ""}')
        self.stdout.write(f'  Records deduplicated: {self.style.WARNING(str(stats["duplicated"]))}{" records" if stats["duplicated"] > 0 else ""}')
        self.stdout.write(f'  Records skipped: {self.style.HTTP_INFO(str(stats["skipped"]))}{" records" if stats["skipped"] > 0 else ""}')
        self.stdout.write(f'  Records with errors: {self.style.ERROR(str(stats["errors"]))}{" records" if stats["errors"] > 0 else ""}')
        self.stdout.write(f'  Total processed: {stats["summary"]["total_processed"]:,}')
        self.stdout.write(f'  Success rate: {self.style.SUCCESS(stats["summary"]["success_rate"])}')
        self.stdout.write('')

        # Statistics by report type
        if stats['by_type']:
            self.stdout.write(self.style.WARNING('📈 Statistics by Report Type'))
            for report_type in sorted(stats['by_type'].keys()):
                type_stats = stats['by_type'][report_type]
                self.stdout.write(f'  {report_type.upper()}:')
                self.stdout.write(f'    Created: {type_stats["created"]:,}')
                self.stdout.write(f'    Updated: {type_stats["updated"]:,}')
                self.stdout.write(f'    Duplicated: {type_stats["duplicated"]:,}')
            self.stdout.write('')

        # Success message
        if stats['errors'] == 0:
            self.stdout.write(self.style.SUCCESS('✅ Migration completed successfully!'))
        else:
            self.stdout.write(self.style.WARNING(f'⚠️  Migration completed with {stats["errors"]} errors'))

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=' * 60))
