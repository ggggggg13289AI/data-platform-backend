"""
AI Models - Prompt templates and AI assistant features.
"""

import uuid

from django.conf import settings
from django.db import models


class PromptTemplate(models.Model):
    """提示詞模板模型"""

    # 分類選項
    CATEGORY_REPORT_ANALYSIS = "report_analysis"
    CATEGORY_EXAM_QUERY = "exam_query"
    CATEGORY_TERM_EXPLANATION = "term_explanation"
    CATEGORY_DATA_EXTRACTION = "data_extraction"
    CATEGORY_SEVERITY_ASSESSMENT = "severity_assessment"
    CATEGORY_GENERAL = "general"

    CATEGORY_CHOICES = [
        (CATEGORY_REPORT_ANALYSIS, "報告分析"),
        (CATEGORY_EXAM_QUERY, "檢查查詢"),
        (CATEGORY_TERM_EXPLANATION, "術語解釋"),
        (CATEGORY_DATA_EXTRACTION, "數據提取"),
        (CATEGORY_SEVERITY_ASSESSMENT, "嚴重程度評估"),
        (CATEGORY_GENERAL, "一般"),
    ]

    # 使用案例選項
    USE_CASE_REPORT_ANALYSIS = "report_analysis"
    USE_CASE_EXAM_QUERY = "exam_query"
    USE_CASE_TERM_EXPLANATION = "term_explanation"
    USE_CASE_DATA_EXTRACTION = "data_extraction"
    USE_CASE_SEVERITY_ASSESSMENT = "severity_assessment"
    USE_CASE_GENERAL = "general"

    USE_CASE_CHOICES = [
        (USE_CASE_REPORT_ANALYSIS, "報告分析"),
        (USE_CASE_EXAM_QUERY, "檢查查詢"),
        (USE_CASE_TERM_EXPLANATION, "術語解釋"),
        (USE_CASE_DATA_EXTRACTION, "數據提取"),
        (USE_CASE_SEVERITY_ASSESSMENT, "嚴重程度評估"),
        (USE_CASE_GENERAL, "一般"),
    ]

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name="模板ID",
    )
    name = models.CharField(
        max_length=200,
        verbose_name="模板名稱",
        db_index=True,
    )
    content = models.TextField(
        verbose_name="模板內容",
    )
    category = models.CharField(
        max_length=50,
        choices=CATEGORY_CHOICES,
        default=CATEGORY_GENERAL,
        verbose_name="分類",
        db_index=True,
    )
    use_case = models.CharField(
        max_length=50,
        choices=USE_CASE_CHOICES,
        default=USE_CASE_GENERAL,
        verbose_name="使用案例",
        db_index=True,
    )
    description = models.TextField(
        blank=True,
        default="",
        verbose_name="描述",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.RESTRICT,
        related_name="created_prompt_templates",
        verbose_name="創建者",
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="創建時間",
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="更新時間",
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name="是否啟用",
        db_index=True,
    )

    class Meta:
        db_table = "prompt_templates"
        verbose_name = "提示詞模板"
        verbose_name_plural = "提示詞模板"
        ordering = ["-updated_at"]
        indexes = [
            models.Index(
                fields=["category", "-updated_at"],
                name="idx_pt_category_updated",
            ),
            models.Index(
                fields=["use_case", "-updated_at"],
                name="idx_pt_usecase_updated",
            ),
            models.Index(
                fields=["created_by", "-created_at"],
                name="idx_pt_creator_created",
            ),
            models.Index(
                fields=["is_active", "-updated_at"],
                name="idx_pt_active_updated",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.get_category_display()})"

    def to_dict(self) -> dict:
        """轉換為字典格式（API 序列化）"""
        return {
            "id": str(self.id),
            "name": self.name,
            "content": self.content,
            "category": self.category,
            "category_display": self.get_category_display(),
            "use_case": self.use_case,
            "use_case_display": self.get_use_case_display(),
            "description": self.description,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "created_by": {
                "id": str(self.created_by.id),
                "name": self.created_by.get_full_name() or self.created_by.get_username(),
                "email": self.created_by.email,
            },
            "is_active": self.is_active,
        }
