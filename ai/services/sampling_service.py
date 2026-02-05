"""
Sampling Service - Stratified and random sampling for review tasks.

This module provides sampling strategies for selecting reports to review:
- Random sampling
- Stratified sampling by various fields
- Confidence-weighted sampling
"""

import logging
import random
from collections import defaultdict

from django.db.models import QuerySet

from report.models import AIAnnotation

logger = logging.getLogger(__name__)


class SamplingError(Exception):
    """Base exception for sampling errors."""

    pass


class SamplingService:
    """
    Service class for sampling AI annotations for review.

    Supports multiple sampling strategies to ensure representative
    coverage of the analyzed data.
    """

    # Supported stratification fields
    STRATA_FIELDS = [
        "patient_gender",
        "patient_age",
        "exam_source",
        "exam_item",
        "exam_description",
    ]

    @classmethod
    def random_sample(
        cls,
        annotations: QuerySet[AIAnnotation],
        sample_size: int,
    ) -> list[AIAnnotation]:
        """
        Simple random sampling.

        Args:
            annotations: QuerySet of annotations to sample from
            sample_size: Number of samples to select

        Returns:
            list: Selected annotations
        """
        total = annotations.count()
        if total == 0:
            return []

        actual_size = min(sample_size, total)

        # Get all IDs and sample
        all_ids = list(annotations.values_list("id", flat=True))
        selected_ids = random.sample(all_ids, actual_size)

        return list(annotations.filter(id__in=selected_ids))

    @classmethod
    def stratified_sample(
        cls,
        annotations: QuerySet[AIAnnotation],
        sample_size: int,
        strata_field: str,
    ) -> tuple[list[AIAnnotation], dict[str, int]]:
        """
        Stratified sampling by a single field.

        Samples proportionally from each stratum to maintain the
        original distribution.

        Args:
            annotations: QuerySet of annotations to sample from
            sample_size: Total number of samples to select
            strata_field: Field to stratify by

        Returns:
            tuple: (selected annotations, stratum distribution)
        """
        if strata_field not in cls.STRATA_FIELDS and strata_field != "ai_confidence":
            raise SamplingError(f"Invalid strata field: {strata_field}")

        # Build strata based on field type
        if strata_field == "ai_confidence":
            strata = cls._build_confidence_strata(annotations)
        else:
            strata = cls._build_field_strata(annotations, strata_field)

        return cls._proportional_sample(strata, sample_size)

    @classmethod
    def multi_stratified_sample(
        cls,
        annotations: QuerySet[AIAnnotation],
        sample_size: int,
        strata_fields: list[str],
    ) -> tuple[list[AIAnnotation], dict[str, int]]:
        """
        Stratified sampling by multiple fields.

        Creates composite strata based on combinations of field values.

        Args:
            annotations: QuerySet of annotations to sample from
            sample_size: Total number of samples to select
            strata_fields: Fields to stratify by

        Returns:
            tuple: (selected annotations, stratum distribution)
        """
        for field in strata_fields:
            if field not in cls.STRATA_FIELDS and field != "ai_confidence":
                raise SamplingError(f"Invalid strata field: {field}")

        strata = cls._build_composite_strata(annotations, strata_fields)
        return cls._proportional_sample(strata, sample_size)

    @classmethod
    def confidence_weighted_sample(
        cls,
        annotations: QuerySet[AIAnnotation],
        sample_size: int,
        low_confidence_weight: float = 2.0,
        low_confidence_threshold: float = 0.7,
    ) -> list[AIAnnotation]:
        """
        Sample with higher weight on low-confidence predictions.

        Args:
            annotations: QuerySet of annotations to sample from
            sample_size: Number of samples to select
            low_confidence_weight: Weight multiplier for low confidence items
            low_confidence_threshold: Threshold for "low confidence"

        Returns:
            list: Selected annotations
        """
        total = annotations.count()
        if total == 0:
            return []

        actual_size = min(sample_size, total)

        # Separate by confidence
        low_conf = annotations.filter(confidence_score__lt=low_confidence_threshold)
        high_conf = annotations.filter(confidence_score__gte=low_confidence_threshold)

        low_count = low_conf.count()
        high_count = high_conf.count()

        # Calculate weighted proportions
        total_weight = (low_count * low_confidence_weight) + high_count

        if total_weight == 0:
            return []

        low_sample_size = int((low_count * low_confidence_weight / total_weight) * actual_size)
        high_sample_size = actual_size - low_sample_size

        # Ensure we don't exceed available
        low_sample_size = min(low_sample_size, low_count)
        high_sample_size = min(high_sample_size, high_count)

        # Sample from each group
        samples = []

        if low_sample_size > 0:
            low_ids = list(low_conf.values_list("id", flat=True))
            selected_low = random.sample(low_ids, low_sample_size)
            samples.extend(annotations.filter(id__in=selected_low))

        if high_sample_size > 0:
            high_ids = list(high_conf.values_list("id", flat=True))
            selected_high = random.sample(high_ids, high_sample_size)
            samples.extend(annotations.filter(id__in=selected_high))

        return samples

    @classmethod
    def _build_field_strata(
        cls,
        annotations: QuerySet[AIAnnotation],
        field: str,
    ) -> dict[str, list[str]]:
        """
        Build strata based on a report field.

        Args:
            annotations: QuerySet to stratify
            field: Field name (must be a Study field)

        Returns:
            dict: Mapping of stratum label to annotation IDs
        """
        strata: dict[str, list[str]] = defaultdict(list)

        # We need to join with Study through Report
        for ann in annotations.select_related("report"):
            # Get the value from the related Study
            report = ann.report
            if hasattr(report, field):
                value = getattr(report, field) or "unknown"
            else:
                # Try to get from Study via report_id
                from study.models import Study

                try:
                    study = Study.objects.get(exam_id=report.report_id)
                    value = getattr(study, field, None) or "unknown"
                except Study.DoesNotExist:
                    value = "unknown"

            stratum_label = f"{field}:{value}"
            strata[stratum_label].append(str(ann.id))

        return dict(strata)

    @classmethod
    def _build_confidence_strata(
        cls,
        annotations: QuerySet[AIAnnotation],
    ) -> dict[str, list[str]]:
        """
        Build strata based on confidence score ranges.

        Args:
            annotations: QuerySet to stratify

        Returns:
            dict: Mapping of stratum label to annotation IDs
        """
        strata: dict[str, list[str]] = {
            "confidence:0.0-0.5": [],
            "confidence:0.5-0.7": [],
            "confidence:0.7-0.9": [],
            "confidence:0.9-1.0": [],
        }

        for ann in annotations:
            conf = ann.confidence_score or 0.0

            if conf < 0.5:
                strata["confidence:0.0-0.5"].append(str(ann.id))
            elif conf < 0.7:
                strata["confidence:0.5-0.7"].append(str(ann.id))
            elif conf < 0.9:
                strata["confidence:0.7-0.9"].append(str(ann.id))
            else:
                strata["confidence:0.9-1.0"].append(str(ann.id))

        # Remove empty strata
        return {k: v for k, v in strata.items() if v}

    @classmethod
    def _build_composite_strata(
        cls,
        annotations: QuerySet[AIAnnotation],
        fields: list[str],
    ) -> dict[str, list[str]]:
        """
        Build composite strata from multiple fields.

        Args:
            annotations: QuerySet to stratify
            fields: List of fields to combine

        Returns:
            dict: Mapping of composite stratum label to annotation IDs
        """
        strata: dict[str, list[str]] = defaultdict(list)

        for ann in annotations.select_related("report"):
            values = []
            report = ann.report

            for field in fields:
                if field == "ai_confidence":
                    conf = ann.confidence_score or 0.0
                    if conf < 0.5:
                        values.append("conf:low")
                    elif conf < 0.8:
                        values.append("conf:med")
                    else:
                        values.append("conf:high")
                elif hasattr(report, field):
                    value = getattr(report, field) or "unknown"
                    values.append(f"{field}:{value}")
                else:
                    from study.models import Study

                    try:
                        study = Study.objects.get(exam_id=report.report_id)
                        value = getattr(study, field, None) or "unknown"
                        values.append(f"{field}:{value}")
                    except Study.DoesNotExist:
                        values.append(f"{field}:unknown")

            stratum_label = "|".join(values)
            strata[stratum_label].append(str(ann.id))

        return dict(strata)

    @classmethod
    def _proportional_sample(
        cls,
        strata: dict[str, list[str]],
        sample_size: int,
    ) -> tuple[list[AIAnnotation], dict[str, int]]:
        """
        Sample proportionally from strata.

        Args:
            strata: Mapping of stratum label to annotation IDs
            sample_size: Total samples to select

        Returns:
            tuple: (selected annotations, stratum distribution)
        """
        total = sum(len(ids) for ids in strata.values())
        if total == 0:
            return [], {}

        actual_size = min(sample_size, total)
        selected_ids: list[str] = []
        distribution: dict[str, int] = {}

        # Calculate proportional samples per stratum
        remaining = actual_size
        for stratum_label, ids in strata.items():
            proportion = len(ids) / total
            stratum_sample_size = max(1, int(proportion * actual_size))
            stratum_sample_size = min(stratum_sample_size, len(ids), remaining)

            if stratum_sample_size > 0:
                sampled = random.sample(ids, stratum_sample_size)
                selected_ids.extend(sampled)
                distribution[stratum_label] = stratum_sample_size
                remaining -= stratum_sample_size

            if remaining <= 0:
                break

        # Get the actual annotation objects
        annotations = list(AIAnnotation.objects.filter(id__in=selected_ids))

        return annotations, distribution

    @classmethod
    def get_stratum_label(cls, annotation: AIAnnotation, strata_fields: list[str]) -> str:
        """
        Get the stratum label for a single annotation.

        Args:
            annotation: The annotation to label
            strata_fields: Fields used for stratification

        Returns:
            str: Composite stratum label
        """
        values = []
        report = annotation.report

        for field in strata_fields:
            if field == "ai_confidence":
                conf = annotation.confidence_score or 0.0
                if conf < 0.5:
                    values.append("conf:low")
                elif conf < 0.8:
                    values.append("conf:med")
                else:
                    values.append("conf:high")
            elif hasattr(report, field):
                value = getattr(report, field) or "unknown"
                values.append(f"{field}:{value}")
            else:
                values.append(f"{field}:unknown")

        return "|".join(values) if values else "default"
