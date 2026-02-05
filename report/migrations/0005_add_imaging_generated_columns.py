# Generated manually for imaging regex search feature
# Migration: Add generated columns for imaging_findings and impression
# Modified: Added conditional column creation to handle partial database state

from django.db import migrations


def column_exists(connection, table_name, column_name):
    """Check if a column exists in a table."""
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.columns
                WHERE table_schema = 'public'
                AND table_name = %s
                AND column_name = %s
            )
        """, [table_name, column_name])
        return cursor.fetchone()[0]


def add_imaging_findings_if_not_exists(apps, schema_editor):
    """Add imaging_findings column if it doesn't exist."""
    if not column_exists(schema_editor.connection, 'one_page_text_report_v2', 'imaging_findings'):
        schema_editor.execute("""
            ALTER TABLE one_page_text_report_v2
            ADD COLUMN imaging_findings TEXT GENERATED ALWAYS AS (
                CASE
                    WHEN content_raw ~* 'Imaging findings\\s?:'
                    THEN TRIM(substring(content_raw FROM '(?i).*Imaging findings\\s?:\\s*(.*)'))
                    ELSE NULL
                END
            ) STORED;
        """)


def add_impression_if_not_exists(apps, schema_editor):
    """Add impression column if it doesn't exist."""
    if not column_exists(schema_editor.connection, 'one_page_text_report_v2', 'impression'):
        schema_editor.execute("""
            ALTER TABLE one_page_text_report_v2
            ADD COLUMN impression TEXT GENERATED ALWAYS AS (
                CASE
                    WHEN content_raw ~* '(impression\\s?:?|imp:?|conclusion\\s?:?)'
                    THEN TRIM(substring(content_raw FROM '(?i).*(impression\\s?:|imp:|conclusion:)\\s*(.*)$'))
                    ELSE NULL
                END
            ) STORED;
        """)


def remove_imaging_findings(apps, schema_editor):
    """Remove imaging_findings column."""
    schema_editor.execute("""
        ALTER TABLE one_page_text_report_v2
        DROP COLUMN IF EXISTS imaging_findings;
    """)


def remove_impression(apps, schema_editor):
    """Remove impression column."""
    schema_editor.execute("""
        ALTER TABLE one_page_text_report_v2
        DROP COLUMN IF EXISTS impression;
    """)


class Migration(migrations.Migration):
    """
    Add PostgreSQL GENERATED ALWAYS AS columns to extract imaging report sections.

    These columns automatically parse content_raw to extract:
    - imaging_findings: Content after "Imaging findings:" section
    - impression: Content after "Impression:", "Imp:", or "Conclusion:" section

    Requirements:
    - PostgreSQL 12+ (for GENERATED ALWAYS AS ... STORED)
    """

    dependencies = [
        ("report", "0004_add_pg_trgm_extension"),
    ]

    operations = [
        migrations.RunPython(add_imaging_findings_if_not_exists, remove_imaging_findings),
        migrations.RunPython(add_impression_if_not_exists, remove_impression),
    ]
