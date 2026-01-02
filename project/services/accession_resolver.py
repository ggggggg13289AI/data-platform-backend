"""
Accession Number Resolution Service.

Resolves canonical Accession Numbers (exam_id/report_id) across different resources.
This ensures Study and Report are correctly linked within a Project.
"""

from report.models import Report
from study.models import Study


class AccessionKeyResolver:
    """
    Utility that keeps Accession Number resolution centralized.

    The Accession Number is the canonical foreign key that links all project
    resources (studies, reports, future AI annotations, etc.).
    """

    @classmethod
    def resolve_study_id(cls, study_id: str) -> str:
        """Study IDs already represent the Accession Number."""
        return study_id

    @classmethod
    def resolve_report_id(cls, report_id: str | None) -> str:
        """Report IDs are expected to match the Accession Number."""
        if not report_id:
            raise ValueError("report_id 必須提供")
        return report_id

    @classmethod
    def resolve_accession(cls, resource_id: str, resource_type: str) -> str:
        """Normalize any resource identifier into the canonical Accession Number."""
        if resource_type == "study":
            return cls.resolve_study_id(resource_id)
        if resource_type == "report":
            return cls.resolve_report_id(resource_id)
        raise ValueError(f"不支援的資源類型: {resource_type}")

    @classmethod
    def validate_linkage(cls, study_id: str, report_id: str) -> bool:
        """
        Ensure that the Study and the Report identifiers map to the same Accession Number.
        """
        return cls.resolve_study_id(study_id) == cls.resolve_report_id(report_id)

    @classmethod
    def get_resources_by_accession(cls, accession_number: str) -> dict[str, object | None]:
        """
        Fetch the Study and the latest Report that share the provided Accession Number.
        """
        study = Study.objects.filter(exam_id=accession_number).first()
        report = Report.objects.filter(report_id=accession_number, is_latest=True).first()
        return {"study": study, "report": report}
