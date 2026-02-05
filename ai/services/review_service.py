"""
Review Service - Physician review workflow management.

This module provides business logic for:
- Creating review tasks with sampling configuration
- Generating stratified samples
- Assigning reviewers (single and double-blind)
- Collecting and processing feedback
- Calculating review metrics (FP rate, Cohen's Kappa)
- Handling disagreements and arbitration
"""

import logging
from typing import Any

from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Count, F, QuerySet
from django.utils import timezone

from ai.models import (
    BatchAnalysisTask,
    ReviewerAssignment,
    ReviewFeedback,
    ReviewSample,
    ReviewTask,
)
from ai.services.batch_analysis_service import BatchAnalysisService
from ai.services.sampling_service import SamplingService
from report.models import AIAnnotation

User = get_user_model()
logger = logging.getLogger(__name__)


class ReviewServiceError(Exception):
    """Base exception for review service errors."""

    pass


class ReviewTaskNotFoundError(ReviewServiceError):
    """Raised when a review task is not found."""

    pass


class ReviewSampleNotFoundError(ReviewServiceError):
    """Raised when a review sample is not found."""

    pass


class ReviewService:
    """
    Service class for physician review workflow operations.

    Manages the complete review lifecycle including task creation,
    sample generation, feedback collection, and metrics calculation.
    """

    @classmethod
    def create_review_task(
        cls,
        name: str,
        batch_task_id: str,
        sample_size: int,
        user: Any,
        review_mode: str = ReviewTask.REVIEW_MODE_SINGLE,
        sampling_config: dict | None = None,
        fp_threshold: float = 0.20,
    ) -> ReviewTask:
        """
        Create a new review task.

        Args:
            name: Task name
            batch_task_id: UUID of the completed BatchAnalysisTask
            sample_size: Number of samples to review
            user: User creating the task
            review_mode: "single" or "double_blind"
            sampling_config: Sampling strategy configuration
            fp_threshold: False positive rate threshold

        Returns:
            ReviewTask: The created task

        Raises:
            ReviewServiceError: If validation fails
        """
        # Validate batch task
        batch_task = BatchAnalysisService.get_task(batch_task_id)
        if batch_task.status != BatchAnalysisTask.STATUS_COMPLETED:
            raise ReviewServiceError(
                f"Batch task must be completed. Current status: {batch_task.status}"
            )

        # Validate sample size
        total_annotations = AIAnnotation.objects.filter(
            batch_task_id=batch_task_id,
            is_deprecated=False,
        ).count()

        if sample_size > total_annotations:
            logger.warning(
                f"Requested sample size {sample_size} exceeds available "
                f"annotations {total_annotations}. Using {total_annotations}."
            )
            sample_size = total_annotations

        # Determine required reviewers
        required_reviewers = 2 if review_mode == ReviewTask.REVIEW_MODE_DOUBLE_BLIND else 1

        task = ReviewTask.objects.create(
            name=name,
            batch_task=batch_task,
            sample_size=sample_size,
            sampling_config=sampling_config or {},
            review_mode=review_mode,
            required_reviewers=required_reviewers,
            fp_threshold=fp_threshold,
            created_by=user,
            status=ReviewTask.STATUS_PENDING,
        )

        logger.info(f"Created review task {task.id} for batch {batch_task_id}")
        return task

    @classmethod
    def get_review_task(cls, task_id: str) -> ReviewTask:
        """
        Get a review task by ID.

        Args:
            task_id: UUID of the task

        Returns:
            ReviewTask: The task

        Raises:
            ReviewTaskNotFoundError: If task not found
        """
        try:
            return ReviewTask.objects.select_related("batch_task", "created_by").get(id=task_id)
        except ReviewTask.DoesNotExist as exc:
            raise ReviewTaskNotFoundError(f"Review task {task_id} not found") from exc

    @classmethod
    @transaction.atomic
    def generate_samples(cls, review_task_id: str) -> dict[str, Any]:
        """
        Generate samples for a review task based on sampling configuration.

        Args:
            review_task_id: UUID of the ReviewTask

        Returns:
            dict: Summary including sample count and distribution
        """
        task = cls.get_review_task(review_task_id)

        if task.status != ReviewTask.STATUS_PENDING:
            raise ReviewServiceError(
                f"Can only generate samples for pending tasks. Status: {task.status}"
            )

        # Get annotations from batch task
        annotations = AIAnnotation.objects.filter(
            batch_task_id=task.batch_task_id,
            is_deprecated=False,
        ).select_related("report")

        # Parse sampling config
        config = task.sampling_config
        strategy = config.get("strategy", "random")
        strata_fields = config.get("strata_fields", [])

        # Execute sampling
        if strategy == "stratified" and strata_fields:
            if len(strata_fields) == 1:
                samples, distribution = SamplingService.stratified_sample(
                    annotations=annotations,
                    sample_size=task.sample_size,
                    strata_field=strata_fields[0],
                )
            else:
                samples, distribution = SamplingService.multi_stratified_sample(
                    annotations=annotations,
                    sample_size=task.sample_size,
                    strata_fields=strata_fields,
                )
        elif strategy == "confidence_weighted":
            samples = SamplingService.confidence_weighted_sample(
                annotations=annotations,
                sample_size=task.sample_size,
                low_confidence_weight=config.get("low_confidence_weight", 2.0),
                low_confidence_threshold=config.get("low_confidence_threshold", 0.7),
            )
            distribution = {}
        else:  # random
            samples = SamplingService.random_sample(
                annotations=annotations,
                sample_size=task.sample_size,
            )
            distribution = {}

        # Create ReviewSample records
        review_samples = []
        for ann in samples:
            stratum = SamplingService.get_stratum_label(ann, strata_fields) if strata_fields else ""

            review_samples.append(
                ReviewSample(
                    review_task=task,
                    ai_annotation=ann,
                    stratum=stratum,
                    ai_classification=ann.content,
                    ai_confidence=ann.confidence_score,
                    status=ReviewSample.STATUS_PENDING,
                )
            )

        ReviewSample.objects.bulk_create(review_samples)

        # Update task status
        task.status = ReviewTask.STATUS_IN_PROGRESS
        task.save(update_fields=["status"])

        logger.info(f"Generated {len(review_samples)} samples for review task {review_task_id}")

        return {
            "task_id": str(review_task_id),
            "sample_count": len(review_samples),
            "distribution": distribution,
        }

    @classmethod
    @transaction.atomic
    def assign_reviewers(
        cls,
        review_task_id: str,
        reviewer_ids: list[str],
        arbitrator_id: str | None = None,
    ) -> list[ReviewerAssignment]:
        """
        Assign reviewers to a review task.

        For double-blind mode, first two reviewers are primary and secondary.
        An optional arbitrator can be assigned for conflict resolution.

        Args:
            review_task_id: UUID of the ReviewTask
            reviewer_ids: List of user IDs to assign
            arbitrator_id: Optional arbitrator user ID

        Returns:
            list: Created ReviewerAssignment records
        """
        task = cls.get_review_task(review_task_id)

        if task.review_mode == ReviewTask.REVIEW_MODE_DOUBLE_BLIND:
            if len(reviewer_ids) < 2:
                raise ReviewServiceError("Double-blind mode requires at least 2 reviewers")

        sample_count = task.samples.count()
        assignments = []

        for i, reviewer_id in enumerate(reviewer_ids):
            try:
                user = User.objects.get(id=reviewer_id)
            except User.DoesNotExist as exc:
                raise ReviewServiceError(f"User {reviewer_id} not found") from exc

            # Determine role
            if i == 0:
                role = ReviewerAssignment.ROLE_PRIMARY
            elif i == 1 and task.review_mode == ReviewTask.REVIEW_MODE_DOUBLE_BLIND:
                role = ReviewerAssignment.ROLE_SECONDARY
            else:
                continue  # Skip additional reviewers

            assignment = ReviewerAssignment.objects.create(
                review_task=task,
                reviewer=user,
                role=role,
                total_assigned=sample_count,
                can_view_others=False,  # Double-blind
            )
            assignments.append(assignment)

        # Add arbitrator if provided
        if arbitrator_id and task.review_mode == ReviewTask.REVIEW_MODE_DOUBLE_BLIND:
            try:
                arbitrator = User.objects.get(id=arbitrator_id)
            except User.DoesNotExist as exc:
                raise ReviewServiceError(f"Arbitrator {arbitrator_id} not found") from exc

            assignment = ReviewerAssignment.objects.create(
                review_task=task,
                reviewer=arbitrator,
                role=ReviewerAssignment.ROLE_ARBITRATOR,
                total_assigned=0,  # Will be updated when conflicts arise
                can_view_others=True,  # Arbitrator can see all reviews
            )
            assignments.append(assignment)

        logger.info(f"Assigned {len(assignments)} reviewers to task {review_task_id}")
        return assignments

    @classmethod
    def get_samples_for_reviewer(
        cls,
        review_task_id: str,
        reviewer_id: str,
        status: str | None = None,
    ) -> QuerySet[ReviewSample]:
        """
        Get samples assigned to a specific reviewer.

        Args:
            review_task_id: UUID of the ReviewTask
            reviewer_id: User ID of the reviewer
            status: Optional filter by sample status

        Returns:
            QuerySet: Samples for the reviewer
        """
        task = cls.get_review_task(review_task_id)

        # Get reviewer's assignment
        try:
            assignment = ReviewerAssignment.objects.get(
                review_task=task,
                reviewer_id=reviewer_id,
            )
        except ReviewerAssignment.DoesNotExist as exc:
            raise ReviewServiceError(
                f"User {reviewer_id} is not assigned to task {review_task_id}"
            ) from exc

        # Build queryset
        queryset = task.samples.select_related("ai_annotation__report")

        if status:
            queryset = queryset.filter(status=status)

        # For arbitrators, only show samples needing arbitration
        if assignment.role == ReviewerAssignment.ROLE_ARBITRATOR:
            queryset = queryset.filter(status=ReviewSample.STATUS_IN_ARBITRATION)

        return queryset

    @classmethod
    @transaction.atomic
    def submit_feedback(
        cls,
        review_task_id: str,
        sample_id: str,
        reviewer_id: str,
        is_correct: bool,
        correct_category: str | None = None,
        confidence_level: str = ReviewFeedback.CONFIDENCE_HIGH,
        notes: str = "",
    ) -> ReviewFeedback:
        """
        Submit feedback for a review sample.

        Args:
            review_task_id: UUID of the ReviewTask
            sample_id: UUID of the ReviewSample
            reviewer_id: User ID of the reviewer
            is_correct: Whether AI classification is correct
            correct_category: Correct category if AI was wrong
            confidence_level: Reviewer's confidence in their assessment
            notes: Optional notes

        Returns:
            ReviewFeedback: The created feedback

        Raises:
            ReviewServiceError: If validation fails
        """
        task = cls.get_review_task(review_task_id)

        # Get sample
        try:
            sample = ReviewSample.objects.get(id=sample_id, review_task=task)
        except ReviewSample.DoesNotExist as exc:
            raise ReviewSampleNotFoundError(f"Sample {sample_id} not found") from exc

        # Get reviewer assignment
        try:
            assignment = ReviewerAssignment.objects.get(
                review_task=task,
                reviewer_id=reviewer_id,
            )
        except ReviewerAssignment.DoesNotExist as exc:
            raise ReviewServiceError(f"User {reviewer_id} is not assigned to this task") from exc

        # Check for duplicate feedback
        if ReviewFeedback.objects.filter(
            review_sample=sample,
            reviewer_id=reviewer_id,
        ).exists():
            raise ReviewServiceError(
                f"User {reviewer_id} has already submitted feedback for this sample"
            )

        # Validate correct_category if AI was wrong
        if not is_correct and not correct_category:
            raise ReviewServiceError("correct_category is required when marking AI as incorrect")

        # Create feedback
        feedback = ReviewFeedback.objects.create(
            review_sample=sample,
            reviewer_id=reviewer_id,
            reviewer_assignment=assignment,
            is_correct=is_correct,
            correct_category=correct_category,
            confidence_level=confidence_level,
            notes=notes,
        )

        # Update assignment progress
        ReviewerAssignment.objects.filter(id=assignment.id).update(
            completed_samples=F("completed_samples") + 1
        )

        # Handle double-blind logic
        cls._handle_double_blind_completion(sample, task)

        logger.info(f"Feedback submitted by {reviewer_id} for sample {sample_id}")
        return feedback

    @classmethod
    def _handle_double_blind_completion(
        cls,
        sample: ReviewSample,
        task: ReviewTask,
    ) -> None:
        """
        Handle sample status updates for double-blind reviews.

        Checks if both reviewers have submitted and whether they agree.
        """
        if task.review_mode != ReviewTask.REVIEW_MODE_DOUBLE_BLIND:
            # Single review mode - mark as completed immediately
            sample.status = ReviewSample.STATUS_COMPLETED
            sample.save(update_fields=["status"])
            return

        # Count feedbacks for this sample
        feedback_count = sample.feedbacks.count()

        if feedback_count < 2:
            # Still waiting for second review
            sample.status = ReviewSample.STATUS_NEEDS_SECOND_REVIEW
            sample.save(update_fields=["status"])
            return

        # Both reviews submitted - check agreement
        feedbacks = list(sample.feedbacks.all())
        agreement = feedbacks[0].is_correct == feedbacks[1].is_correct

        if agreement:
            # Agreement - finalize with the consensus
            sample.status = ReviewSample.STATUS_COMPLETED
            sample.final_is_correct = feedbacks[0].is_correct
            if not feedbacks[0].is_correct:
                sample.final_correct_category = feedbacks[0].correct_category
            sample.save(update_fields=["status", "final_is_correct", "final_correct_category"])
        else:
            # Disagreement - needs arbitration
            sample.status = ReviewSample.STATUS_IN_ARBITRATION
            sample.save(update_fields=["status"])

            # Update arbitrator's assignment count
            ReviewerAssignment.objects.filter(
                review_task=task,
                role=ReviewerAssignment.ROLE_ARBITRATOR,
            ).update(total_assigned=F("total_assigned") + 1)

            logger.info(f"Sample {sample.id} requires arbitration due to disagreement")

    @classmethod
    @transaction.atomic
    def resolve_conflict(
        cls,
        review_task_id: str,
        sample_id: str,
        arbitrator_id: str,
        is_correct: bool,
        correct_category: str | None = None,
        notes: str = "",
    ) -> ReviewSample:
        """
        Resolve a conflict through arbitration.

        Args:
            review_task_id: UUID of the ReviewTask
            sample_id: UUID of the ReviewSample
            arbitrator_id: User ID of the arbitrator
            is_correct: Final determination
            correct_category: Correct category if AI was wrong
            notes: Resolution notes

        Returns:
            ReviewSample: Updated sample
        """
        task = cls.get_review_task(review_task_id)

        # Verify arbitrator
        try:
            assignment = ReviewerAssignment.objects.get(
                review_task=task,
                reviewer_id=arbitrator_id,
                role=ReviewerAssignment.ROLE_ARBITRATOR,
            )
        except ReviewerAssignment.DoesNotExist as exc:
            raise ReviewServiceError(
                f"User {arbitrator_id} is not the arbitrator for this task"
            ) from exc

        # Get sample
        try:
            sample = ReviewSample.objects.get(
                id=sample_id,
                review_task=task,
                status=ReviewSample.STATUS_IN_ARBITRATION,
            )
        except ReviewSample.DoesNotExist as exc:
            raise ReviewSampleNotFoundError(
                f"Sample {sample_id} not found or not in arbitration"
            ) from exc

        # Update sample
        sample.status = ReviewSample.STATUS_COMPLETED
        sample.final_is_correct = is_correct
        sample.final_correct_category = correct_category if not is_correct else None
        sample.final_determined_by_id = arbitrator_id
        sample.save(
            update_fields=[
                "status",
                "final_is_correct",
                "final_correct_category",
                "final_determined_by_id",
            ]
        )

        # Update arbitrator progress
        ReviewerAssignment.objects.filter(id=assignment.id).update(
            completed_samples=F("completed_samples") + 1
        )

        # Create feedback record for arbitrator
        ReviewFeedback.objects.create(
            review_sample=sample,
            reviewer_id=arbitrator_id,
            reviewer_assignment=assignment,
            is_correct=is_correct,
            correct_category=correct_category,
            confidence_level=ReviewFeedback.CONFIDENCE_HIGH,
            notes=notes,
        )

        logger.info(f"Conflict resolved for sample {sample_id} by {arbitrator_id}")
        return sample

    @classmethod
    def calculate_metrics(cls, review_task_id: str) -> dict[str, Any]:
        """
        Calculate review metrics.

        Computes:
        - False Positive rate
        - Cohen's Kappa (for double-blind)
        - Sample completion rate

        Args:
            review_task_id: UUID of the ReviewTask

        Returns:
            dict: Calculated metrics
        """
        task = cls.get_review_task(review_task_id)

        completed_samples = task.samples.filter(status=ReviewSample.STATUS_COMPLETED)
        total_completed = completed_samples.count()

        if total_completed == 0:
            return {
                "task_id": str(review_task_id),
                "total_samples": task.samples.count(),
                "completed_samples": 0,
                "fp_rate": None,
                "agreement_rate": None,
                "completion_rate": 0.0,
            }

        # Calculate FP rate (AI errors)
        incorrect_count = completed_samples.filter(final_is_correct=False).count()
        fp_rate = incorrect_count / total_completed

        # Calculate agreement rate for double-blind
        agreement_rate = None
        if task.review_mode == ReviewTask.REVIEW_MODE_DOUBLE_BLIND:
            agreement_rate = cls._calculate_agreement_rate(task)

        # Completion rate
        total_samples = task.samples.count()
        completion_rate = total_completed / total_samples if total_samples > 0 else 0

        # Update task
        task.fp_rate = fp_rate
        task.agreement_rate = agreement_rate
        task.save(update_fields=["fp_rate", "agreement_rate"])

        # Check if task is complete
        if total_completed == total_samples:
            task.status = ReviewTask.STATUS_COMPLETED
            task.completed_at = timezone.now()
            task.save(update_fields=["status", "completed_at"])

        return {
            "task_id": str(review_task_id),
            "total_samples": total_samples,
            "completed_samples": total_completed,
            "incorrect_samples": incorrect_count,
            "fp_rate": fp_rate,
            "fp_threshold": task.fp_threshold,
            "fp_passed": fp_rate <= task.fp_threshold,
            "agreement_rate": agreement_rate,
            "completion_rate": completion_rate,
        }

    @classmethod
    def _calculate_agreement_rate(cls, task: ReviewTask) -> float:
        """
        Calculate inter-rater agreement rate (simple percentage).

        For more robust measurement, Cohen's Kappa could be implemented.
        """
        samples_with_two_reviews = task.samples.annotate(feedback_count=Count("feedbacks")).filter(
            feedback_count__gte=2
        )

        if not samples_with_two_reviews.exists():
            return 0.0

        agreements = 0
        total = 0

        for sample in samples_with_two_reviews:
            feedbacks = list(sample.feedbacks.all()[:2])
            if len(feedbacks) >= 2:
                if feedbacks[0].is_correct == feedbacks[1].is_correct:
                    agreements += 1
                total += 1

        return agreements / total if total > 0 else 0.0

    @classmethod
    def get_conflicts(cls, review_task_id: str) -> QuerySet[ReviewSample]:
        """
        Get all samples with conflicting reviews.

        Args:
            review_task_id: UUID of the ReviewTask

        Returns:
            QuerySet: Samples in arbitration status
        """
        task = cls.get_review_task(review_task_id)
        return task.samples.filter(status=ReviewSample.STATUS_IN_ARBITRATION).select_related(
            "ai_annotation__report"
        )
