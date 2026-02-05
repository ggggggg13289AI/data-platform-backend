"""
Funboost Tasks - Distributed task definitions for AI workflow.

This module defines async tasks using funboost for:
- Batch AI analysis of reports
- Review sample generation
- Long-running background operations

Usage (development - SQLite, no Redis required):
    # Start worker
    python -c "from ai.tasks import run_batch_analysis; run_batch_analysis.consume()"

Usage (production - Redis):
    FUNBOOST_BROKER=REDIS_ACK_ABLE python -c "from ai.tasks import run_batch_analysis; run_batch_analysis.consume()"

    # Or start all workers
    python -c "from funboost import BoostersManager; import ai.tasks; BoostersManager.consume_all_queues()"
"""

import logging
from typing import Any

from django.conf import settings
from funboost import BoosterParams, BrokerEnum, boost

logger = logging.getLogger(__name__)


def get_broker() -> BrokerEnum:
    """
    Get the appropriate broker based on configuration.

    Returns:
        BrokerEnum: SQLITE_QUEUE for development, REDIS_ACK_ABLE for production
    """
    broker_name = settings.FUNBOOST_CONFIG["BROKER_KIND"]
    return getattr(BrokerEnum, broker_name, BrokerEnum.SQLITE_QUEUE)


def get_booster_params(
    queue_name: str,
    concurrent_num: int | None = None,
    qps: float | None = None,
    max_retry_times: int | None = None,
    retry_interval: int | None = None,
    is_using_rpc_mode: bool = False,
) -> BoosterParams:
    """
    Create BoosterParams with configuration from settings.

    Args:
        queue_name: Name of the task queue
        concurrent_num: Override concurrent worker count
        qps: Override queries per second limit
        max_retry_times: Override max retry count
        retry_interval: Override retry interval in seconds
        is_using_rpc_mode: Enable RPC mode for result tracking

    Returns:
        BoosterParams: Configured parameters for the task
    """
    config = settings.FUNBOOST_CONFIG
    return BoosterParams(
        queue_name=queue_name,
        broker_kind=get_broker(),
        concurrent_num=concurrent_num or config["CONCURRENT_NUM"],
        qps=qps or config["QPS"],
        max_retry_times=max_retry_times or config["MAX_RETRY_TIMES"],
        retry_interval=retry_interval or config["RETRY_INTERVAL"],
        is_using_rpc_mode=is_using_rpc_mode,
    )


# ============================================================================
# Batch Analysis Tasks
# ============================================================================


@boost(get_booster_params("ai_batch_analysis", is_using_rpc_mode=True))
def run_batch_analysis(task_id: str) -> dict[str, Any]:
    """
    Execute batch AI analysis for a given task.

    This task processes multiple reports through the LLM using a classification
    guideline. Results are stored as AIAnnotation records.

    Args:
        task_id: UUID of the BatchAnalysisTask to process

    Returns:
        dict: Summary of processing results including success/error counts
    """
    from ai.services.batch_analysis_service import BatchAnalysisService

    logger.info(f"Starting batch analysis for task: {task_id}")
    try:
        result = BatchAnalysisService.execute_batch_analysis(task_id)
        logger.info(f"Batch analysis completed for task: {task_id}")
        return result
    except Exception as e:
        logger.exception(f"Batch analysis failed for task {task_id}: {e}")
        raise


@boost(get_booster_params("ai_single_report_analysis", concurrent_num=5, qps=3))
def analyze_single_report(
    report_uid: str,
    guideline_id: str,
    batch_task_id: str | None = None,
) -> dict[str, Any]:
    """
    Analyze a single report with a classification guideline.

    This is called as a sub-task from batch analysis for individual report
    processing, allowing fine-grained progress tracking.

    Args:
        report_uid: UID of the report to analyze
        guideline_id: UUID of the ClassificationGuideline to use
        batch_task_id: Optional parent batch task ID for progress tracking

    Returns:
        dict: Analysis result including classification and confidence
    """
    from ai.services.batch_analysis_service import BatchAnalysisService

    logger.info(f"Analyzing report: {report_uid} with guideline: {guideline_id}")
    try:
        result = BatchAnalysisService.process_single_report(
            report_uid=report_uid,
            guideline_id=guideline_id,
            batch_task_id=batch_task_id,
        )
        return result
    except Exception as e:
        logger.exception(f"Single report analysis failed for {report_uid}: {e}")
        raise


# ============================================================================
# Review Workflow Tasks
# ============================================================================


@boost(get_booster_params("ai_generate_samples", concurrent_num=2, max_retry_times=2))
def generate_review_samples(review_task_id: str) -> dict[str, Any]:
    """
    Generate stratified samples for a review task.

    This task creates ReviewSample records based on the sampling configuration
    (random, stratified by field, confidence-weighted).

    Args:
        review_task_id: UUID of the ReviewTask

    Returns:
        dict: Summary including sample count and stratification details
    """
    from ai.services.review_service import ReviewService

    logger.info(f"Generating review samples for task: {review_task_id}")
    try:
        result = ReviewService.generate_samples(review_task_id)
        logger.info(f"Sample generation completed for task: {review_task_id}")
        return result
    except Exception as e:
        logger.exception(f"Sample generation failed for task {review_task_id}: {e}")
        raise


@boost(get_booster_params("ai_calculate_metrics", concurrent_num=2))
def calculate_review_metrics(review_task_id: str) -> dict[str, Any]:
    """
    Calculate review metrics after feedback collection.

    Computes false positive rate, Cohen's Kappa (for double-blind reviews),
    and other quality metrics.

    Args:
        review_task_id: UUID of the ReviewTask

    Returns:
        dict: Calculated metrics including FP rate and agreement scores
    """
    from ai.services.review_service import ReviewService

    logger.info(f"Calculating review metrics for task: {review_task_id}")
    try:
        result = ReviewService.calculate_metrics(review_task_id)
        logger.info(f"Metrics calculation completed for task: {review_task_id}")
        return result
    except Exception as e:
        logger.exception(f"Metrics calculation failed for task {review_task_id}: {e}")
        raise


# ============================================================================
# Utility Tasks
# ============================================================================


@boost(get_booster_params("ai_deprecate_annotations", concurrent_num=1, qps=10))
def deprecate_old_annotations(
    guideline_id: str,
    new_version: int,
    report_uids: list[str] | None = None,
) -> dict[str, Any]:
    """
    Mark old AI annotations as deprecated after re-analysis.

    When a guideline is updated and reports are re-analyzed, this task marks
    the old annotations as deprecated while preserving them for audit.

    Args:
        guideline_id: UUID of the ClassificationGuideline
        new_version: The new version number being applied
        report_uids: Optional list of specific reports to update (all if None)

    Returns:
        dict: Count of deprecated annotations
    """
    from ai.services.batch_analysis_service import BatchAnalysisService

    logger.info(f"Deprecating annotations for guideline: {guideline_id}, version < {new_version}")
    try:
        result = BatchAnalysisService.deprecate_old_annotations(
            guideline_id=guideline_id,
            new_version=new_version,
            report_uids=report_uids,
        )
        return result
    except Exception as e:
        logger.exception(f"Annotation deprecation failed: {e}")
        raise


# ============================================================================
# Task Management Utilities
# ============================================================================


def start_batch_analysis(task_id: str) -> str:
    """
    Start a batch analysis task asynchronously.

    Args:
        task_id: UUID of the BatchAnalysisTask

    Returns:
        str: The funboost task tracking ID
    """
    result = run_batch_analysis.push(task_id)
    return str(result.task_id) if hasattr(result, "task_id") else str(result)


def start_sample_generation(review_task_id: str) -> str:
    """
    Start sample generation task asynchronously.

    Args:
        review_task_id: UUID of the ReviewTask

    Returns:
        str: The funboost task tracking ID
    """
    result = generate_review_samples.push(review_task_id)
    return str(result.task_id) if hasattr(result, "task_id") else str(result)


def start_metrics_calculation(review_task_id: str) -> str:
    """
    Start metrics calculation task asynchronously.

    Args:
        review_task_id: UUID of the ReviewTask

    Returns:
        str: The funboost task tracking ID
    """
    result = calculate_review_metrics.push(review_task_id)
    return str(result.task_id) if hasattr(result, "task_id") else str(result)
