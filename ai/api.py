"""
AI API - Chat, analysis, and prompt template endpoints.
"""

import asyncio
import logging

from django.db.models import Q
from django.shortcuts import get_object_or_404
from ninja import Router
from ninja_jwt.authentication import JWTAuth

from ai.models import PromptTemplate
from ai.schemas import (
    AIHealthResponse,
    BatchAnalysisRequest,
    BatchAnalysisResponse,
    ConversationChatRequest,
    ConversationChatResponse,
    CreatePromptTemplateRequest,
    PromptTemplateDetailResponse,
    PromptTemplateListItem,
    QuickChatRequest,
    QuickChatResponse,
    SingleAnalysisRequest,
    SingleAnalysisResponse,
    UpdatePromptTemplateRequest,
)
from ai.services import LLMConnectionError, LLMTimeoutError
from ai.services.llm_service import get_llm_service

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
