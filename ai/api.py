"""
AI API - Prompt templates endpoints.
"""

import logging

from django.db.models import Q
from django.shortcuts import get_object_or_404
from ninja import Router
from ninja_jwt.authentication import JWTAuth

from ai.models import PromptTemplate
from ai.schemas import (
    CreatePromptTemplateRequest,
    PromptTemplateDetailResponse,
    PromptTemplateListItem,
    UpdatePromptTemplateRequest,
)

logger = logging.getLogger(__name__)

router = Router(auth=JWTAuth())


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
