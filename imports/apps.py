"""Django app configuration for imports module."""

from django.apps import AppConfig


class ImportsConfig(AppConfig):
    """Configuration for the imports application."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "imports"
    verbose_name = "Data Import"
