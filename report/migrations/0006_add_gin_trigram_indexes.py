# Generated manually for imaging regex search feature
# Migration: Add GIN trigram indexes for fast regex/ILIKE search

from django.db import migrations


class Migration(migrations.Migration):
    """
    Add GIN trigram indexes to support fast pattern matching queries.

    pg_trgm GIN indexes support:
    - ILIKE '%pattern%' queries
    - Regex queries with ~* and ~ operators

    Performance characteristics:
    - Index size: approximately 2-3x the column data size
    - Query performance: O(log n) vs O(n) full table scan
    - Update cost: moderate (recomputes trigrams on insert/update)

    Using CONCURRENTLY to avoid locking the table during index creation.
    Note: CONCURRENTLY cannot be used inside a transaction, so Django
    may need to handle this specially in some deployment scenarios.
    """

    dependencies = [
        ("report", "0005_add_imaging_generated_columns"),
    ]

    # Set atomic = False to allow CREATE INDEX CONCURRENTLY
    atomic = False

    operations = [
        # GIN trigram index on content_raw for full-text regex search
        migrations.RunSQL(
            sql="""
                CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_content_raw_trgm
                ON one_page_text_report_v2
                USING GIN (content_raw gin_trgm_ops);
            """,
            reverse_sql="""
                DROP INDEX CONCURRENTLY IF EXISTS idx_content_raw_trgm;
            """,
        ),
        # GIN trigram index on imaging_findings
        migrations.RunSQL(
            sql="""
                CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_imaging_findings_trgm
                ON one_page_text_report_v2
                USING GIN (imaging_findings gin_trgm_ops);
            """,
            reverse_sql="""
                DROP INDEX CONCURRENTLY IF EXISTS idx_imaging_findings_trgm;
            """,
        ),
        # GIN trigram index on impression
        migrations.RunSQL(
            sql="""
                CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_impression_trgm
                ON one_page_text_report_v2
                USING GIN (impression gin_trgm_ops);
            """,
            reverse_sql="""
                DROP INDEX CONCURRENTLY IF EXISTS idx_impression_trgm;
            """,
        ),
    ]
