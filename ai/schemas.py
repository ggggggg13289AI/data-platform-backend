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
