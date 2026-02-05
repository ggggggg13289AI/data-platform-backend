"""
AI Schemas - Pydantic schemas for prompt templates API.
"""

from datetime import datetime

from ninja import Schema

from ai.models import PromptTemplate


class UserInfo(Schema):
    """用戶資訊"""

    id: str
    name: str
    email: str | None = None


class PromptTemplateListItem(Schema):
    """提示詞模板列表項"""

    id: str
    name: str
    content: str
    category: str
    category_display: str
    use_case: str
    use_case_display: str
    description: str
    created_at: datetime
    updated_at: datetime
    created_by: UserInfo
    is_active: bool

    @classmethod
    def from_model(cls, template: PromptTemplate) -> "PromptTemplateListItem":
        """從模型創建"""
        return cls(
            id=str(template.id),
            name=template.name,
            content=template.content,
            category=template.category,
            category_display=template.get_category_display(),
            use_case=template.use_case,
            use_case_display=template.get_use_case_display(),
            description=template.description,
            created_at=template.created_at,
            updated_at=template.updated_at,
            created_by=UserInfo(
                id=str(template.created_by.id),
                name=template.created_by.get_full_name() or template.created_by.get_username(),
                email=template.created_by.email,
            ),
            is_active=template.is_active,
        )


class PromptTemplateDetailResponse(Schema):
    """提示詞模板詳情響應"""

    id: str
    name: str
    content: str
    category: str
    category_display: str
    use_case: str
    use_case_display: str
    description: str
    created_at: datetime
    updated_at: datetime
    created_by: UserInfo
    is_active: bool

    @classmethod
    def from_model(cls, template: PromptTemplate) -> "PromptTemplateDetailResponse":
        """從模型創建"""
        return cls(
            id=str(template.id),
            name=template.name,
            content=template.content,
            category=template.category,
            category_display=template.get_category_display(),
            use_case=template.use_case,
            use_case_display=template.get_use_case_display(),
            description=template.description,
            created_at=template.created_at,
            updated_at=template.updated_at,
            created_by=UserInfo(
                id=str(template.created_by.id),
                name=template.created_by.get_full_name() or template.created_by.get_username(),
                email=template.created_by.email,
            ),
            is_active=template.is_active,
        )


class CreatePromptTemplateRequest(Schema):
    """創建提示詞模板請求"""

    name: str
    content: str
    category: str = PromptTemplate.CATEGORY_GENERAL
    use_case: str = PromptTemplate.USE_CASE_GENERAL
    description: str = ""


class UpdatePromptTemplateRequest(Schema):
    """更新提示詞模板請求"""

    name: str | None = None
    content: str | None = None
    category: str | None = None
    use_case: str | None = None
    description: str | None = None
    is_active: bool | None = None


# ============================================================================
# Chat Schemas
# ============================================================================


class ChatMessage(Schema):
    """聊天訊息"""

    role: str  # user, assistant, system
    content: str


class QuickChatRequest(Schema):
    """快速聊天請求"""

    message: str
    system_prompt: str | None = None
    temperature: float | None = None


class QuickChatResponse(Schema):
    """快速聊天響應"""

    content: str
    model: str
    latency_ms: int
    tokens_used: int | None = None


class ConversationChatRequest(Schema):
    """對話聊天請求"""

    message: str
    conversation_history: list[ChatMessage] = []
    context: dict | None = None
    temperature: float | None = None


class ConversationChatResponse(Schema):
    """對話聊天響應"""

    content: str
    model: str
    latency_ms: int
    tokens_used: int | None = None


# ============================================================================
# Health Check Schemas
# ============================================================================


class AIHealthResponse(Schema):
    """AI 服務健康檢查響應"""

    status: str
    provider: str
    base_url: str
    model: str | None = None
    model_available: bool | None = None
    available_models: list[str] | None = None
    error: str | None = None


# ============================================================================
# Analysis Schemas
# ============================================================================


class SingleAnalysisRequest(Schema):
    """單一報告分析請求"""

    report_uid: str
    user_prompt: str
    annotation_type: str = "general"  # highlight, classification, extraction, scoring, general
    temperature: float = 0.7


class SingleAnalysisResponse(Schema):
    """單一報告分析響應"""

    report_uid: str
    analysis_content: str
    annotation_type: str
    model: str
    latency_ms: int
    tokens_used: int | None = None


class BatchAnalysisRequest(Schema):
    """批次分析請求"""

    report_ids: list[str]
    user_prompt: str
    annotation_type: str = "general"
    temperature: float = 0.7


class BatchAnalysisResponse(Schema):
    """批次分析響應"""

    status: str  # queued, processing, completed, failed
    message: str
    report_count: int
    task_id: str | None = None


# ============================================================================
# Classification Guideline Schemas
# ============================================================================


class GuidelineListItem(Schema):
    """分類指南列表項"""

    id: str
    name: str
    description: str
    version: int
    is_current: bool
    status: str
    status_display: str
    categories: list[str]
    created_at: datetime
    updated_at: datetime
    created_by: UserInfo


class GuidelineDetailResponse(Schema):
    """分類指南詳情響應"""

    id: str
    name: str
    description: str
    prompt_template: str
    categories: list[str]
    version: int
    parent_version_id: str | None = None
    is_current: bool
    status: str
    status_display: str
    llm_config: dict
    created_at: datetime
    updated_at: datetime
    approved_at: datetime | None = None
    created_by: UserInfo
    approved_by: UserInfo | None = None


class CreateGuidelineRequest(Schema):
    """建立分類指南請求"""

    name: str
    prompt_template: str
    categories: list[str]
    description: str = ""
    llm_config: dict | None = None


class UpdateGuidelineRequest(Schema):
    """更新分類指南請求"""

    name: str | None = None
    description: str | None = None
    prompt_template: str | None = None
    categories: list[str] | None = None
    llm_config: dict | None = None


class CreateGuidelineVersionRequest(Schema):
    """建立新版本請求"""

    prompt_template: str | None = None
    categories: list[str] | None = None
    llm_config: dict | None = None


class GuidelineVersionItem(Schema):
    """指南版本列表項"""

    id: str
    version: int
    is_current: bool
    status: str
    created_at: datetime
    created_by: UserInfo


class TestGuidelineRequest(Schema):
    """測試分類指南請求"""

    report_uids: list[str]


class TestGuidelineResponse(Schema):
    """測試分類指南響應"""

    guideline_id: str
    test_count: int
    results: list[dict]


# ============================================================================
# Batch Analysis Task Schemas
# ============================================================================


class CreateBatchAnalysisRequest(Schema):
    """建立批次分析請求"""

    guideline_id: str
    report_uids: list[str]
    project_id: str | None = None


class BatchAnalysisTaskResponse(Schema):
    """批次分析任務響應"""

    id: str
    guideline_id: str
    guideline_name: str | None = None
    project_id: str | None = None
    status: str
    status_display: str
    total_count: int
    processed_count: int
    success_count: int
    error_count: int
    progress_percent: int
    results_summary: dict
    error_details: list[dict]
    funboost_task_id: str | None = None
    created_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_by: UserInfo


class BatchAnalysisResultItem(Schema):
    """批次分析結果項"""

    annotation_id: str
    report_uid: str
    classification: str
    confidence_score: float | None = None
    created_at: datetime


# ============================================================================
# Review Task Schemas
# ============================================================================


class SamplingConfigSchema(Schema):
    """抽樣配置 Schema"""

    strategy: str = "random"  # random, stratified, confidence_weighted
    strata_fields: list[str] = []  # patient_gender, exam_source, ai_confidence, etc.
    low_confidence_weight: float = 2.0  # for confidence_weighted
    low_confidence_threshold: float = 0.7


class CreateReviewTaskRequest(Schema):
    """建立審核任務請求"""

    name: str
    batch_task_id: str
    sample_size: int
    review_mode: str = "single"  # single, double_blind
    sampling_config: SamplingConfigSchema | None = None
    fp_threshold: float = 0.20


class ReviewTaskResponse(Schema):
    """審核任務響應"""

    id: str
    name: str
    batch_task_id: str
    sample_size: int
    sampling_config: dict
    review_mode: str
    review_mode_display: str
    required_reviewers: int
    fp_threshold: float
    status: str
    status_display: str
    fp_rate: float | None = None
    agreement_rate: float | None = None
    created_at: datetime
    completed_at: datetime | None = None
    created_by: UserInfo


class AssignReviewersRequest(Schema):
    """分配審核者請求"""

    reviewer_ids: list[str]
    arbitrator_id: str | None = None


class ReviewerAssignmentResponse(Schema):
    """審核者分配響應"""

    id: str
    reviewer: UserInfo
    role: str
    role_display: str
    completed_samples: int
    total_assigned: int
    progress_percent: int
    can_view_others: bool
    assigned_at: datetime


class ReviewSampleResponse(Schema):
    """審核樣本響應"""

    id: str
    review_task_id: str
    ai_annotation_id: str
    report_uid: str
    report_title: str
    stratum: str
    ai_classification: str
    ai_confidence: float | None = None
    status: str
    status_display: str
    final_is_correct: bool | None = None
    final_correct_category: str | None = None


class SubmitFeedbackRequest(Schema):
    """提交審核回饋請求"""

    is_correct: bool
    correct_category: str | None = None
    confidence_level: str = "high"  # high, medium, low
    notes: str = ""


class ReviewFeedbackResponse(Schema):
    """審核回饋響應"""

    id: str
    review_sample_id: str
    reviewer: UserInfo
    is_correct: bool
    correct_category: str | None = None
    confidence_level: str
    confidence_level_display: str
    notes: str
    submitted_at: datetime


class ResolveFeedbackRequest(Schema):
    """仲裁決定請求"""

    is_correct: bool
    correct_category: str | None = None
    notes: str = ""


class ReviewMetricsResponse(Schema):
    """審核指標響應"""

    task_id: str
    total_samples: int
    completed_samples: int
    incorrect_samples: int | None = None
    fp_rate: float | None = None
    fp_threshold: float
    fp_passed: bool | None = None
    agreement_rate: float | None = None
    completion_rate: float


# ============================================================================
# AIAnnotation CRUD Schemas
# ============================================================================


class AIAnnotationListItem(Schema):
    """AI 註解列表項"""

    id: str
    report_id: str
    annotation_type: str
    content: str
    confidence_score: float | None = None
    is_deprecated: bool
    created_at: datetime


class AIAnnotationDetailResponse(Schema):
    """AI 註解詳情響應"""

    id: str
    report_id: str
    annotation_type: str
    content: str
    metadata: dict
    guideline_id: str | None = None
    guideline_version: int | None = None
    batch_task_id: str | None = None
    confidence_score: float | None = None
    is_deprecated: bool
    deprecated_at: datetime | None = None
    deprecated_reason: str
    created_at: datetime
    updated_at: datetime
    created_by: str | None = None


class UpdateAIAnnotationRequest(Schema):
    """更新 AI 註解請求"""

    content: str | None = None
    metadata: dict | None = None


# ============================================================================
# LLM Provider Schemas
# ============================================================================


class ProviderInfo(Schema):
    """LLM 提供者資訊"""

    name: str
    display_name: str
    description: str
    is_default: bool
    is_available: bool
    base_url: str
    default_model: str | None = None


class ProviderListResponse(Schema):
    """提供者列表響應"""

    providers: list[ProviderInfo]
    default_provider: str


class ModelInfoResponse(Schema):
    """模型資訊響應"""

    name: str
    provider: str
    size: str | None = None
    size_bytes: int | None = None
    family: str | None = None
    parameter_size: str | None = None
    quantization: str | None = None
    modified_at: str | None = None


class ProviderModelsResponse(Schema):
    """提供者模型列表響應"""

    provider: str
    models: list[ModelInfoResponse]
    total: int


class ProviderHealthResponse(Schema):
    """提供者健康狀態響應"""

    provider: str
    status: str  # healthy, unhealthy
    base_url: str
    model: str | None = None
    model_available: bool | None = None
    available_models: list[str] | None = None
    latency_ms: int | None = None
    error: str | None = None


class TestProviderRequest(Schema):
    """測試提供者請求"""

    base_url: str | None = None
    model: str | None = None
    api_key: str | None = None
    test_message: str = "Hello, respond with 'OK' only."


class TestProviderResponse(Schema):
    """測試提供者響應"""

    success: bool
    provider: str
    message: str
    latency_ms: int | None = None
    model_response: str | None = None
    model_used: str | None = None
