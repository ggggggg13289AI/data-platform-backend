"""
AI Models - Prompt templates, classification guidelines, and AI workflow features.

This module provides models for:
- PromptTemplate: Reusable prompt templates for AI interactions
- ClassificationGuideline: Version-controlled AI classification guidelines
- BatchAnalysisTask: Batch AI analysis job tracking
- ReviewTask: Physician review workflow management
- ReviewSample: Individual samples for review
- ReviewerAssignment: Reviewer assignment and progress tracking
- ReviewFeedback: Reviewer feedback on samples
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


class ClassificationGuideline(models.Model):
    """
    AI 分類指南模型 - 支援版本控制的醫師定義分類規則。

    醫師可定義分類指南（包含 prompt template 和 categories），
    並進行版本控制。每次修改會建立新版本，舊版本保留以供追溯。

    特性
    --------
    - Version control: 自動版本遞增和歷史追蹤
    - Status workflow: draft → testing → approved → archived
    - Template variables: 支援 {{content_raw}}, {{imaging_findings}}, {{impression}}
    - Category definition: 彈性定義分類類別列表
    """

    STATUS_DRAFT = "draft"
    STATUS_TESTING = "testing"
    STATUS_APPROVED = "approved"
    STATUS_ARCHIVED = "archived"

    STATUS_CHOICES = [
        (STATUS_DRAFT, "草稿"),
        (STATUS_TESTING, "測試中"),
        (STATUS_APPROVED, "已核准"),
        (STATUS_ARCHIVED, "已封存"),
    ]

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name="指南ID",
    )
    name = models.CharField(
        max_length=200,
        verbose_name="指南名稱",
        db_index=True,
    )
    description = models.TextField(
        blank=True,
        default="",
        verbose_name="描述",
    )
    prompt_template = models.TextField(
        verbose_name="Prompt 模板",
        help_text="支援變數: {{content_raw}}, {{imaging_findings}}, {{impression}}",
    )
    categories = models.JSONField(
        default=list,
        verbose_name="分類類別",
        help_text='分類標籤列表，例如: ["positive", "negative", "uncertain"]',
    )

    # Version control
    version = models.IntegerField(
        default=1,
        verbose_name="版本號",
    )
    parent_version = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="child_versions",
        verbose_name="父版本",
    )
    is_current = models.BooleanField(
        default=True,
        db_index=True,
        verbose_name="是否為當前版本",
    )

    # Status
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_DRAFT,
        db_index=True,
        verbose_name="狀態",
    )

    # Model configuration
    model_config = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="模型配置",
        help_text="LLM 參數配置，如 temperature, model_name 等",
    )

    # Audit fields
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.RESTRICT,
        related_name="created_guidelines",
        verbose_name="建立者",
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="建立時間",
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="更新時間",
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="approved_guidelines",
        verbose_name="核准者",
    )
    approved_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="核准時間",
    )

    class Meta:
        db_table = "ai_classification_guidelines"
        verbose_name = "分類指南"
        verbose_name_plural = "分類指南"
        ordering = ["-updated_at"]
        indexes = [
            models.Index(
                fields=["status", "-updated_at"],
                name="idx_guideline_status_updated",
            ),
            models.Index(
                fields=["is_current", "-version"],
                name="idx_guideline_current_version",
            ),
            models.Index(
                fields=["created_by", "-created_at"],
                name="idx_guideline_creator",
            ),
            models.Index(
                fields=["name", "is_current"],
                name="idx_guideline_name_current",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.name} v{self.version} ({self.get_status_display()})"

    def to_dict(self) -> dict:
        """轉換為字典格式（API 序列化）"""
        return {
            "id": str(self.id),
            "name": self.name,
            "description": self.description,
            "prompt_template": self.prompt_template,
            "categories": self.categories,
            "version": self.version,
            "parent_version_id": str(self.parent_version_id) if self.parent_version_id else None,
            "is_current": self.is_current,
            "status": self.status,
            "status_display": self.get_status_display(),
            "model_config": self.model_config,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "approved_at": self.approved_at.isoformat() if self.approved_at else None,
            "created_by": {
                "id": str(self.created_by.id),
                "name": self.created_by.get_full_name() or self.created_by.get_username(),
            },
            "approved_by": (
                {
                    "id": str(self.approved_by.id),
                    "name": self.approved_by.get_full_name() or self.approved_by.get_username(),
                }
                if self.approved_by
                else None
            ),
        }


class BatchAnalysisTask(models.Model):
    """
    批次 AI 分析任務模型。

    追蹤批次報告分析的狀態和進度。支援 100+ 報告的批次處理，
    透過 funboost 進行異步執行。

    狀態流程: pending → processing → completed/failed/cancelled
    """

    STATUS_PENDING = "pending"
    STATUS_PROCESSING = "processing"
    STATUS_COMPLETED = "completed"
    STATUS_FAILED = "failed"
    STATUS_CANCELLED = "cancelled"

    STATUS_CHOICES = [
        (STATUS_PENDING, "待處理"),
        (STATUS_PROCESSING, "處理中"),
        (STATUS_COMPLETED, "已完成"),
        (STATUS_FAILED, "失敗"),
        (STATUS_CANCELLED, "已取消"),
    ]

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name="任務ID",
    )
    guideline = models.ForeignKey(
        ClassificationGuideline,
        on_delete=models.PROTECT,
        related_name="batch_tasks",
        verbose_name="分類指南",
    )
    project = models.ForeignKey(
        "project.Project",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="batch_analysis_tasks",
        verbose_name="所屬專案",
    )

    # Report selection
    report_uids = models.JSONField(
        default=list,
        verbose_name="報告 UID 列表",
        help_text="要分析的報告 UID 陣列",
    )

    # Progress tracking
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
        db_index=True,
        verbose_name="狀態",
    )
    total_count = models.IntegerField(
        default=0,
        verbose_name="總數",
    )
    processed_count = models.IntegerField(
        default=0,
        verbose_name="已處理數",
    )
    success_count = models.IntegerField(
        default=0,
        verbose_name="成功數",
    )
    error_count = models.IntegerField(
        default=0,
        verbose_name="錯誤數",
    )

    # Funboost tracking
    funboost_task_id = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        db_index=True,
        verbose_name="Funboost 任務 ID",
    )

    # Results
    results_summary = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="結果摘要",
        help_text="各分類類別的統計計數",
    )
    error_details = models.JSONField(
        default=list,
        blank=True,
        verbose_name="錯誤詳情",
        help_text="失敗報告的錯誤資訊列表",
    )

    # Timestamps
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.RESTRICT,
        related_name="created_batch_tasks",
        verbose_name="建立者",
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="建立時間",
    )
    started_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="開始時間",
    )
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="完成時間",
    )

    class Meta:
        db_table = "ai_batch_analysis_tasks"
        verbose_name = "批次分析任務"
        verbose_name_plural = "批次分析任務"
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["status", "-created_at"],
                name="idx_batch_status_created",
            ),
            models.Index(
                fields=["guideline", "-created_at"],
                name="idx_batch_guideline_created",
            ),
            models.Index(
                fields=["created_by", "-created_at"],
                name="idx_batch_creator_created",
            ),
            models.Index(
                fields=["project", "-created_at"],
                name="idx_batch_project_created",
            ),
        ]

    def __str__(self) -> str:
        return f"BatchTask {self.id} - {self.status} ({self.processed_count}/{self.total_count})"

    def get_progress_percent(self) -> int:
        """計算處理進度百分比"""
        if self.total_count == 0:
            return 0
        return int((self.processed_count / self.total_count) * 100)

    def to_dict(self) -> dict:
        """轉換為字典格式（API 序列化）"""
        return {
            "id": str(self.id),
            "guideline_id": str(self.guideline_id),
            "guideline_name": self.guideline.name if self.guideline else None,
            "project_id": str(self.project_id) if self.project_id else None,
            "status": self.status,
            "status_display": self.get_status_display(),
            "total_count": self.total_count,
            "processed_count": self.processed_count,
            "success_count": self.success_count,
            "error_count": self.error_count,
            "progress_percent": self.get_progress_percent(),
            "results_summary": self.results_summary,
            "error_details": self.error_details,
            "funboost_task_id": self.funboost_task_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "created_by": {
                "id": str(self.created_by.id),
                "name": self.created_by.get_full_name() or self.created_by.get_username(),
            },
        }


class ReviewTask(models.Model):
    """
    醫師審核任務模型。

    管理 AI 分析結果的醫師審核工作流程，支援：
    - 單人審閱模式
    - 雙盲審閱模式（需要仲裁機制）
    - 多種抽樣策略（隨機、分層、信心度加權）
    """

    REVIEW_MODE_SINGLE = "single"
    REVIEW_MODE_DOUBLE_BLIND = "double_blind"

    REVIEW_MODE_CHOICES = [
        (REVIEW_MODE_SINGLE, "單人審閱"),
        (REVIEW_MODE_DOUBLE_BLIND, "雙盲審閱"),
    ]

    STATUS_PENDING = "pending"
    STATUS_IN_PROGRESS = "in_progress"
    STATUS_ARBITRATION = "arbitration"
    STATUS_COMPLETED = "completed"

    STATUS_CHOICES = [
        (STATUS_PENDING, "待處理"),
        (STATUS_IN_PROGRESS, "進行中"),
        (STATUS_ARBITRATION, "仲裁中"),
        (STATUS_COMPLETED, "已完成"),
    ]

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name="審核任務ID",
    )
    name = models.CharField(
        max_length=200,
        verbose_name="任務名稱",
    )
    batch_task = models.ForeignKey(
        BatchAnalysisTask,
        on_delete=models.CASCADE,
        related_name="review_tasks",
        verbose_name="批次分析任務",
    )

    # Sampling configuration
    sample_size = models.IntegerField(
        verbose_name="樣本數",
        help_text="要抽樣的報告數量",
    )
    sampling_config = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="抽樣配置",
        help_text="抽樣策略配置，如分層欄位、權重等",
    )

    # Review mode
    review_mode = models.CharField(
        max_length=20,
        choices=REVIEW_MODE_CHOICES,
        default=REVIEW_MODE_SINGLE,
        verbose_name="審核模式",
    )
    required_reviewers = models.IntegerField(
        default=1,
        verbose_name="所需審核者數",
    )

    # Thresholds
    fp_threshold = models.FloatField(
        default=0.20,
        verbose_name="FP 閾值",
        help_text="False Positive 比例閾值，超過則需要重新訓練",
    )

    # Status
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
        db_index=True,
        verbose_name="狀態",
    )

    # Cached results
    fp_rate = models.FloatField(
        null=True,
        blank=True,
        verbose_name="FP 率",
    )
    agreement_rate = models.FloatField(
        null=True,
        blank=True,
        verbose_name="一致性率",
        help_text="Cohen's Kappa 或其他一致性指標",
    )

    # Audit fields
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.RESTRICT,
        related_name="created_review_tasks",
        verbose_name="建立者",
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="建立時間",
    )
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="完成時間",
    )

    class Meta:
        db_table = "ai_review_tasks"
        verbose_name = "審核任務"
        verbose_name_plural = "審核任務"
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["status", "-created_at"],
                name="idx_review_status_created",
            ),
            models.Index(
                fields=["batch_task", "-created_at"],
                name="idx_review_batch_created",
            ),
            models.Index(
                fields=["created_by", "-created_at"],
                name="idx_review_creator_created",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.get_status_display()})"

    def to_dict(self) -> dict:
        """轉換為字典格式（API 序列化）"""
        return {
            "id": str(self.id),
            "name": self.name,
            "batch_task_id": str(self.batch_task_id),
            "sample_size": self.sample_size,
            "sampling_config": self.sampling_config,
            "review_mode": self.review_mode,
            "review_mode_display": self.get_review_mode_display(),
            "required_reviewers": self.required_reviewers,
            "fp_threshold": self.fp_threshold,
            "status": self.status,
            "status_display": self.get_status_display(),
            "fp_rate": self.fp_rate,
            "agreement_rate": self.agreement_rate,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "created_by": {
                "id": str(self.created_by.id),
                "name": self.created_by.get_full_name() or self.created_by.get_username(),
            },
        }


class ReviewSample(models.Model):
    """
    審核樣本模型。

    儲存從批次分析結果中抽樣出的個別報告，供醫師審核。
    包含抽樣時的 AI 分析快照，以便比較審核結果。
    """

    STATUS_PENDING = "pending"
    STATUS_NEEDS_SECOND_REVIEW = "needs_second_review"
    STATUS_IN_ARBITRATION = "in_arbitration"
    STATUS_COMPLETED = "completed"

    STATUS_CHOICES = [
        (STATUS_PENDING, "待審核"),
        (STATUS_NEEDS_SECOND_REVIEW, "需要第二審核"),
        (STATUS_IN_ARBITRATION, "仲裁中"),
        (STATUS_COMPLETED, "已完成"),
    ]

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name="樣本ID",
    )
    review_task = models.ForeignKey(
        ReviewTask,
        on_delete=models.CASCADE,
        related_name="samples",
        verbose_name="審核任務",
    )
    ai_annotation = models.ForeignKey(
        "report.AIAnnotation",
        on_delete=models.CASCADE,
        related_name="review_samples",
        verbose_name="AI 註解",
    )

    # Snapshot at sampling time
    stratum = models.CharField(
        max_length=100,
        blank=True,
        default="",
        verbose_name="分層標籤",
        help_text='抽樣時的分層標籤，如 "exam_source:CT"',
    )
    ai_classification = models.CharField(
        max_length=50,
        verbose_name="AI 分類結果",
        help_text="抽樣時的 AI 分類結果快照",
    )
    ai_confidence = models.FloatField(
        null=True,
        blank=True,
        verbose_name="AI 信心度",
        help_text="抽樣時的 AI 信心度分數 (0.0-1.0)",
    )

    # Status
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
        db_index=True,
        verbose_name="狀態",
    )

    # Final determination
    final_is_correct = models.BooleanField(
        null=True,
        blank=True,
        verbose_name="最終判定是否正確",
    )
    final_correct_category = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        verbose_name="最終正確分類",
        help_text="若 AI 分類錯誤，此欄位記錄正確分類",
    )
    final_determined_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="determined_samples",
        verbose_name="最終判定者",
    )

    class Meta:
        db_table = "ai_review_samples"
        verbose_name = "審核樣本"
        verbose_name_plural = "審核樣本"
        ordering = ["review_task", "stratum"]
        indexes = [
            models.Index(
                fields=["review_task", "status"],
                name="idx_sample_task_status",
            ),
            models.Index(
                fields=["ai_annotation"],
                name="idx_sample_annotation",
            ),
            models.Index(
                fields=["stratum"],
                name="idx_sample_stratum",
            ),
        ]

    def __str__(self) -> str:
        return f"Sample {self.id} - {self.ai_classification} ({self.get_status_display()})"

    def to_dict(self) -> dict:
        """轉換為字典格式（API 序列化）"""
        return {
            "id": str(self.id),
            "review_task_id": str(self.review_task_id),
            "ai_annotation_id": str(self.ai_annotation_id),
            "stratum": self.stratum,
            "ai_classification": self.ai_classification,
            "ai_confidence": self.ai_confidence,
            "status": self.status,
            "status_display": self.get_status_display(),
            "final_is_correct": self.final_is_correct,
            "final_correct_category": self.final_correct_category,
            "final_determined_by": (
                {
                    "id": str(self.final_determined_by.id),
                    "name": (
                        self.final_determined_by.get_full_name()
                        or self.final_determined_by.get_username()
                    ),
                }
                if self.final_determined_by
                else None
            ),
        }


class ReviewerAssignment(models.Model):
    """
    審核者分配模型。

    追蹤審核者在審核任務中的角色和進度。
    支援主審、副審和仲裁者角色。
    """

    ROLE_PRIMARY = "primary"
    ROLE_SECONDARY = "secondary"
    ROLE_ARBITRATOR = "arbitrator"

    ROLE_CHOICES = [
        (ROLE_PRIMARY, "主審"),
        (ROLE_SECONDARY, "副審"),
        (ROLE_ARBITRATOR, "仲裁者"),
    ]

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name="分配ID",
    )
    review_task = models.ForeignKey(
        ReviewTask,
        on_delete=models.CASCADE,
        related_name="assignments",
        verbose_name="審核任務",
    )
    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="review_assignments",
        verbose_name="審核者",
    )
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default=ROLE_PRIMARY,
        verbose_name="角色",
    )

    # Progress tracking
    completed_samples = models.IntegerField(
        default=0,
        verbose_name="已完成樣本數",
    )
    total_assigned = models.IntegerField(
        default=0,
        verbose_name="分配樣本總數",
    )

    # Double-blind control
    can_view_others = models.BooleanField(
        default=False,
        verbose_name="可查看其他審核者結果",
        help_text="雙盲模式下應設為 False",
    )

    # Timestamps
    assigned_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="分配時間",
    )

    class Meta:
        db_table = "ai_reviewer_assignments"
        verbose_name = "審核者分配"
        verbose_name_plural = "審核者分配"
        unique_together = [["review_task", "reviewer"]]
        ordering = ["review_task", "role"]
        indexes = [
            models.Index(
                fields=["review_task", "role"],
                name="idx_assignment_task_role",
            ),
            models.Index(
                fields=["reviewer"],
                name="idx_assignment_reviewer",
            ),
        ]

    def __str__(self) -> str:
        reviewer_name = self.reviewer.get_full_name() or self.reviewer.get_username()
        return f"{reviewer_name} - {self.get_role_display()} ({self.completed_samples}/{self.total_assigned})"

    def get_progress_percent(self) -> int:
        """計算審核進度百分比"""
        if self.total_assigned == 0:
            return 0
        return int((self.completed_samples / self.total_assigned) * 100)

    def to_dict(self) -> dict:
        """轉換為字典格式（API 序列化）"""
        return {
            "id": str(self.id),
            "review_task_id": str(self.review_task_id),
            "reviewer": {
                "id": str(self.reviewer.id),
                "name": self.reviewer.get_full_name() or self.reviewer.get_username(),
                "email": self.reviewer.email,
            },
            "role": self.role,
            "role_display": self.get_role_display(),
            "completed_samples": self.completed_samples,
            "total_assigned": self.total_assigned,
            "progress_percent": self.get_progress_percent(),
            "can_view_others": self.can_view_others,
            "assigned_at": self.assigned_at.isoformat() if self.assigned_at else None,
        }


class ReviewFeedback(models.Model):
    """
    審核回饋模型。

    儲存審核者對單一樣本的審核意見。
    每個審核者對每個樣本只能提交一次回饋。
    """

    CONFIDENCE_HIGH = "high"
    CONFIDENCE_MEDIUM = "medium"
    CONFIDENCE_LOW = "low"

    CONFIDENCE_CHOICES = [
        (CONFIDENCE_HIGH, "高"),
        (CONFIDENCE_MEDIUM, "中"),
        (CONFIDENCE_LOW, "低"),
    ]

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name="回饋ID",
    )
    review_sample = models.ForeignKey(
        ReviewSample,
        on_delete=models.CASCADE,
        related_name="feedbacks",
        verbose_name="審核樣本",
    )
    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.RESTRICT,
        related_name="review_feedbacks",
        verbose_name="審核者",
    )
    reviewer_assignment = models.ForeignKey(
        ReviewerAssignment,
        on_delete=models.CASCADE,
        related_name="feedbacks",
        verbose_name="審核者分配",
    )

    # Feedback content
    is_correct = models.BooleanField(
        verbose_name="AI 分類是否正確",
    )
    correct_category = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        verbose_name="正確分類",
        help_text="若 AI 分類錯誤，此欄位記錄正確分類",
    )
    confidence_level = models.CharField(
        max_length=20,
        choices=CONFIDENCE_CHOICES,
        default=CONFIDENCE_HIGH,
        verbose_name="信心程度",
    )
    notes = models.TextField(
        blank=True,
        default="",
        verbose_name="備註",
    )

    # Timestamps
    submitted_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="提交時間",
    )

    class Meta:
        db_table = "ai_review_feedbacks"
        verbose_name = "審核回饋"
        verbose_name_plural = "審核回饋"
        unique_together = [["review_sample", "reviewer"]]
        ordering = ["-submitted_at"]
        indexes = [
            models.Index(
                fields=["review_sample", "reviewer"],
                name="idx_feedback_sample_reviewer",
            ),
            models.Index(
                fields=["reviewer_assignment"],
                name="idx_feedback_assignment",
            ),
            models.Index(
                fields=["is_correct"],
                name="idx_feedback_is_correct",
            ),
        ]

    def __str__(self) -> str:
        reviewer_name = self.reviewer.get_full_name() or self.reviewer.get_username()
        result = "正確" if self.is_correct else "錯誤"
        return f"{reviewer_name} - {result}"

    def to_dict(self) -> dict:
        """轉換為字典格式（API 序列化）"""
        return {
            "id": str(self.id),
            "review_sample_id": str(self.review_sample_id),
            "reviewer": {
                "id": str(self.reviewer.id),
                "name": self.reviewer.get_full_name() or self.reviewer.get_username(),
            },
            "is_correct": self.is_correct,
            "correct_category": self.correct_category,
            "confidence_level": self.confidence_level,
            "confidence_level_display": self.get_confidence_level_display(),
            "notes": self.notes,
            "submitted_at": self.submitted_at.isoformat() if self.submitted_at else None,
        }
