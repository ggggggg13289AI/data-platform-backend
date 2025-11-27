from django.apps import AppConfig


class ReportConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'report'
    verbose_name = 'report'  # Medical Studies

    def ready(self) -> None:
        # Import signals to keep search_vector in sync
        import report.signals  # noqa: F401