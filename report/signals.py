"""
Signal handlers for report app.
"""

from __future__ import annotations

import logging

from django.contrib.postgres.search import SearchVector
from django.db import connection
from django.db.models.signals import post_save
from django.dispatch import receiver

from report.models import Report

logger = logging.getLogger(__name__)

SEARCH_VECTOR_EXPRESSION = (
    SearchVector('title', weight='A', config='simple')
    + SearchVector('content_processed', weight='B', config='simple')
    + SearchVector('report_id', weight='C', config='simple')
    + SearchVector('uid', weight='C', config='simple')
)


@receiver(post_save, sender=Report)
def refresh_search_vector(sender, instance: Report, **kwargs):
    """
    Keep the persisted search_vector column in sync after report changes.

    Uses database-level SearchVector expression so Postgres can utilize the GIN index.
    """
    if connection.vendor != 'postgresql':
        return

    try:
        Report.objects.filter(pk=instance.pk).update(search_vector=SEARCH_VECTOR_EXPRESSION)
    except Exception as exc:  # pragma: no cover - defensive logging
        logger.warning('Failed to update search_vector for %s: %s', instance.pk, exc)

