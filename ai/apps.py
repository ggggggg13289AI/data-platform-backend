"""
AI App Config
"""

from django.apps import AppConfig


class AiConfig(AppConfig):
    """AI 應用配置"""

    default_auto_field = "django.db.models.BigAutoField"
    name = "ai"
    verbose_name = "AI 助手"
