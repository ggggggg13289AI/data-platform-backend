"""
Django migration: 使用 regexp_matches 改進 imaging_findings 和 impression 的 generated column

改進內容：
- 使用 regexp_matches 取代 substring，支援更精確的模式匹配
- imaging_findings: 支援 "Imaging finding" 和 "Imaging findings" (單複數)
- impression: 支援 "Impression/Impressions", "Conclusion/Conclusions", "Imp"
- 輸出包含標籤和內容 (e.g., "Impression: No acute findings")

實作方式：
- 建立 IMMUTABLE 函數來封裝 regexp_matches 邏輯
- GENERATED column 調用這些函數

路徑: backend_django/report/migrations/0008_improve_generated_columns_with_functions.py
"""

from django.db import migrations


class Migration(migrations.Migration):
    """
    使用自定義函數改進 generated columns。

    PostgreSQL GENERATED columns 不支援 subquery 和 set-returning functions，
    但可以調用 IMMUTABLE 函數。因此我們：
    1. 建立 extract_imaging_findings() 和 extract_impression() 函數
    2. 在 GENERATED column 中調用這些函數
    """

    dependencies = [
        ('report', '0007_add_imaging_fields_to_model_state'),
    ]

    operations = [
        # Step 1: 建立提取函數
        migrations.RunSQL(
            sql="""
                -- ===== 建立 extract_imaging_findings 函數 =====
                CREATE OR REPLACE FUNCTION extract_imaging_findings(content text)
                RETURNS text AS $$
                SELECT TRIM(concat(m[1], m[2]))
                FROM regexp_matches(
                    content,
                    '(?i)(imaging\\s+findings?)(.+?)(?=\\n|$)',
                    'g'
                ) AS m
                LIMIT 1;
                $$ LANGUAGE SQL IMMUTABLE STRICT;

                COMMENT ON FUNCTION extract_imaging_findings(text) IS
                    '從報告內容提取 Imaging finding(s) 區塊，支援單複數形式';

                -- ===== 建立 extract_impression 函數 =====
                CREATE OR REPLACE FUNCTION extract_impression(content text)
                RETURNS text AS $$
                SELECT TRIM(concat(m[1], m[2]))
                FROM regexp_matches(
                    content,
                    '(?i)(impressions?|imp|conclusions?)(.+?)(?=\\n|$)',
                    'g'
                ) AS m
                LIMIT 1;
                $$ LANGUAGE SQL IMMUTABLE STRICT;

                COMMENT ON FUNCTION extract_impression(text) IS
                    '從報告內容提取 Impression/Imp/Conclusion 區塊，支援單複數形式';
            """,
            reverse_sql="""
                DROP FUNCTION IF EXISTS extract_imaging_findings(text);
                DROP FUNCTION IF EXISTS extract_impression(text);
            """,
        ),

        # Step 2: 重建 GENERATED columns 使用新函數
        migrations.RunSQL(
            sql="""
                -- ===== 重建 imaging_findings column =====
                ALTER TABLE one_page_text_report_v2
                DROP COLUMN IF EXISTS imaging_findings;

                ALTER TABLE one_page_text_report_v2
                ADD COLUMN imaging_findings TEXT GENERATED ALWAYS AS (
                    extract_imaging_findings(content_raw)
                ) STORED;

                -- ===== 重建 impression column =====
                ALTER TABLE one_page_text_report_v2
                DROP COLUMN IF EXISTS impression;

                ALTER TABLE one_page_text_report_v2
                ADD COLUMN impression TEXT GENERATED ALWAYS AS (
                    extract_impression(content_raw)
                ) STORED;
            """,
            reverse_sql="""
                -- 回滾到 migration 0005 的原始 substring 定義
                ALTER TABLE one_page_text_report_v2
                DROP COLUMN IF EXISTS imaging_findings;

                ALTER TABLE one_page_text_report_v2
                ADD COLUMN imaging_findings TEXT GENERATED ALWAYS AS (
                    CASE
                        WHEN content_raw ~* 'Imaging findings\\s?:'
                        THEN TRIM(substring(content_raw FROM '(?i).*Imaging findings\\s?:\\s*(.*)'))
                        ELSE NULL
                    END
                ) STORED;

                ALTER TABLE one_page_text_report_v2
                DROP COLUMN IF EXISTS impression;

                ALTER TABLE one_page_text_report_v2
                ADD COLUMN impression TEXT GENERATED ALWAYS AS (
                    CASE
                        WHEN content_raw ~* '(impression\\s?:?|imp:?|conclusion:?)'
                        THEN TRIM(substring(content_raw FROM '(?i).*(impression\\s?:|imp:|conclusion:)\\s*(.*)$'))
                        ELSE NULL
                    END
                ) STORED;
            """,
        ),
    ]
