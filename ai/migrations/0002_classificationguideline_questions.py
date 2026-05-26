# Generated manually - adds questions JSONField to ClassificationGuideline

from django.db import migrations


def column_exists(connection, table_name, column_name):
    """Check if a column exists in the database."""
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT EXISTS (
                SELECT FROM information_schema.columns
                WHERE table_schema = 'public'
                AND table_name = %s AND column_name = %s
            )
        """,
            [table_name, column_name],
        )
        return cursor.fetchone()[0]


def add_questions_column(apps, schema_editor):
    """Conditionally add questions column."""
    connection = schema_editor.connection
    if not column_exists(connection, "ai_classification_guidelines", "questions"):
        with connection.cursor() as cursor:
            cursor.execute(
                """
                ALTER TABLE ai_classification_guidelines
                ADD COLUMN questions jsonb DEFAULT '[]'::jsonb NOT NULL
            """
            )


class Migration(migrations.Migration):
    dependencies = [
        ("ai", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(add_questions_column, migrations.RunPython.noop),
    ]
