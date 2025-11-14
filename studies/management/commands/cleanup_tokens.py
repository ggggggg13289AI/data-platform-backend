"""
Management command to clean up expired JWT tokens from TokenBlackList.

This command removes expired OutstandingToken and BlacklistedToken records
to prevent unlimited database growth and maintain optimal performance.

Usage:
    python manage.py cleanup_tokens --days=30 --dry-run
    python manage.py cleanup_tokens --days=30

Related documentation:
    docs/authentication/token-blacklist.md
"""

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from django.db import connection
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Clean up expired tokens from TokenBlackList tables'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=30,
            help='Keep tokens from last N days (default: 30)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Preview deletion without actually deleting records',
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Show detailed output',
        )

    def handle(self, *args, **options):
        days = options['days']
        dry_run = options['dry_run']
        verbose = options['verbose']

        # Validate parameters
        if days < 0:
            raise CommandError('--days must be >= 0')

        # Calculate cutoff date
        cutoff_date = timezone.now() - timedelta(days=days)

        self.stdout.write(
            self.style.MIGRATE_HEADING(
                '\n=== JWT Token Cleanup ==='
            )
        )
        self.stdout.write(f'Cutoff date: {cutoff_date.isoformat()}')
        self.stdout.write(f'Mode: {"DRY RUN" if dry_run else "LIVE"}')
        self.stdout.write('')

        try:
            # Import here to avoid dependency issues
            from token_blacklist.models import OutstandingToken, BlacklistedToken

            # Get database size before cleanup
            db_size_before = self._get_table_size() if verbose else None

            # Find expired tokens
            expired_tokens = OutstandingToken.objects.filter(
                expires_at__lt=cutoff_date
            )
            expired_count = expired_tokens.count()

            # Find corresponding blacklisted tokens (will be CASCADE deleted)
            blacklisted_count = BlacklistedToken.objects.filter(
                token__expires_at__lt=cutoff_date
            ).count()

            # Display statistics
            self.stdout.write(self.style.WARNING('Statistics:'))
            self.stdout.write(f'  Expired OutstandingTokens: {expired_count:,}')
            self.stdout.write(f'  Blacklisted tokens (CASCADE): {blacklisted_count:,}')
            self.stdout.write(f'  Total records to delete: {expired_count:,}')

            if verbose and db_size_before:
                self.stdout.write(f'  Database size before: {db_size_before}')

            # Perform deletion
            if dry_run:
                self.stdout.write('')
                self.stdout.write(
                    self.style.WARNING('[DRY RUN] No records deleted')
                )
                self.stdout.write(
                    'Run without --dry-run to perform actual deletion'
                )
            else:
                self.stdout.write('')
                self.stdout.write('Deleting expired tokens...')

                deleted_outstanding, deletion_info = expired_tokens.delete()

                # Verify deletion
                deleted_blacklisted = deletion_info.get(
                    'token_blacklist.BlacklistedToken',
                    0
                )

                self.stdout.write(
                    self.style.SUCCESS(
                        f'\n✅ Successfully deleted {deleted_outstanding:,} records'
                    )
                )
                self.stdout.write(
                    f'  OutstandingTokens deleted: {deleted_outstanding:,}'
                )
                self.stdout.write(
                    f'  BlacklistedTokens deleted (CASCADE): {deleted_blacklisted:,}'
                )

                if verbose:
                    db_size_after = self._get_table_size()
                    if db_size_before and db_size_after:
                        self.stdout.write(f'  Database size after: {db_size_after}')

                        # Try to calculate savings (rough estimate)
                        try:
                            before_bytes = self._parse_size(db_size_before)
                            after_bytes = self._parse_size(db_size_after)
                            if before_bytes and after_bytes:
                                saved_bytes = before_bytes - after_bytes
                                if saved_bytes > 0:
                                    saved_mb = saved_bytes / (1024 * 1024)
                                    self.stdout.write(
                                        f'  Space saved: ~{saved_mb:.2f} MB'
                                    )
                        except Exception:
                            pass

                logger.info(
                    f'Token cleanup completed: deleted {deleted_outstanding} records '
                    f'(cutoff: {cutoff_date.isoformat()})'
                )

            # Recommendations
            if expired_count > 100000:
                self.stdout.write('')
                self.stdout.write(
                    self.style.WARNING(
                        '⚠️  Large number of expired tokens detected!'
                    )
                )
                self.stdout.write(
                    'Consider scheduling this cleanup more frequently (e.g., weekly)'
                )

        except ImportError as e:
            raise CommandError(
                f'Token blacklist models not found: {e}\n'
                'Ensure django-ninja-jwt token_blacklist is installed'
            )
        except Exception as e:
            logger.error(f'Token cleanup failed: {str(e)}')
            raise CommandError(f'Cleanup failed: {e}')

    def _get_table_size(self):
        """Get total size of token blacklist tables (PostgreSQL)"""
        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT pg_size_pretty(
                        pg_total_relation_size('token_blacklist_outstandingtoken') +
                        pg_total_relation_size('token_blacklist_blacklistedtoken')
                    );
                """)
                result = cursor.fetchone()
                return result[0] if result else None
        except Exception:
            # Not PostgreSQL or query failed
            return None

    def _parse_size(self, size_str):
        """Parse PostgreSQL size string to bytes (rough estimate)"""
        if not size_str:
            return None

        try:
            parts = size_str.strip().split()
            if len(parts) != 2:
                return None

            value = float(parts[0])
            unit = parts[1].upper()

            units = {
                'BYTES': 1,
                'KB': 1024,
                'MB': 1024 ** 2,
                'GB': 1024 ** 3,
                'TB': 1024 ** 4,
            }

            return int(value * units.get(unit, 1))
        except Exception:
            return None
