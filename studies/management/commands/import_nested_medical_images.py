"""
Django management command to import nested medical imaging records from content_raw JSON field.

These are medical imaging records embedded in pt.get_resource API responses
(stored in the 'image' field of content_raw JSON).

Usage:
    python manage.py import_nested_medical_images
    python manage.py import_nested_medical_images --batch-size 2000
    python manage.py import_nested_medical_images --verbose
"""

import json
import hashlib
from datetime import datetime
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from studies.models import Report, ReportVersion


class Command(BaseCommand):
    help = 'Import nested medical imaging records from content_raw JSON field (pt.get_resource API data)'

    def add_arguments(self, parser):
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
        parser.add_argument(
            '--skip-existing',
            action='store_true',
            help='Skip records that already exist by uid',
        )

    def handle(self, *args, **options):
        """Execute the import command for nested medical imaging records."""
        batch_size = options['batch_size']
        verbose = options['verbose']
        skip_existing = options['skip_existing']

        self.stdout.write(self.style.SUCCESS('=== Importing Nested Medical Imaging Records ==='))
        self.stdout.write('Source: pt.get_resource API (image field in content_raw)')
        self.stdout.write(f'Batch size: {batch_size}')
        self.stdout.write('')

        try:
            stats = self._import_medical_images(batch_size, verbose, skip_existing)
            self._display_results(stats)
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'ERROR: {str(e)}'))
            raise

    def _import_medical_images(self, batch_size, verbose, skip_existing):
        """Import medical imaging records from content_raw JSON field."""
        from django.db import connection

        stats = {
            'total_parent_records': 0,
            'total_image_records': 0,
            'created': 0,
            'updated': 0,
            'duplicated': 0,
            'errors': 0,
        }

        # Query records that contain 'image' field in content_raw
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT uid, content_raw, chr_no, report_date, verified_at
                FROM one_page_text_report_v2
                WHERE report_type = %s AND content_raw like %s
                ORDER BY chr_no
            """, ['system_data', '%"image"%'])

            processed = 0
            batch_records = []

            while True:
                rows = cursor.fetchmany(batch_size)
                if not rows:
                    break

                for row in rows:
                    parent_uid, content_raw, chr_no, report_date, verified_at = row
                    stats['total_parent_records'] += 1

                    try:
                        # Parse JSON content
                        content_data = json.loads(content_raw)

                        if 'image' not in content_data:
                            continue

                        image_list = content_data['image']
                        stats['total_image_records'] += len(image_list)

                        # Process each medical imaging record
                        for image_record in image_list:
                            try:
                                # Generate or use existing uid
                                if 'id' in image_record and image_record['id']:
                                    # Use image id to generate uid
                                    uid_source = f"{chr_no}_{image_record['id']}"
                                else:
                                    # Generate uid from content hash
                                    content_str = json.dumps(image_record, sort_keys=True)
                                    uid_source = hashlib.md5(content_str.encode()).hexdigest()

                                short_uid = hashlib.md5(uid_source.encode()).hexdigest()

                                # Prepare report data
                                report_data = {
                                    'uid': short_uid,
                                    'title': image_record.get('title', 'Medical Imaging Report'),
                                    'report_type': 'medical_imaging',
                                    'content_raw': json.dumps(image_record),
                                    'content_hash': hashlib.sha256(
                                        json.dumps(image_record, sort_keys=True).encode()
                                    ).hexdigest(),
                                    'mod': image_record.get('mod', 'imaging'),
                                    'chr_no': chr_no,
                                    'report_date': image_record.get('date', report_date),
                                    'verified_at': verified_at or timezone.now(),
                                    'metadata': {
                                        'parent_uid': parent_uid,
                                        'image_id': image_record.get('id'),
                                        'source': 'pt.get_resource_image',
                                        'nested_import': True,
                                    }
                                }

                                # Check if record exists
                                try:
                                    report = Report.objects.get(uid=short_uid)

                                    if skip_existing:
                                        stats['duplicated'] += 1
                                    else:
                                        # Update existing record
                                        report.content_raw = report_data['content_raw']
                                        report.content_hash = report_data['content_hash']
                                        report.version_number += 1
                                        report.is_latest = True
                                        report.verified_at = report_data['verified_at']
                                        report.save()

                                        # Create version record
                                        ReportVersion.objects.create(
                                            report=report,
                                            version_number=report.version_number,
                                            content_hash=report_data['content_hash'],
                                            content_raw=report_data['content_raw'],
                                            change_type='update',
                                            verified_at=report.verified_at,
                                        )
                                        stats['updated'] += 1

                                except Report.DoesNotExist:
                                    # Create new report
                                    report = Report.objects.create(**report_data)

                                    # Create initial version record
                                    ReportVersion.objects.create(
                                        report=report,
                                        version_number=1,
                                        content_hash=report_data['content_hash'],
                                        content_raw=report_data['content_raw'],
                                        change_type='create',
                                        verified_at=report.verified_at,
                                    )
                                    stats['created'] += 1

                                processed += 1
                                if verbose and processed % 1000 == 0:
                                    self.stdout.write(f'  Processed: {processed:,} image records')

                            except Exception as e:
                                stats['errors'] += 1
                                if verbose:
                                    self.stdout.write(
                                        self.style.WARNING(
                                            f'  Error processing image from {chr_no}: {str(e)}'
                                        )
                                    )

                    except json.JSONDecodeError as e:
                        stats['errors'] += 1
                        if verbose:
                            self.stdout.write(
                                self.style.WARNING(f'  JSON parse error in {parent_uid}: {str(e)}')
                            )

        return stats

    def _display_results(self, stats):
        """Display import statistics."""
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(self.style.SUCCESS('IMPORT COMPLETE'))
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write('')

        self.stdout.write('Statistics:')
        self.stdout.write(f'  Parent records processed: {stats["total_parent_records"]:,}')
        self.stdout.write(f'  Total image records found: {stats["total_image_records"]:,}')
        self.stdout.write(
            f'  Created: {self.style.SUCCESS(str(stats["created"]))}{" records" if stats["created"] > 0 else ""}'
        )
        self.stdout.write(
            f'  Updated: {self.style.WARNING(str(stats["updated"]))}{" records" if stats["updated"] > 0 else ""}'
        )
        self.stdout.write(
            f'  Deduplicated: {self.style.WARNING(str(stats["duplicated"]))}{" records" if stats["duplicated"] > 0 else ""}'
        )
        self.stdout.write(
            f'  Errors: {self.style.ERROR(str(stats["errors"]))}{" records" if stats["errors"] > 0 else ""}'
        )
        self.stdout.write('')

        if stats['errors'] == 0:
            self.stdout.write(self.style.SUCCESS('SUCCESS: All image records imported without errors!'))
        else:
            self.stdout.write(
                self.style.WARNING(f'WARNING: {stats["errors"]} errors occurred')
            )

        self.stdout.write(self.style.SUCCESS('=' * 60))
