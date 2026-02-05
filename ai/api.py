"""
AI API - Chat, analysis, guideline, batch analysis, and review workflow endpoints.

This module provides REST API endpoints for:
- AI health checks and LLM provider management
- Chat and analysis
- Classification guidelines (CRUD, version control, approval workflow)
- Batch analysis tasks
- Review tasks and feedback
- AI annotations
"""

import asyncio
import logging
import time

from django.conf import settings
from django.db.models import Q
from django.shortcuts import get_object_or_404
from ninja import Router
from ninja_jwt.authentication import JWTAuth

from ai.models import (
    BatchAnalysisTask,
    ClassificationGuideline,
    PromptTemplate,
    ReviewTask,
)
from ai.schemas import (
    AIAnnotationDetailResponse,
    AIAnnotationListItem,
    AIHealthResponse,
    AssignReviewersRequest,
    BatchAnalysisRequest,
    BatchAnalysisResponse,
    BatchAnalysisResultItem,
    BatchAnalysisTaskResponse,
    ConversationChatRequest,
    ConversationChatResponse,
    CreateBatchAnalysisRequest,
    CreateGuidelineRequest,
    CreateGuidelineVersionRequest,
    CreatePromptTemplateRequest,
    CreateReviewTaskRequest,
    GuidelineDetailResponse,
    GuidelineListItem,
    GuidelineVersionItem,
    ModelInfoResponse,
    PromptTemplateDetailResponse,
    PromptTemplateListItem,
    ProviderHealthResponse,
    ProviderInfo,
    ProviderListResponse,
    ProviderModelsResponse,
    QuickChatRequest,
    QuickChatResponse,
    ResolveFeedbackRequest,
    ReviewerAssignmentResponse,
    ReviewFeedbackResponse,
    ReviewMetricsResponse,
    ReviewSampleResponse,
    ReviewTaskResponse,
    SingleAnalysisRequest,
    SingleAnalysisResponse,
    SubmitFeedbackRequest,
    TestGuidelineRequest,
    TestGuidelineResponse,
    TestProviderRequest,
    TestProviderResponse,
    UpdateAIAnnotationRequest,
    UpdateGuidelineRequest,
    UpdatePromptTemplateRequest,
    UserInfo,
)
from ai.services import (
    BatchAnalysisError,
    BatchAnalysisService,
    BatchAnalysisTaskNotFoundError,
    GuidelineNotFoundError,
    GuidelineService,
    GuidelineServiceError,
    GuidelineStatusError,
    LLMConnectionError,
    LLMProviderFactory,
    LLMTimeoutError,
    ReviewService,
    ReviewServiceError,
    ReviewTaskNotFoundError,
)
from ai.services.llm_service import get_llm_service
from report.models import AIAnnotation

logger = logging.getLogger(__name__)

router = Router(auth=JWTAuth())


# ============================================================================
# Health Check Endpoints
# ============================================================================


@router.get("/health", response=AIHealthResponse, auth=None)
def ai_health_check(request):
    """AI 服務健康檢查（無需認證）"""
    llm = get_llm_service()

    # Run async health check
    loop = asyncio.new_event_loop()
    try:
        result = loop.run_until_complete(llm.health_check())
    finally:
        loop.close()

    return AIHealthResponse(**result)


# ============================================================================
# Chat Endpoints
# ============================================================================


@router.post("/chat/quick", response=QuickChatResponse)
def quick_chat(request, data: QuickChatRequest):
    """快速聊天（單輪對話）"""
    llm = get_llm_service()

    try:
        loop = asyncio.new_event_loop()
        try:
            response = loop.run_until_complete(
                llm.quick_chat(
                    message=data.message,
                    system_prompt=data.system_prompt,
                )
            )
        finally:
            loop.close()

        return QuickChatResponse(
            content=response.content,
            model=response.model,
            latency_ms=response.latency_ms,
            tokens_used=response.tokens_used,
        )

    except LLMConnectionError as e:
        logger.warning(f"LLM connection error: {e}")
        return QuickChatResponse(
            content=f"無法連接 AI 服務：{e}",
            model="error",
            latency_ms=0,
            tokens_used=None,
        )

    except LLMTimeoutError as e:
        logger.warning(f"LLM timeout: {e}")
        return QuickChatResponse(
            content="AI 服務回應超時，請稍後再試",
            model="error",
            latency_ms=0,
            tokens_used=None,
        )


@router.post("/chat", response=ConversationChatResponse)
def conversation_chat(request, data: ConversationChatRequest):
    """對話聊天（多輪對話）"""
    llm = get_llm_service()

    # Build messages from history
    messages = []

    # Add system prompt based on context
    if data.context:
        context_parts = []
        if data.context.get("pageType"):
            context_parts.append(f"頁面類型: {data.context['pageType']}")
        if data.context.get("reportId"):
            context_parts.append(f"報告 ID: {data.context['reportId']}")
        if data.context.get("studyId"):
            context_parts.append(f"檢查 ID: {data.context['studyId']}")

        if context_parts:
            system_prompt = (
                "你是醫學影像資料平台的 AI 助手，可以幫助用戶分析報告、查詢資訊和解答問題。\n"
                f"當前上下文：{', '.join(context_parts)}"
            )
            messages.append({"role": "system", "content": system_prompt})

    # Add conversation history
    for msg in data.conversation_history:
        messages.append({"role": msg.role, "content": msg.content})

    # Add current message
    messages.append({"role": "user", "content": data.message})

    try:
        loop = asyncio.new_event_loop()
        try:
            response = loop.run_until_complete(
                llm.chat(messages=messages, temperature=data.temperature)
            )
        finally:
            loop.close()

        return ConversationChatResponse(
            content=response.content,
            model=response.model,
            latency_ms=response.latency_ms,
            tokens_used=response.tokens_used,
        )

    except LLMConnectionError as e:
        logger.warning(f"LLM connection error: {e}")
        return ConversationChatResponse(
            content=f"無法連接 AI 服務：{e}",
            model="error",
            latency_ms=0,
            tokens_used=None,
        )

    except LLMTimeoutError as e:
        logger.warning(f"LLM timeout: {e}")
        return ConversationChatResponse(
            content="AI 服務回應超時，請稍後再試",
            model="error",
            latency_ms=0,
            tokens_used=None,
        )


# ============================================================================
# Analysis Endpoints
# ============================================================================


@router.post("/analyze", response=SingleAnalysisResponse)
def analyze_report(request, data: SingleAnalysisRequest):
    """單一報告 AI 分析"""
    from report.models import Report

    llm = get_llm_service()

    # Get report content
    try:
        report = Report.objects.get(uid=data.report_uid)
        report_content = report.content_raw or report.content or ""
    except Report.DoesNotExist:
        return SingleAnalysisResponse(
            report_uid=data.report_uid,
            analysis_content=f"找不到報告 {data.report_uid}",
            annotation_type=data.annotation_type,
            model="error",
            latency_ms=0,
            tokens_used=None,
        )

    # Build analysis prompt
    annotation_prompts = {
        "highlight": "請標記報告中的重要發現和異常結果，使用 **粗體** 標記重點：",
        "classification": "請分析這份報告並分類其主要發現，包括：嚴重程度（正常/輕微/中等/嚴重）、主要診斷類別：",
        "extraction": "請從這份報告中提取以下結構化資訊：主要發現、異常值、建議事項：",
        "scoring": "請為這份報告的嚴重程度評分（1-10），並說明評分理由：",
        "general": "請分析這份醫療報告：",
    }

    system_prompt = (
        "你是專業的醫學影像分析助手，專精於分析醫療報告和影像檢查結果。請用繁體中文回答。"
    )
    analysis_prompt = annotation_prompts.get(data.annotation_type, annotation_prompts["general"])

    messages = [
        {"role": "system", "content": system_prompt},
        {
            "role": "user",
            "content": f"{analysis_prompt}\n\n{data.user_prompt}\n\n報告內容：\n{report_content}",
        },
    ]

    try:
        loop = asyncio.new_event_loop()
        try:
            response = loop.run_until_complete(
                llm.chat(messages=messages, temperature=data.temperature)
            )
        finally:
            loop.close()

        return SingleAnalysisResponse(
            report_uid=data.report_uid,
            analysis_content=response.content,
            annotation_type=data.annotation_type,
            model=response.model,
            latency_ms=response.latency_ms,
            tokens_used=response.tokens_used,
        )

    except LLMConnectionError as e:
        logger.warning(f"Analysis LLM connection error: {e}")
        return SingleAnalysisResponse(
            report_uid=data.report_uid,
            analysis_content=f"AI 服務連接失敗：{e}",
            annotation_type=data.annotation_type,
            model="error",
            latency_ms=0,
            tokens_used=None,
        )

    except LLMTimeoutError as e:
        logger.warning(f"Analysis LLM timeout: {e}")
        return SingleAnalysisResponse(
            report_uid=data.report_uid,
            analysis_content="AI 分析超時，請稍後再試",
            annotation_type=data.annotation_type,
            model="error",
            latency_ms=0,
            tokens_used=None,
        )


@router.post("/batch-analyze", response=BatchAnalysisResponse)
def batch_analyze_reports(request, data: BatchAnalysisRequest):
    """批次報告 AI 分析（目前同步處理，後續可改為背景任務）"""
    report_count = len(data.report_ids)

    # Validate report count
    if report_count > 50:
        return BatchAnalysisResponse(
            status="failed",
            message="批次分析最多支援 50 份報告",
            report_count=report_count,
            task_id=None,
        )

    if report_count == 0:
        return BatchAnalysisResponse(
            status="failed",
            message="請提供至少一份報告進行分析",
            report_count=0,
            task_id=None,
        )

    # For now, return queued status
    # TODO: Implement actual background task processing with Celery
    import uuid

    task_id = f"batch_{uuid.uuid4().hex[:12]}"

    return BatchAnalysisResponse(
        status="queued",
        message=f"已將 {report_count} 份報告加入分析佇列",
        report_count=report_count,
        task_id=task_id,
    )


# ============================================================================
# Prompt Template Endpoints
# ============================================================================


@router.get("/prompt-templates", response=list[PromptTemplateListItem])
def list_prompt_templates(
    request,
    category: str | None = None,
    use_case: str | None = None,
    q: str | None = None,
    is_active: bool | None = None,
):
    """獲取提示詞模板列表"""
    queryset = PromptTemplate.objects.filter(created_by=request.user)

    # 分類篩選
    if category:
        queryset = queryset.filter(category=category)

    # 使用案例篩選
    if use_case:
        queryset = queryset.filter(use_case=use_case)

    # 搜尋
    if q:
        queryset = queryset.filter(
            Q(name__icontains=q) | Q(description__icontains=q) | Q(content__icontains=q)
        )

    # 啟用狀態篩選
    if is_active is not None:
        queryset = queryset.filter(is_active=is_active)

    templates = queryset.order_by("-updated_at")
    return [PromptTemplateListItem.from_model(template) for template in templates]


@router.get("/prompt-templates/{template_id}", response=PromptTemplateDetailResponse)
def get_prompt_template(request, template_id: str):
    """獲取提示詞模板詳情"""
    template = get_object_or_404(
        PromptTemplate,
        id=template_id,
        created_by=request.user,
    )
    return PromptTemplateDetailResponse.from_model(template)


@router.post("/prompt-templates", response=PromptTemplateDetailResponse)
def create_prompt_template(request, data: CreatePromptTemplateRequest):
    """創建提示詞模板"""
    template = PromptTemplate.objects.create(
        name=data.name,
        content=data.content,
        category=data.category,
        use_case=data.use_case,
        description=data.description,
        created_by=request.user,
    )
    return PromptTemplateDetailResponse.from_model(template)


@router.put("/prompt-templates/{template_id}", response=PromptTemplateDetailResponse)
def update_prompt_template(
    request,
    template_id: str,
    data: UpdatePromptTemplateRequest,
):
    """更新提示詞模板"""
    template = get_object_or_404(
        PromptTemplate,
        id=template_id,
        created_by=request.user,
    )

    # 更新欄位
    if data.name is not None:
        template.name = data.name
    if data.content is not None:
        template.content = data.content
    if data.category is not None:
        template.category = data.category
    if data.use_case is not None:
        template.use_case = data.use_case
    if data.description is not None:
        template.description = data.description
    if data.is_active is not None:
        template.is_active = data.is_active

    template.save()
    return PromptTemplateDetailResponse.from_model(template)


@router.delete("/prompt-templates/{template_id}")
def delete_prompt_template(request, template_id: str):
    """刪除提示詞模板"""
    template = get_object_or_404(
        PromptTemplate,
        id=template_id,
        created_by=request.user,
    )
    template.delete()
    return {"message": "提示詞模板已刪除"}


# ============================================================================
# Classification Guideline Endpoints
# ============================================================================


@router.get("/guidelines", response=list[GuidelineListItem])
def list_guidelines(
    request,
    status: str | None = None,
    is_current: bool | None = None,
    q: str | None = None,
):
    """獲取分類指南列表"""
    queryset = GuidelineService.get_guidelines_queryset(
        user=request.user,
        status=status,
        is_current=is_current,
        q=q,
    )

    guidelines = []
    for g in queryset[:100]:  # Limit to 100
        guidelines.append(
            GuidelineListItem(
                id=str(g.id),
                name=g.name,
                description=g.description,
                version=g.version,
                is_current=g.is_current,
                status=g.status,
                status_display=g.get_status_display(),
                categories=g.categories,
                created_at=g.created_at,
                updated_at=g.updated_at,
                created_by=UserInfo(
                    id=str(g.created_by.id),
                    name=g.created_by.get_full_name() or g.created_by.get_username(),
                    email=g.created_by.email,
                ),
            )
        )
    return guidelines


@router.post("/guidelines", response=GuidelineDetailResponse)
def create_guideline(request, data: CreateGuidelineRequest):
    """建立分類指南"""
    try:
        guideline = GuidelineService.create_guideline(
            name=data.name,
            prompt_template=data.prompt_template,
            categories=data.categories,
            user=request.user,
            description=data.description,
            model_config=data.llm_config,
        )
        return _guideline_to_response(guideline)
    except GuidelineServiceError as e:
        return router.create_response(request, {"error": str(e)}, status=400)


@router.get("/guidelines/{guideline_id}", response=GuidelineDetailResponse)
def get_guideline(request, guideline_id: str):
    """獲取分類指南詳情"""
    try:
        guideline = GuidelineService.get_guideline(guideline_id)
        return _guideline_to_response(guideline)
    except GuidelineNotFoundError:
        return router.create_response(request, {"error": "Guideline not found"}, status=404)


@router.put("/guidelines/{guideline_id}", response=GuidelineDetailResponse)
def update_guideline(request, guideline_id: str, data: UpdateGuidelineRequest):
    """更新分類指南（僅草稿狀態）"""
    try:
        guideline = GuidelineService.update_guideline(
            guideline_id=guideline_id,
            user=request.user,
            name=data.name,
            description=data.description,
            prompt_template=data.prompt_template,
            categories=data.categories,
            model_config=data.llm_config,
        )
        return _guideline_to_response(guideline)
    except GuidelineNotFoundError:
        return router.create_response(request, {"error": "Guideline not found"}, status=404)
    except GuidelineStatusError as e:
        return router.create_response(request, {"error": str(e)}, status=400)
    except GuidelineServiceError as e:
        return router.create_response(request, {"error": str(e)}, status=400)


@router.post("/guidelines/{guideline_id}/test", response=TestGuidelineResponse)
def test_guideline(request, guideline_id: str, data: TestGuidelineRequest):
    """測試分類指南（使用樣本報告）"""
    try:
        guideline = GuidelineService.get_guideline(guideline_id)

        results = []
        for report_uid in data.report_uids[:5]:  # Limit to 5 test reports
            try:
                result = BatchAnalysisService.process_single_report(
                    report_uid=report_uid,
                    guideline_id=guideline_id,
                    batch_task_id=None,
                )
                results.append(result)
            except Exception as e:
                results.append(
                    {
                        "report_uid": report_uid,
                        "error": str(e),
                    }
                )

        return TestGuidelineResponse(
            guideline_id=str(guideline.id),
            test_count=len(results),
            results=results,
        )
    except GuidelineNotFoundError:
        return router.create_response(request, {"error": "Guideline not found"}, status=404)


@router.post("/guidelines/{guideline_id}/testing", response=GuidelineDetailResponse)
def set_guideline_testing(request, guideline_id: str):
    """將指南設為測試中狀態"""
    try:
        guideline = GuidelineService.set_status_testing(guideline_id, request.user)
        return _guideline_to_response(guideline)
    except GuidelineNotFoundError:
        return router.create_response(request, {"error": "Guideline not found"}, status=404)
    except GuidelineStatusError as e:
        return router.create_response(request, {"error": str(e)}, status=400)


@router.post("/guidelines/{guideline_id}/approve", response=GuidelineDetailResponse)
def approve_guideline(request, guideline_id: str):
    """核准分類指南"""
    try:
        guideline = GuidelineService.approve_guideline(guideline_id, request.user)
        return _guideline_to_response(guideline)
    except GuidelineNotFoundError:
        return router.create_response(request, {"error": "Guideline not found"}, status=404)
    except GuidelineStatusError as e:
        return router.create_response(request, {"error": str(e)}, status=400)


@router.post("/guidelines/{guideline_id}/archive", response=GuidelineDetailResponse)
def archive_guideline(request, guideline_id: str):
    """封存分類指南"""
    try:
        guideline = GuidelineService.archive_guideline(guideline_id, request.user)
        return _guideline_to_response(guideline)
    except GuidelineNotFoundError:
        return router.create_response(request, {"error": "Guideline not found"}, status=404)
    except GuidelineStatusError as e:
        return router.create_response(request, {"error": str(e)}, status=400)


@router.get("/guidelines/{guideline_id}/versions", response=list[GuidelineVersionItem])
def get_guideline_versions(request, guideline_id: str):
    """獲取指南版本歷史"""
    try:
        versions = GuidelineService.get_version_history(guideline_id)
        return [
            GuidelineVersionItem(
                id=str(v.id),
                version=v.version,
                is_current=v.is_current,
                status=v.status,
                created_at=v.created_at,
                created_by=UserInfo(
                    id=str(v.created_by.id),
                    name=v.created_by.get_full_name() or v.created_by.get_username(),
                    email=v.created_by.email,
                ),
            )
            for v in versions
        ]
    except GuidelineNotFoundError:
        return router.create_response(request, {"error": "Guideline not found"}, status=404)


@router.post("/guidelines/{guideline_id}/versions", response=GuidelineDetailResponse)
def create_guideline_version(request, guideline_id: str, data: CreateGuidelineVersionRequest):
    """建立新版本"""
    try:
        guideline = GuidelineService.create_new_version(
            guideline_id=guideline_id,
            user=request.user,
            prompt_template=data.prompt_template,
            categories=data.categories,
            model_config=data.llm_config,
        )
        return _guideline_to_response(guideline)
    except GuidelineNotFoundError:
        return router.create_response(request, {"error": "Guideline not found"}, status=404)
    except GuidelineStatusError as e:
        return router.create_response(request, {"error": str(e)}, status=400)


def _guideline_to_response(g: ClassificationGuideline) -> GuidelineDetailResponse:
    """Convert guideline model to response schema."""
    return GuidelineDetailResponse(
        id=str(g.id),
        name=g.name,
        description=g.description,
        prompt_template=g.prompt_template,
        categories=g.categories,
        version=g.version,
        parent_version_id=str(g.parent_version_id) if g.parent_version_id else None,
        is_current=g.is_current,
        status=g.status,
        status_display=g.get_status_display(),
        llm_config=g.model_config,
        created_at=g.created_at,
        updated_at=g.updated_at,
        approved_at=g.approved_at,
        created_by=UserInfo(
            id=str(g.created_by.id),
            name=g.created_by.get_full_name() or g.created_by.get_username(),
            email=g.created_by.email,
        ),
        approved_by=(
            UserInfo(
                id=str(g.approved_by.id),
                name=g.approved_by.get_full_name() or g.approved_by.get_username(),
                email=g.approved_by.email,
            )
            if g.approved_by
            else None
        ),
    )


# ============================================================================
# Batch Analysis Task Endpoints
# ============================================================================


@router.post("/batch-analysis", response=BatchAnalysisTaskResponse)
def create_batch_analysis_task(request, data: CreateBatchAnalysisRequest):
    """建立批次分析任務"""
    try:
        task = BatchAnalysisService.create_task(
            guideline_id=data.guideline_id,
            report_uids=data.report_uids,
            user=request.user,
            project_id=data.project_id,
        )

        # Start async processing
        BatchAnalysisService.start_task(str(task.id))

        return _batch_task_to_response(task)
    except BatchAnalysisError as e:
        return router.create_response(request, {"error": str(e)}, status=400)


@router.get("/batch-analysis/{task_id}", response=BatchAnalysisTaskResponse)
def get_batch_analysis_task(request, task_id: str):
    """獲取批次分析任務狀態"""
    try:
        task = BatchAnalysisService.get_task(task_id)
        return _batch_task_to_response(task)
    except BatchAnalysisTaskNotFoundError:
        return router.create_response(request, {"error": "Task not found"}, status=404)


@router.get("/batch-analysis/{task_id}/results", response=list[BatchAnalysisResultItem])
def get_batch_analysis_results(
    request,
    task_id: str,
    page: int = 1,
    page_size: int = 20,
):
    """獲取批次分析結果（分頁）"""
    try:
        # Verify task exists
        BatchAnalysisService.get_task(task_id)

        annotations = (
            AIAnnotation.objects.filter(
                batch_task_id=task_id,
                is_deprecated=False,
            )
            .select_related("report")
            .order_by("-created_at")
        )

        # Manual pagination
        start = (page - 1) * page_size
        end = start + page_size
        page_annotations = annotations[start:end]

        return [
            BatchAnalysisResultItem(
                annotation_id=str(ann.id),
                report_uid=ann.report.uid,
                classification=ann.content,
                confidence_score=ann.confidence_score,
                created_at=ann.created_at,
            )
            for ann in page_annotations
        ]
    except BatchAnalysisTaskNotFoundError:
        return router.create_response(request, {"error": "Task not found"}, status=404)


@router.post("/batch-analysis/{task_id}/cancel", response=BatchAnalysisTaskResponse)
def cancel_batch_analysis_task(request, task_id: str):
    """取消批次分析任務"""
    try:
        task = BatchAnalysisService.cancel_task(task_id)
        return _batch_task_to_response(task)
    except BatchAnalysisTaskNotFoundError:
        return router.create_response(request, {"error": "Task not found"}, status=404)
    except BatchAnalysisError as e:
        return router.create_response(request, {"error": str(e)}, status=400)


def _batch_task_to_response(task: BatchAnalysisTask) -> BatchAnalysisTaskResponse:
    """Convert batch task model to response schema."""
    return BatchAnalysisTaskResponse(
        id=str(task.id),
        guideline_id=str(task.guideline_id),
        guideline_name=task.guideline.name if task.guideline else None,
        project_id=str(task.project_id) if task.project_id else None,
        status=task.status,
        status_display=task.get_status_display(),
        total_count=task.total_count,
        processed_count=task.processed_count,
        success_count=task.success_count,
        error_count=task.error_count,
        progress_percent=task.get_progress_percent(),
        results_summary=task.results_summary,
        error_details=task.error_details,
        funboost_task_id=task.funboost_task_id,
        created_at=task.created_at,
        started_at=task.started_at,
        completed_at=task.completed_at,
        created_by=UserInfo(
            id=str(task.created_by.id),
            name=task.created_by.get_full_name() or task.created_by.get_username(),
            email=task.created_by.email,
        ),
    )


# ============================================================================
# Review Task Endpoints
# ============================================================================


@router.post("/reviews", response=ReviewTaskResponse)
def create_review_task(request, data: CreateReviewTaskRequest):
    """建立審核任務"""
    try:
        sampling_config = data.sampling_config.dict() if data.sampling_config else None
        task = ReviewService.create_review_task(
            name=data.name,
            batch_task_id=data.batch_task_id,
            sample_size=data.sample_size,
            user=request.user,
            review_mode=data.review_mode,
            sampling_config=sampling_config,
            fp_threshold=data.fp_threshold,
        )

        # Start sample generation
        from ai.tasks import start_sample_generation

        start_sample_generation(str(task.id))

        return _review_task_to_response(task)
    except ReviewServiceError as e:
        return router.create_response(request, {"error": str(e)}, status=400)


@router.get("/reviews/{task_id}", response=ReviewTaskResponse)
def get_review_task(request, task_id: str):
    """獲取審核任務詳情"""
    try:
        task = ReviewService.get_review_task(task_id)
        return _review_task_to_response(task)
    except ReviewTaskNotFoundError:
        return router.create_response(request, {"error": "Task not found"}, status=404)


@router.post("/reviews/{task_id}/assign", response=list[ReviewerAssignmentResponse])
def assign_reviewers(request, task_id: str, data: AssignReviewersRequest):
    """分配審核者"""
    try:
        assignments = ReviewService.assign_reviewers(
            review_task_id=task_id,
            reviewer_ids=data.reviewer_ids,
            arbitrator_id=data.arbitrator_id,
        )
        return [
            ReviewerAssignmentResponse(
                id=str(a.id),
                reviewer=UserInfo(
                    id=str(a.reviewer.id),
                    name=a.reviewer.get_full_name() or a.reviewer.get_username(),
                    email=a.reviewer.email,
                ),
                role=a.role,
                role_display=a.get_role_display(),
                completed_samples=a.completed_samples,
                total_assigned=a.total_assigned,
                progress_percent=a.get_progress_percent(),
                can_view_others=a.can_view_others,
                assigned_at=a.assigned_at,
            )
            for a in assignments
        ]
    except ReviewTaskNotFoundError:
        return router.create_response(request, {"error": "Task not found"}, status=404)
    except ReviewServiceError as e:
        return router.create_response(request, {"error": str(e)}, status=400)


@router.get("/reviews/{task_id}/samples", response=list[ReviewSampleResponse])
def get_review_samples(
    request,
    task_id: str,
    status: str | None = None,
):
    """獲取審核樣本（當前審核者可見的）"""
    try:
        samples = ReviewService.get_samples_for_reviewer(
            review_task_id=task_id,
            reviewer_id=str(request.user.id),
            status=status,
        )
        return [
            ReviewSampleResponse(
                id=str(s.id),
                review_task_id=str(s.review_task_id),
                ai_annotation_id=str(s.ai_annotation_id),
                report_uid=s.ai_annotation.report.uid,
                report_title=s.ai_annotation.report.title,
                stratum=s.stratum,
                ai_classification=s.ai_classification,
                ai_confidence=s.ai_confidence,
                status=s.status,
                status_display=s.get_status_display(),
                final_is_correct=s.final_is_correct,
                final_correct_category=s.final_correct_category,
            )
            for s in samples[:100]  # Limit to 100
        ]
    except ReviewTaskNotFoundError:
        return router.create_response(request, {"error": "Task not found"}, status=404)
    except ReviewServiceError as e:
        return router.create_response(request, {"error": str(e)}, status=400)


@router.post(
    "/reviews/{task_id}/samples/{sample_id}/feedback",
    response=ReviewFeedbackResponse,
)
def submit_feedback(
    request,
    task_id: str,
    sample_id: str,
    data: SubmitFeedbackRequest,
):
    """提交審核回饋"""
    try:
        feedback = ReviewService.submit_feedback(
            review_task_id=task_id,
            sample_id=sample_id,
            reviewer_id=str(request.user.id),
            is_correct=data.is_correct,
            correct_category=data.correct_category,
            confidence_level=data.confidence_level,
            notes=data.notes,
        )
        return ReviewFeedbackResponse(
            id=str(feedback.id),
            review_sample_id=str(feedback.review_sample_id),
            reviewer=UserInfo(
                id=str(feedback.reviewer.id),
                name=feedback.reviewer.get_full_name() or feedback.reviewer.get_username(),
                email=feedback.reviewer.email,
            ),
            is_correct=feedback.is_correct,
            correct_category=feedback.correct_category,
            confidence_level=feedback.confidence_level,
            confidence_level_display=feedback.get_confidence_level_display(),
            notes=feedback.notes,
            submitted_at=feedback.submitted_at,
        )
    except ReviewTaskNotFoundError:
        return router.create_response(request, {"error": "Task not found"}, status=404)
    except ReviewServiceError as e:
        return router.create_response(request, {"error": str(e)}, status=400)


@router.get("/reviews/{task_id}/statistics", response=ReviewMetricsResponse)
def get_review_statistics(request, task_id: str):
    """獲取審核統計指標"""
    try:
        metrics = ReviewService.calculate_metrics(task_id)
        task = ReviewService.get_review_task(task_id)
        return ReviewMetricsResponse(
            task_id=str(task_id),
            total_samples=metrics["total_samples"],
            completed_samples=metrics["completed_samples"],
            incorrect_samples=metrics.get("incorrect_samples"),
            fp_rate=metrics["fp_rate"],
            fp_threshold=task.fp_threshold,
            fp_passed=metrics.get("fp_passed"),
            agreement_rate=metrics.get("agreement_rate"),
            completion_rate=metrics["completion_rate"],
        )
    except ReviewTaskNotFoundError:
        return router.create_response(request, {"error": "Task not found"}, status=404)


@router.get("/reviews/{task_id}/conflicts", response=list[ReviewSampleResponse])
def get_review_conflicts(request, task_id: str):
    """獲取待仲裁的衝突樣本"""
    try:
        conflicts = ReviewService.get_conflicts(task_id)
        return [
            ReviewSampleResponse(
                id=str(s.id),
                review_task_id=str(s.review_task_id),
                ai_annotation_id=str(s.ai_annotation_id),
                report_uid=s.ai_annotation.report.uid,
                report_title=s.ai_annotation.report.title,
                stratum=s.stratum,
                ai_classification=s.ai_classification,
                ai_confidence=s.ai_confidence,
                status=s.status,
                status_display=s.get_status_display(),
                final_is_correct=s.final_is_correct,
                final_correct_category=s.final_correct_category,
            )
            for s in conflicts
        ]
    except ReviewTaskNotFoundError:
        return router.create_response(request, {"error": "Task not found"}, status=404)


@router.post(
    "/reviews/{task_id}/samples/{sample_id}/resolve",
    response=ReviewSampleResponse,
)
def resolve_conflict(
    request,
    task_id: str,
    sample_id: str,
    data: ResolveFeedbackRequest,
):
    """仲裁解決衝突"""
    try:
        sample = ReviewService.resolve_conflict(
            review_task_id=task_id,
            sample_id=sample_id,
            arbitrator_id=str(request.user.id),
            is_correct=data.is_correct,
            correct_category=data.correct_category,
            notes=data.notes,
        )
        return ReviewSampleResponse(
            id=str(sample.id),
            review_task_id=str(sample.review_task_id),
            ai_annotation_id=str(sample.ai_annotation_id),
            report_uid=sample.ai_annotation.report.uid,
            report_title=sample.ai_annotation.report.title,
            stratum=sample.stratum,
            ai_classification=sample.ai_classification,
            ai_confidence=sample.ai_confidence,
            status=sample.status,
            status_display=sample.get_status_display(),
            final_is_correct=sample.final_is_correct,
            final_correct_category=sample.final_correct_category,
        )
    except ReviewTaskNotFoundError:
        return router.create_response(request, {"error": "Task not found"}, status=404)
    except ReviewServiceError as e:
        return router.create_response(request, {"error": str(e)}, status=400)


def _review_task_to_response(task: ReviewTask) -> ReviewTaskResponse:
    """Convert review task model to response schema."""
    return ReviewTaskResponse(
        id=str(task.id),
        name=task.name,
        batch_task_id=str(task.batch_task_id),
        sample_size=task.sample_size,
        sampling_config=task.sampling_config,
        review_mode=task.review_mode,
        review_mode_display=task.get_review_mode_display(),
        required_reviewers=task.required_reviewers,
        fp_threshold=task.fp_threshold,
        status=task.status,
        status_display=task.get_status_display(),
        fp_rate=task.fp_rate,
        agreement_rate=task.agreement_rate,
        created_at=task.created_at,
        completed_at=task.completed_at,
        created_by=UserInfo(
            id=str(task.created_by.id),
            name=task.created_by.get_full_name() or task.created_by.get_username(),
            email=task.created_by.email,
        ),
    )


# ============================================================================
# AI Annotation CRUD Endpoints
# ============================================================================


@router.get("/annotations", response=list[AIAnnotationListItem])
def list_annotations(
    request,
    report_uid: str | None = None,
    guideline_id: str | None = None,
    batch_task_id: str | None = None,
    annotation_type: str | None = None,
    is_deprecated: bool | None = None,
):
    """獲取 AI 註解列表"""
    queryset = AIAnnotation.objects.select_related("report").order_by("-created_at")

    if report_uid:
        queryset = queryset.filter(report__uid=report_uid)
    if guideline_id:
        queryset = queryset.filter(guideline_id=guideline_id)
    if batch_task_id:
        queryset = queryset.filter(batch_task_id=batch_task_id)
    if annotation_type:
        queryset = queryset.filter(annotation_type=annotation_type)
    if is_deprecated is not None:
        queryset = queryset.filter(is_deprecated=is_deprecated)

    return [
        AIAnnotationListItem(
            id=str(ann.id),
            report_id=ann.report.uid,
            annotation_type=ann.annotation_type,
            content=ann.content,
            confidence_score=ann.confidence_score,
            is_deprecated=ann.is_deprecated,
            created_at=ann.created_at,
        )
        for ann in queryset[:100]  # Limit to 100
    ]


@router.get("/annotations/{annotation_id}", response=AIAnnotationDetailResponse)
def get_annotation(request, annotation_id: str):
    """獲取 AI 註解詳情"""
    annotation = get_object_or_404(AIAnnotation, id=annotation_id)
    return AIAnnotationDetailResponse(
        id=str(annotation.id),
        report_id=annotation.report.uid,
        annotation_type=annotation.annotation_type,
        content=annotation.content,
        metadata=annotation.metadata,
        guideline_id=str(annotation.guideline_id) if annotation.guideline_id else None,
        guideline_version=annotation.guideline_version,
        batch_task_id=str(annotation.batch_task_id) if annotation.batch_task_id else None,
        confidence_score=annotation.confidence_score,
        is_deprecated=annotation.is_deprecated,
        deprecated_at=annotation.deprecated_at,
        deprecated_reason=annotation.deprecated_reason,
        created_at=annotation.created_at,
        updated_at=annotation.updated_at,
        created_by=annotation.created_by.get_full_name() if annotation.created_by else None,
    )


@router.put("/annotations/{annotation_id}", response=AIAnnotationDetailResponse)
def update_annotation(request, annotation_id: str, data: UpdateAIAnnotationRequest):
    """更新 AI 註解（手動修正）"""
    annotation = get_object_or_404(AIAnnotation, id=annotation_id)

    if data.content is not None:
        annotation.content = data.content
    if data.metadata is not None:
        annotation.metadata = data.metadata

    annotation.save()

    return AIAnnotationDetailResponse(
        id=str(annotation.id),
        report_id=annotation.report.uid,
        annotation_type=annotation.annotation_type,
        content=annotation.content,
        metadata=annotation.metadata,
        guideline_id=str(annotation.guideline_id) if annotation.guideline_id else None,
        guideline_version=annotation.guideline_version,
        batch_task_id=str(annotation.batch_task_id) if annotation.batch_task_id else None,
        confidence_score=annotation.confidence_score,
        is_deprecated=annotation.is_deprecated,
        deprecated_at=annotation.deprecated_at,
        deprecated_reason=annotation.deprecated_reason,
        created_at=annotation.created_at,
        updated_at=annotation.updated_at,
        created_by=annotation.created_by.get_full_name() if annotation.created_by else None,
    )


@router.delete("/annotations/{annotation_id}")
def delete_annotation(request, annotation_id: str):
    """軟刪除 AI 註解（標記為廢棄）"""
    from django.utils import timezone

    annotation = get_object_or_404(AIAnnotation, id=annotation_id)

    annotation.is_deprecated = True
    annotation.deprecated_at = timezone.now()
    annotation.deprecated_reason = "Manually deprecated by user"
    annotation.save(update_fields=["is_deprecated", "deprecated_at", "deprecated_reason"])

    return {"message": "Annotation marked as deprecated"}


# ============================================================================
# LLM Provider Management Endpoints
# ============================================================================


PROVIDER_DESCRIPTIONS = {
    "ollama": "Local LLM server supporting Llama, Mistral, Qwen, and other open-source models",
    "lmstudio": "Desktop application for running local LLMs with OpenAI-compatible API",
    "openai_compatible": "Generic provider for OpenAI API compatible backends",
    "vllm": "High-throughput LLM serving engine with OpenAI-compatible API",
    "localai": "Self-hosted, community-driven local AI with OpenAI-compatible API",
    "text_generation_webui": "Web UI for running Large Language Models",
    "tgwui": "Text Generation Web UI (alias)",
}


@router.get("/providers", response=ProviderListResponse, auth=None)
def list_providers(request):
    """列出可用的 LLM 提供者"""
    providers = []
    default_provider = settings.AI_CONFIG.get("PROVIDER", "ollama")

    for name in LLMProviderFactory.list_providers():
        try:
            provider = LLMProviderFactory.create(name, use_cache=False)
            providers.append(
                ProviderInfo(
                    name=name,
                    display_name=name.replace("_", " ").title(),
                    description=PROVIDER_DESCRIPTIONS.get(name, f"{name} LLM provider"),
                    is_default=(name == default_provider),
                    is_available=True,
                    base_url=provider.get_base_url(),
                    default_model=provider.get_default_model(),
                )
            )
        except Exception as e:
            logger.warning(f"Failed to get provider info for {name}: {e}")
            providers.append(
                ProviderInfo(
                    name=name,
                    display_name=name.replace("_", " ").title(),
                    description=PROVIDER_DESCRIPTIONS.get(name, f"{name} LLM provider"),
                    is_default=(name == default_provider),
                    is_available=False,
                    base_url="",
                    default_model=None,
                )
            )

    return ProviderListResponse(
        providers=providers,
        default_provider=default_provider,
    )


@router.get("/providers/{provider_name}", response=ProviderInfo, auth=None)
def get_provider(request, provider_name: str):
    """獲取特定提供者資訊"""
    if not LLMProviderFactory.is_registered(provider_name):
        return router.create_response(
            request,
            {"error": f"Provider '{provider_name}' not found"},
            status=404,
        )

    default_provider = settings.AI_CONFIG.get("PROVIDER", "ollama")

    try:
        provider = LLMProviderFactory.create(provider_name, use_cache=False)
        return ProviderInfo(
            name=provider_name,
            display_name=provider_name.replace("_", " ").title(),
            description=PROVIDER_DESCRIPTIONS.get(provider_name, f"{provider_name} LLM provider"),
            is_default=(provider_name == default_provider),
            is_available=True,
            base_url=provider.get_base_url(),
            default_model=provider.get_default_model(),
        )
    except Exception as e:
        logger.warning(f"Failed to get provider {provider_name}: {e}")
        return ProviderInfo(
            name=provider_name,
            display_name=provider_name.replace("_", " ").title(),
            description=PROVIDER_DESCRIPTIONS.get(provider_name, f"{provider_name} LLM provider"),
            is_default=(provider_name == default_provider),
            is_available=False,
            base_url="",
            default_model=None,
        )


@router.get("/providers/{provider_name}/models", response=ProviderModelsResponse, auth=None)
def list_provider_models(request, provider_name: str):
    """列出提供者的可用模型"""
    if not LLMProviderFactory.is_registered(provider_name):
        return router.create_response(
            request,
            {"error": f"Provider '{provider_name}' not found"},
            status=404,
        )

    try:
        provider = LLMProviderFactory.create(provider_name)

        # Run async list_models
        loop = asyncio.new_event_loop()
        try:
            models = loop.run_until_complete(provider.list_models())
        finally:
            loop.close()

        return ProviderModelsResponse(
            provider=provider_name,
            models=[
                ModelInfoResponse(
                    name=m.name,
                    provider=provider_name,
                    size=m.size,
                    size_bytes=m.size_bytes,
                    family=m.family,
                    parameter_size=m.parameter_size,
                    quantization=m.quantization,
                    modified_at=m.modified_at,
                )
                for m in models
            ],
            total=len(models),
        )

    except LLMConnectionError as e:
        return router.create_response(
            request,
            {"error": f"Cannot connect to provider: {e}"},
            status=503,
        )
    except Exception as e:
        logger.error(f"Failed to list models for {provider_name}: {e}")
        return router.create_response(
            request,
            {"error": f"Failed to list models: {e}"},
            status=500,
        )


@router.get("/providers/{provider_name}/health", response=ProviderHealthResponse, auth=None)
def provider_health_check(request, provider_name: str):
    """提供者健康檢查"""
    if not LLMProviderFactory.is_registered(provider_name):
        return router.create_response(
            request,
            {"error": f"Provider '{provider_name}' not found"},
            status=404,
        )

    try:
        provider = LLMProviderFactory.create(provider_name)

        # Run async health check
        loop = asyncio.new_event_loop()
        try:
            health = loop.run_until_complete(provider.health_check())
        finally:
            loop.close()

        return ProviderHealthResponse(**health)

    except Exception as e:
        logger.error(f"Health check failed for {provider_name}: {e}")
        return ProviderHealthResponse(
            provider=provider_name,
            status="unhealthy",
            base_url="",
            error=str(e),
        )


@router.post("/providers/{provider_name}/test", response=TestProviderResponse, auth=None)
def test_provider(request, provider_name: str, data: TestProviderRequest):
    """測試提供者連接"""
    if not LLMProviderFactory.is_registered(provider_name):
        return router.create_response(
            request,
            {"error": f"Provider '{provider_name}' not found"},
            status=404,
        )

    # Build custom config if provided
    config = dict(settings.AI_CONFIG)
    if data.base_url:
        config["API_BASE"] = data.base_url
    if data.model:
        config["MODEL"] = data.model
    if data.api_key:
        config["API_KEY"] = data.api_key

    try:
        # Create provider with custom config (don't cache)
        provider = LLMProviderFactory.create(provider_name, config=config, use_cache=False)

        # Run test chat
        start_time = time.time()
        loop = asyncio.new_event_loop()
        try:
            response = loop.run_until_complete(
                provider.chat(
                    messages=[{"role": "user", "content": data.test_message}],
                    max_tokens=20,
                )
            )
        finally:
            loop.close()

        latency_ms = int((time.time() - start_time) * 1000)

        return TestProviderResponse(
            success=True,
            provider=provider_name,
            message="Provider connection successful",
            latency_ms=latency_ms,
            model_response=response.content[:200] if response.content else "",
            model_used=response.model,
        )

    except LLMConnectionError as e:
        return TestProviderResponse(
            success=False,
            provider=provider_name,
            message=f"Connection failed: {e}",
        )

    except LLMTimeoutError as e:
        return TestProviderResponse(
            success=False,
            provider=provider_name,
            message=f"Request timeout: {e}",
        )

    except Exception as e:
        logger.error(f"Provider test failed for {provider_name}: {e}")
        return TestProviderResponse(
            success=False,
            provider=provider_name,
            message=f"Test failed: {e}",
        )
