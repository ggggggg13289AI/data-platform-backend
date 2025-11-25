"""
Accession Number Resolution Service.

Resolves canonical Accession Numbers (exam_id/report_id) across different resources.
This ensures Study and Report are correctly linked within a Project.
"""

from typing import Optional


class AccessionKeyResolver:
    """
    Resolver for canonical Accession Numbers.
    
    The canonical key is the 'Accession Number' (exam_id).
    - Study.exam_id == Accession Number
    - Report.report_id == Accession Number
    """

    @staticmethod
    def resolve_study_id(study_id: str) -> str:
        """
        Resolve Study ID to Accession Number.
        For Study, exam_id IS the Accession Number.
        """
        return study_id

    @staticmethod
    def resolve_report_id(report_id: str) -> str:
        """
        Resolve Report ID to Accession Number.
        For Report, report_id usually matches Accession Number.
        """
        return report_id

    @staticmethod
    def validate_linkage(study_id: str, report_id: str) -> bool:
        """
        Validate if a Study and Report belong to the same Accession Number.
        """
        return study_id == report_id

