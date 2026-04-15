"""
Batch Analysis Service - Batch AI analysis execution and management.

This module provides business logic for:
- Creating batch analysis tasks
- Executing batch analysis (called by funboost worker)
- Processing individual reports with LLM
- Managing annotation versioning (deprecating old results)
"""

import asyncio
import json
import logging
from typing import Any

from django.db import transaction
from django.db.models import F
from django.utils import timezone

from ai.models import BatchAnalysisTask, ClassificationGuideline
from ai.services.guideline_service import GuidelineNotFoundError, GuidelineService
from ai.services.llm_service import LLMConnectionError, LLMTimeoutError, get_llm_service
from report.models import AIAnnotation, Report

logger = logging.getLogger(__name__)


class BatchAnalysisError(Exception):
    """Base exception for batch analysis errors."""

    pass


class BatchAnalysisTaskNotFoundError(BatchAnalysisError):
    """Raised when a batch task is not found."""

    pass


class BatchAnalysisService:
    """
    Service class for batch AI analysis operations.

    Handles creation and execution of batch analysis tasks,
    integrating with funboost for async processing.
    """

    MAX_BATCH_SIZE = 9999
    ANNOTATION_TYPE = "Classification"

    @classmethod
    def create_task(
        cls,
        guideline_id: str,
        report_uids: list[str],
        user: Any,
        project_id: str | None = None,
    ) -> BatchAnalysisTask:
        """
        Create a new batch analysis task.

        Args:
            guideline_id: UUID of the classification guideline
            report_uids: List of report UIDs to analyze
            user: User creating the task
            project_id: Optional project ID to associate with

        Returns:
            BatchAnalysisTask: The created task

        Raises:
            BatchAnalysisError: If validation fails
        """
        # Validate guideline
        try:
            guideline = GuidelineService.get_guideline(guideline_id)
        except GuidelineNotFoundError as exc:
            raise BatchAnalysisError(f"Guideline not found: {guideline_id}") from exc

        if guideline.status != ClassificationGuideline.STATUS_APPROVED:
            raise BatchAnalysisError(
                f"Guideline must be approved. Current status: {guideline.status}"
            )

        # Validate report count
        unique_uids = list(dict.fromkeys(report_uids))  # Remove duplicates
        if not unique_uids:
            raise BatchAnalysisError("No report UIDs provided")

        if len(unique_uids) > cls.MAX_BATCH_SIZE:
            raise BatchAnalysisError(
                f"Batch size {len(unique_uids)} exceeds max {cls.MAX_BATCH_SIZE}"
            )

        # Verify reports exist
        existing_reports = set(
            Report.objects.filter(uid__in=unique_uids).values_list("uid", flat=True)
        )
        missing_uids = set(unique_uids) - existing_reports
        if missing_uids:
            logger.warning(f"Missing reports: {list(missing_uids)[:10]}...")

        # Create task
        task = BatchAnalysisTask.objects.create(
            guideline=guideline,
            project_id=project_id,
            report_uids=list(existing_reports),  # Only include existing reports
            total_count=len(existing_reports),
            created_by=user,
            status=BatchAnalysisTask.STATUS_PENDING,
        )

        logger.info(
            f"Created batch task {task.id} for {len(existing_reports)} reports "
            f"using guideline {guideline.name}"
        )
        return task

    @classmethod
    def start_task(cls, task_id: str) -> str:
        """
        Start a batch analysis task asynchronously.

        Falls back to synchronous execution if funboost is not available.

        Args:
            task_id: UUID of the BatchAnalysisTask

        Returns:
            str: The funboost task tracking ID or 'sync'
        """
        task = cls.get_task(task_id)
        if task.status != BatchAnalysisTask.STATUS_PENDING:
            raise BatchAnalysisError(f"Task {task_id} is not pending. Status: {task.status}")

        try:
            from ai.tasks import start_batch_analysis

            funboost_task_id = start_batch_analysis(str(task_id))
            task.funboost_task_id = funboost_task_id
            task.save(update_fields=["funboost_task_id"])
            return funboost_task_id
        except (ImportError, OSError, Exception) as e:
            logger.warning(f"Funboost unavailable ({e}), executing synchronously")
            import threading

            thread = threading.Thread(
                target=cls.execute_batch_analysis, args=(str(task_id),)
            )
            thread.daemon = True
            thread.start()
            return "sync"

    @classmethod
    def get_task(cls, task_id: str) -> BatchAnalysisTask:
        """
        Get a batch task by ID.

        Args:
            task_id: UUID of the task

        Returns:
            BatchAnalysisTask: The task

        Raises:
            BatchAnalysisTaskNotFoundError: If task not found
        """
        try:
            return BatchAnalysisTask.objects.select_related("guideline", "created_by").get(
                id=task_id
            )
        except BatchAnalysisTask.DoesNotExist as exc:
            raise BatchAnalysisTaskNotFoundError(f"Batch task {task_id} not found") from exc

    @classmethod
    def execute_batch_analysis(cls, task_id: str) -> dict[str, Any]:
        """
        Execute a batch analysis task (called by funboost worker).

        This is the main entry point for batch processing. It iterates
        through all reports and processes them with the LLM.

        Args:
            task_id: UUID of the BatchAnalysisTask

        Returns:
            dict: Summary of processing results
        """
        task = cls.get_task(task_id)

        # Mark as processing
        task.status = BatchAnalysisTask.STATUS_PROCESSING
        task.started_at = timezone.now()
        task.save(update_fields=["status", "started_at"])

        logger.info(f"Starting batch analysis for task {task_id}")

        results_summary: dict[str, int] = {}
        error_details: list[dict] = []

        try:
            # Process each report
            for report_uid in task.report_uids:
                try:
                    result = cls.process_single_report(
                        report_uid=report_uid,
                        guideline_id=str(task.guideline_id),
                        batch_task_id=str(task_id),
                    )

                    # Update summary
                    classification = result.get("classification", "unknown")
                    results_summary[classification] = results_summary.get(classification, 0) + 1

                    # Update progress
                    BatchAnalysisTask.objects.filter(id=task_id).update(
                        processed_count=F("processed_count") + 1,
                        success_count=F("success_count") + 1,
                    )

                except Exception as e:
                    logger.error(f"Error processing report {report_uid}: {e}")
                    error_details.append(
                        {
                            "report_uid": report_uid,
                            "error": str(e),
                        }
                    )

                    # Update error count
                    BatchAnalysisTask.objects.filter(id=task_id).update(
                        processed_count=F("processed_count") + 1,
                        error_count=F("error_count") + 1,
                    )

            # Refresh and mark as completed
            task.refresh_from_db()
            task.status = BatchAnalysisTask.STATUS_COMPLETED
            task.completed_at = timezone.now()
            task.results_summary = results_summary
            task.error_details = error_details
            task.save(update_fields=["status", "completed_at", "results_summary", "error_details"])

            logger.info(
                f"Batch analysis completed for task {task_id}: "
                f"{task.success_count} success, {task.error_count} errors"
            )

            return {
                "task_id": str(task_id),
                "status": "completed",
                "total_count": task.total_count,
                "success_count": task.success_count,
                "error_count": task.error_count,
                "results_summary": results_summary,
            }

        except Exception as e:
            # Mark as failed
            task.status = BatchAnalysisTask.STATUS_FAILED
            task.completed_at = timezone.now()
            task.error_details = [{"error": str(e)}]
            task.save(update_fields=["status", "completed_at", "error_details"])
            logger.exception(f"Batch analysis failed for task {task_id}")
            raise

    @classmethod
    def process_single_report(
        cls,
        report_uid: str,
        guideline_id: str,
        batch_task_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Process a single report with the LLM.

        Args:
            report_uid: UID of the report to analyze
            guideline_id: UUID of the ClassificationGuideline
            batch_task_id: Optional parent batch task ID

        Returns:
            dict: Analysis result including classification and confidence
        """
        # Get report
        try:
            report = Report.objects.get(uid=report_uid)
        except Report.DoesNotExist as exc:
            raise BatchAnalysisError(f"Report {report_uid} not found") from exc

        # Get guideline
        guideline = GuidelineService.get_guideline(guideline_id)

        # Render prompt
        prompt = GuidelineService.render_prompt(
            guideline=guideline,
            content_raw=report.content_raw,
            imaging_findings=report.imaging_findings,
            impression=report.impression,
        )

        # Build messages for LLM
        system_prompt = cls._build_system_prompt(guideline)
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ]

        # Get LLM response
        llm = get_llm_service()
        model_config = guideline.model_config or {}

        try:
            loop = asyncio.new_event_loop()
            try:
                response = loop.run_until_complete(
                    llm.chat(
                        messages=messages,
                        model=model_config.get("model"),
                        temperature=model_config.get("temperature", 0.3),
                    )
                )
            finally:
                loop.close()

            # Parse response (multi-question or single-classification)
            questions = getattr(guideline, "questions", None) or []
            classification, confidence, structured_answers = cls._parse_llm_response(
                response.content, guideline.categories, questions=questions or None
            )

            # Create annotation
            annotation = cls._create_annotation(
                report=report,
                guideline=guideline,
                batch_task_id=batch_task_id,
                classification=classification,
                confidence=confidence,
                raw_response=response.content,
                structured_answers=structured_answers,
            )

            result: dict[str, Any] = {
                "report_uid": report_uid,
                "classification": classification,
                "confidence": confidence,
                "annotation_id": str(annotation.id),
            }
            if structured_answers:
                result["structured_answers"] = structured_answers
            return result

        except (LLMConnectionError, LLMTimeoutError) as e:
            raise BatchAnalysisError(f"LLM error for report {report_uid}: {e}") from e

    @classmethod
    def _build_system_prompt(cls, guideline: ClassificationGuideline) -> str:
        """Build the system prompt for classification.

        Supports two modes:
        - Single-classification: when guideline.questions is empty
        - Multi-question: when guideline.questions is defined
        """
        questions = getattr(guideline, "questions", None) or []
        if questions:
            return cls._build_multi_question_prompt(guideline, questions)

        categories_str = ", ".join(guideline.categories)
        return (
            "你是專業的醫學影像報告分類助手。請根據報告內容進行分類。\n\n"
            f"可用的分類類別: {categories_str}\n\n"
            "請以下列 JSON 格式回應:\n"
            '{"classification": "<類別>", "confidence": <0.0-1.0的數值>, "reasoning": "<簡短理由>"}\n\n'
            "只輸出 JSON，不要輸出其他文字。"
        )

    @classmethod
    def _build_multi_question_prompt(
        cls, guideline: ClassificationGuideline, questions: list[dict[str, Any]]
    ) -> str:
        """Build a multi-question system prompt."""
        lines = ["你是專業的醫學影像報告分類助手。請根據報告內容回答以下問題。\n"]
        for q in questions:
            opts = ", ".join(q["options"])
            lines.append(f"- {q['key']}: {q['label']} (選項: {opts})")
            dep = q.get("depends_on")
            if dep:
                lines.append(
                    f"  (僅在 {dep['question_key']} = {dep['expected_value']} 時回答，否則回答 N/A)"
                )
        lines.append("\n請以下列 JSON 格式回應:")
        # Build example answers
        example_keys = ", ".join(f'"{q["key"]}": "<答案>"' for q in questions)
        lines.append(
            '{"answers": {' + example_keys + "}, "
            '"confidence": <0.0-1.0的數值>, "reasoning": "<簡短理由>"}'
        )
        lines.append("\n只輸出 JSON，不要輸出其他文字。")
        return "\n".join(lines)

    @classmethod
    def _parse_llm_response(
        cls,
        response: str,
        categories: list[str],
        questions: list[dict[str, Any]] | None = None,
    ) -> tuple[str, float, dict[str, str] | None]:
        """
        Parse the LLM response to extract classification and confidence.

        Supports two modes:
        - Single-classification: returns (classification, confidence, None)
        - Multi-question: returns (primary_answer, confidence, structured_answers)

        Args:
            response: Raw LLM response
            categories: Valid categories
            questions: Optional multi-question config

        Returns:
            tuple: (classification, confidence, structured_answers_or_None)
        """
        try:
            data = json.loads(response.strip())

            # Multi-question mode
            if questions and "answers" in data:
                answers = data["answers"]
                confidence = float(data.get("confidence", 0.5))
                # Validate each answer against its question options
                validated: dict[str, str] = {}
                for q in questions:
                    key = q["key"]
                    answer = answers.get(key, "N/A")
                    options = [o.lower() for o in q["options"]]
                    if str(answer).lower() in options:
                        # Preserve original casing from options
                        for opt in q["options"]:
                            if opt.lower() == str(answer).lower():
                                answer = opt
                                break
                    validated[key] = str(answer)
                # Primary classification from first question
                primary = validated.get(questions[0]["key"], "unknown")
                return primary, min(max(confidence, 0.0), 1.0), validated

            # Single-classification mode
            classification = data.get("classification", "unknown")
            confidence = float(data.get("confidence", 0.5))

            if classification not in categories:
                for cat in categories:
                    if cat.lower() == classification.lower():
                        classification = cat
                        break
                else:
                    classification = "unknown"
                    confidence = 0.0

            return classification, min(max(confidence, 0.0), 1.0), None

        except (json.JSONDecodeError, ValueError, TypeError):
            response_lower = response.lower()
            for cat in categories:
                if cat.lower() in response_lower:
                    return cat, 0.5, None
            return "unknown", 0.0, None

    @classmethod
    def _create_annotation(
        cls,
        report: Report,
        guideline: ClassificationGuideline,
        batch_task_id: str | None,
        classification: str,
        confidence: float,
        raw_response: str,
        structured_answers: dict[str, str] | None = None,
    ) -> AIAnnotation:
        """Create an AI annotation record."""
        metadata: dict[str, Any] = {
            "raw_response": raw_response,
            "reasoning": cls._extract_reasoning(raw_response),
        }
        if structured_answers:
            metadata["structured_answers"] = structured_answers
        return AIAnnotation.objects.create(
            report=report,
            annotation_type=cls.ANNOTATION_TYPE,
            content=classification,
            metadata=metadata,
            guideline=guideline,
            guideline_version=guideline.version,
            batch_task_id=batch_task_id,
            confidence_score=confidence,
            is_deprecated=False,
        )

    @classmethod
    def _extract_reasoning(cls, response: str) -> str:
        """Extract reasoning from LLM response."""
        try:
            data = json.loads(response.strip())
            return data.get("reasoning", "")
        except (json.JSONDecodeError, ValueError):
            return ""

    @classmethod
    @transaction.atomic
    def deprecate_old_annotations(
        cls,
        guideline_id: str,
        new_version: int,
        report_uids: list[str] | None = None,
    ) -> dict[str, Any]:
        """
        Mark old annotations as deprecated after re-analysis.

        Args:
            guideline_id: UUID of the ClassificationGuideline
            new_version: The new version number
            report_uids: Optional list of specific reports (all if None)

        Returns:
            dict: Count of deprecated annotations
        """
        queryset = AIAnnotation.objects.filter(
            guideline_id=guideline_id,
            guideline_version__lt=new_version,
            is_deprecated=False,
        )

        if report_uids:
            queryset = queryset.filter(report__uid__in=report_uids)

        count = queryset.update(
            is_deprecated=True,
            deprecated_at=timezone.now(),
            deprecated_reason=f"Re-analyzed with guideline version {new_version}",
        )

        logger.info(
            f"Deprecated {count} annotations for guideline {guideline_id}, version < {new_version}"
        )

        return {
            "deprecated_count": count,
            "guideline_id": guideline_id,
            "new_version": new_version,
        }

    @classmethod
    def cancel_task(cls, task_id: str) -> BatchAnalysisTask:
        """
        Cancel a pending or processing task.

        Args:
            task_id: UUID of the task

        Returns:
            BatchAnalysisTask: The cancelled task
        """
        task = cls.get_task(task_id)

        if task.status not in [
            BatchAnalysisTask.STATUS_PENDING,
            BatchAnalysisTask.STATUS_PROCESSING,
        ]:
            raise BatchAnalysisError(f"Cannot cancel task in status: {task.status}")

        task.status = BatchAnalysisTask.STATUS_CANCELLED
        task.completed_at = timezone.now()
        task.save(update_fields=["status", "completed_at"])

        logger.info(f"Cancelled batch task {task_id}")
        return task
