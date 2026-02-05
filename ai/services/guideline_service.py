"""
Guideline Service - Classification guideline management with version control.

This module provides business logic for:
- Creating and managing classification guidelines
- Version control (creating new versions from existing)
- Status workflow (draft → testing → approved → archived)
- Template rendering with report data
- Testing guidelines against sample reports
"""

import logging
import re
from datetime import datetime
from typing import Any

from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import QuerySet

from ai.models import ClassificationGuideline

User = get_user_model()
logger = logging.getLogger(__name__)


class GuidelineServiceError(Exception):
    """Base exception for guideline service errors."""

    pass


class GuidelineNotFoundError(GuidelineServiceError):
    """Raised when a guideline is not found."""

    pass


class GuidelineStatusError(GuidelineServiceError):
    """Raised when a status transition is invalid."""

    pass


class GuidelineVersionError(GuidelineServiceError):
    """Raised when version control operation fails."""

    pass


class GuidelineService:
    """
    Service class for classification guideline operations.

    Provides CRUD operations with version control and status workflow
    management for AI classification guidelines.
    """

    # Template variable pattern for validation
    TEMPLATE_VARIABLES = ["content_raw", "imaging_findings", "impression"]
    VARIABLE_PATTERN = re.compile(r"\{\{(\w+)\}\}")

    @classmethod
    def create_guideline(
        cls,
        name: str,
        prompt_template: str,
        categories: list[str],
        user: Any,
        description: str = "",
        model_config: dict | None = None,
    ) -> ClassificationGuideline:
        """
        Create a new classification guideline.

        Args:
            name: Guideline name
            prompt_template: Prompt template with variables
            categories: List of classification categories
            user: User creating the guideline
            description: Optional description
            model_config: Optional LLM configuration

        Returns:
            ClassificationGuideline: The created guideline

        Raises:
            GuidelineServiceError: If creation fails
        """
        # Validate template
        cls._validate_template(prompt_template)

        # Validate categories
        if not categories or len(categories) < 2:
            raise GuidelineServiceError("At least 2 categories are required")

        guideline = ClassificationGuideline.objects.create(
            name=name,
            description=description,
            prompt_template=prompt_template,
            categories=categories,
            model_config=model_config or {},
            created_by=user,
            status=ClassificationGuideline.STATUS_DRAFT,
            version=1,
            is_current=True,
        )

        logger.info(f"Created guideline: {guideline.id} - {name}")
        return guideline

    @classmethod
    def get_guideline(cls, guideline_id: str) -> ClassificationGuideline:
        """
        Get a guideline by ID.

        Args:
            guideline_id: UUID of the guideline

        Returns:
            ClassificationGuideline: The guideline

        Raises:
            GuidelineNotFoundError: If guideline not found
        """
        try:
            return ClassificationGuideline.objects.get(id=guideline_id)
        except ClassificationGuideline.DoesNotExist as exc:
            raise GuidelineNotFoundError(f"Guideline {guideline_id} not found") from exc

    @classmethod
    def get_guidelines_queryset(
        cls,
        user: Any,
        status: str | None = None,
        is_current: bool | None = None,
        q: str | None = None,
    ) -> QuerySet[ClassificationGuideline]:
        """
        Get filtered queryset of guidelines.

        Args:
            user: User requesting the guidelines
            status: Filter by status
            is_current: Filter by current version flag
            q: Search query for name/description

        Returns:
            QuerySet: Filtered guidelines
        """
        queryset = ClassificationGuideline.objects.select_related(
            "created_by", "approved_by"
        ).order_by("-updated_at")

        if status:
            queryset = queryset.filter(status=status)

        if is_current is not None:
            queryset = queryset.filter(is_current=is_current)

        if q:
            queryset = queryset.filter(name__icontains=q) | queryset.filter(
                description__icontains=q
            )

        return queryset

    @classmethod
    def update_guideline(
        cls,
        guideline_id: str,
        user: Any,
        name: str | None = None,
        description: str | None = None,
        prompt_template: str | None = None,
        categories: list[str] | None = None,
        model_config: dict | None = None,
    ) -> ClassificationGuideline:
        """
        Update a guideline (only allowed for draft status).

        Args:
            guideline_id: UUID of the guideline
            user: User performing the update
            name: New name (optional)
            description: New description (optional)
            prompt_template: New template (optional)
            categories: New categories (optional)
            model_config: New model config (optional)

        Returns:
            ClassificationGuideline: Updated guideline

        Raises:
            GuidelineStatusError: If guideline is not in draft status
        """
        guideline = cls.get_guideline(guideline_id)

        if guideline.status != ClassificationGuideline.STATUS_DRAFT:
            raise GuidelineStatusError(
                f"Cannot update guideline in status: {guideline.status}. "
                "Create a new version instead."
            )

        if name is not None:
            guideline.name = name
        if description is not None:
            guideline.description = description
        if prompt_template is not None:
            cls._validate_template(prompt_template)
            guideline.prompt_template = prompt_template
        if categories is not None:
            if len(categories) < 2:
                raise GuidelineServiceError("At least 2 categories are required")
            guideline.categories = categories
        if model_config is not None:
            guideline.model_config = model_config

        guideline.save()
        logger.info(f"Updated guideline: {guideline_id}")
        return guideline

    @classmethod
    @transaction.atomic
    def create_new_version(
        cls,
        guideline_id: str,
        user: Any,
        prompt_template: str | None = None,
        categories: list[str] | None = None,
        model_config: dict | None = None,
    ) -> ClassificationGuideline:
        """
        Create a new version of an existing guideline.

        The old version is marked as not current. Only approved guidelines
        can have new versions created.

        Args:
            guideline_id: UUID of the parent guideline
            user: User creating the new version
            prompt_template: New template (optional, copies from parent)
            categories: New categories (optional, copies from parent)
            model_config: New model config (optional, copies from parent)

        Returns:
            ClassificationGuideline: The new version

        Raises:
            GuidelineStatusError: If parent guideline is not approved
        """
        parent = cls.get_guideline(guideline_id)

        if parent.status != ClassificationGuideline.STATUS_APPROVED:
            raise GuidelineStatusError("Can only create new versions from approved guidelines")

        # Mark parent as not current
        parent.is_current = False
        parent.save(update_fields=["is_current"])

        # Create new version
        new_version = ClassificationGuideline.objects.create(
            name=parent.name,
            description=parent.description,
            prompt_template=prompt_template or parent.prompt_template,
            categories=categories or parent.categories,
            model_config=model_config or parent.model_config,
            version=parent.version + 1,
            parent_version=parent,
            is_current=True,
            status=ClassificationGuideline.STATUS_DRAFT,
            created_by=user,
        )

        logger.info(f"Created new version {new_version.version} of guideline {parent.name}")
        return new_version

    @classmethod
    def set_status_testing(cls, guideline_id: str, user: Any) -> ClassificationGuideline:
        """
        Set guideline status to testing.

        Args:
            guideline_id: UUID of the guideline
            user: User performing the action

        Returns:
            ClassificationGuideline: Updated guideline

        Raises:
            GuidelineStatusError: If current status is not draft
        """
        guideline = cls.get_guideline(guideline_id)

        if guideline.status != ClassificationGuideline.STATUS_DRAFT:
            raise GuidelineStatusError(
                f"Can only move to testing from draft. Current: {guideline.status}"
            )

        guideline.status = ClassificationGuideline.STATUS_TESTING
        guideline.save(update_fields=["status", "updated_at"])
        logger.info(f"Guideline {guideline_id} moved to testing status")
        return guideline

    @classmethod
    def approve_guideline(cls, guideline_id: str, user: Any) -> ClassificationGuideline:
        """
        Approve a guideline for production use.

        Args:
            guideline_id: UUID of the guideline
            user: User performing the approval

        Returns:
            ClassificationGuideline: Approved guideline

        Raises:
            GuidelineStatusError: If current status is not testing
        """
        guideline = cls.get_guideline(guideline_id)

        if guideline.status != ClassificationGuideline.STATUS_TESTING:
            raise GuidelineStatusError(
                f"Can only approve from testing. Current: {guideline.status}"
            )

        guideline.status = ClassificationGuideline.STATUS_APPROVED
        guideline.approved_by = user
        guideline.approved_at = datetime.now()
        guideline.save(update_fields=["status", "approved_by", "approved_at", "updated_at"])

        logger.info(f"Guideline {guideline_id} approved by {user}")
        return guideline

    @classmethod
    def archive_guideline(cls, guideline_id: str, user: Any) -> ClassificationGuideline:
        """
        Archive a guideline.

        Args:
            guideline_id: UUID of the guideline
            user: User performing the action

        Returns:
            ClassificationGuideline: Archived guideline
        """
        guideline = cls.get_guideline(guideline_id)

        if guideline.status == ClassificationGuideline.STATUS_ARCHIVED:
            raise GuidelineStatusError("Guideline is already archived")

        guideline.status = ClassificationGuideline.STATUS_ARCHIVED
        guideline.is_current = False
        guideline.save(update_fields=["status", "is_current", "updated_at"])

        logger.info(f"Guideline {guideline_id} archived")
        return guideline

    @classmethod
    def render_prompt(
        cls,
        guideline: ClassificationGuideline,
        content_raw: str | None = None,
        imaging_findings: str | None = None,
        impression: str | None = None,
    ) -> str:
        """
        Render the prompt template with report data.

        Args:
            guideline: The guideline containing the template
            content_raw: Raw report content
            imaging_findings: Imaging findings section
            impression: Impression/diagnosis section

        Returns:
            str: Rendered prompt ready for LLM
        """
        template = guideline.prompt_template

        # Replace variables
        replacements = {
            "content_raw": content_raw or "",
            "imaging_findings": imaging_findings or "",
            "impression": impression or "",
        }

        for var, value in replacements.items():
            template = template.replace(f"{{{{{var}}}}}", value)

        # Add category information
        categories_str = ", ".join(guideline.categories)
        if "{{categories}}" in template:
            template = template.replace("{{categories}}", categories_str)

        return template

    @classmethod
    def get_version_history(cls, guideline_id: str) -> list[ClassificationGuideline]:
        """
        Get the version history of a guideline.

        Args:
            guideline_id: UUID of any version in the chain

        Returns:
            list: All versions from newest to oldest
        """
        guideline = cls.get_guideline(guideline_id)

        # Find the root (first version)
        root = guideline
        while root.parent_version:
            root = root.parent_version

        # Collect all versions
        versions = [root]
        current = root
        while True:
            children = list(current.child_versions.all())
            if not children:
                break
            current = children[0]  # Should only be one child
            versions.append(current)

        # Return newest first
        return list(reversed(versions))

    @classmethod
    def _validate_template(cls, template: str) -> None:
        """
        Validate a prompt template.

        Args:
            template: The template string to validate

        Raises:
            GuidelineServiceError: If template is invalid
        """
        if not template or not template.strip():
            raise GuidelineServiceError("Template cannot be empty")

        # Check for at least one valid variable
        found_vars = cls.VARIABLE_PATTERN.findall(template)
        valid_vars = [v for v in found_vars if v in cls.TEMPLATE_VARIABLES]

        if not valid_vars:
            raise GuidelineServiceError(
                f"Template must contain at least one variable: "
                f"{{{{{', '.join(cls.TEMPLATE_VARIABLES)}}}}}"
            )

        # Check for invalid variables
        invalid_vars = [
            v for v in found_vars if v not in cls.TEMPLATE_VARIABLES and v != "categories"
        ]
        if invalid_vars:
            logger.warning(f"Template contains unknown variables: {invalid_vars}")
