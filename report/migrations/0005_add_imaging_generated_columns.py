# Generated manually for imaging regex search feature
# Migration: Add generated columns for imaging_findings and impression

from django.db import migrations


class Migration(migrations.Migration):
    """
    Add PostgreSQL GENERATED ALWAYS AS columns to extract imaging report sections.

    These columns automatically parse content_raw to extract:
    - imaging_findings: Content after "Imaging findings:" section
    - impression: Content after "Impression:", "Imp:", or "Conclusion:" section

    The regex patterns are designed to match the Python extraction logic:
    - pattern_impression_str = re.compile(r'(?i:impression\\s?:?|imp:?|conclusion:?)')
    - pattern_Imaging_findings_str = re.compile(r'(Imaging findings :)')

    Both use split()[-1] behavior, which we simulate using greedy .* matching
    to find the LAST occurrence of the pattern.

    Requirements:
    - PostgreSQL 12+ (for GENERATED ALWAYS AS ... STORED)
    """

    dependencies = [
        ("report", "0004_add_pg_trgm_extension"),
    ]

    operations = [
        # Add imaging_findings column
        # Extracts content after "Imaging findings:" (case-insensitive)
        # Uses greedy .* to match the LAST occurrence (simulates Python split()[-1])
        migrations.RunSQL(
            sql="""
                ALTER TABLE one_page_text_report_v2
                ADD COLUMN imaging_findings TEXT GENERATED ALWAYS AS (
                    CASE
                        WHEN content_raw ~* 'Imaging findings\\s?:'
                        THEN TRIM(substring(content_raw FROM '(?i).*Imaging findings\\s?:\\s*(.*)'))
                        ELSE NULL
                    END
                ) STORED;
            """,
            reverse_sql="""
                ALTER TABLE one_page_text_report_v2
                DROP COLUMN IF EXISTS imaging_findings;
            """,
        ),
        # Add impression column
        # Extracts content after "Impression:", "Imp:", or "Conclusion:" (case-insensitive)
        # Uses greedy .* to match the LAST occurrence (simulates Python split()[-1])
        migrations.RunSQL(
            sql="""
                ALTER TABLE one_page_text_report_v2
                ADD COLUMN impression TEXT GENERATED ALWAYS AS (
                    CASE
                        WHEN content_raw ~* '(impression\\s?:?|imp:?|conclusion\\s?:?)'
                        THEN TRIM(substring(content_raw FROM '(?i).*(impression\\s?:|imp:|conclusion:)\\s*(.*)$'))
                        ELSE NULL
                    END
                ) STORED;
            """,
            reverse_sql="""
                ALTER TABLE one_page_text_report_v2
                DROP COLUMN IF EXISTS impression;
            """,
        ),
    ]
