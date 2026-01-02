from django.contrib.postgres.search import SearchVector
from django.db import migrations


def populate_search_vector(apps, schema_editor):
    Study = apps.get_model('study', 'Study')
    vector = (
        SearchVector('patient_name', weight='A', config='simple')
        + SearchVector('exam_description', weight='B', config='simple')
        + SearchVector('exam_item', weight='B', config='simple')
        + SearchVector('medical_record_no', weight='C', config='simple')
        + SearchVector('certified_physician', weight='C', config='simple')
    )
    Study.objects.all().update(search_vector=vector)


def reset_search_vector(apps, schema_editor):
    Study = apps.get_model('study', 'Study')
    Study.objects.all().update(search_vector=None)


class Migration(migrations.Migration):

    dependencies = [
        ('study', '0002_study_search_vector_and_more'),
    ]

    operations = [
        migrations.RunPython(populate_search_vector, reverse_code=reset_search_vector),
    ]


