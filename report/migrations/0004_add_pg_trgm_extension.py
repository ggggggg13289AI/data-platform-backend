# Generated manually for imaging regex search feature
# Migration: Add pg_trgm extension for trigram-based search

from django.db import migrations


class Migration(migrations.Migration):
    """
    Enable pg_trgm extension for trigram-based pattern matching.
    This extension is required for GIN indexes on regex/ILIKE queries.

    Requirements:
    - PostgreSQL 9.1+ (pg_trgm included)
    - Database superuser or pg_trgm already available
    """

    dependencies = [
        ('report', '0003_populate_search_vector'),
    ]

    operations = [
        migrations.RunSQL(
            sql="CREATE EXTENSION IF NOT EXISTS pg_trgm;",
            reverse_sql="DROP EXTENSION IF EXISTS pg_trgm;",
        ),
    ]
