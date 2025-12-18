from datetime import datetime
from typing import Any, Dict, List, Optional, Set

from django.db.models import Q

from common.models import StudyProjectAssignment
from project.schemas import ProjectResourceAssignment, ProjectResourceItem, UserInfo
from project.services.accession_resolver import AccessionKeyResolver
from report.models import Report
from report.schemas import ReportResponse
from study.models import Study
from study.schemas import StudyListItem


class ResourceAggregator:
    """
    Aggregates project resources (Studies, Reports) into a unified list.
    """

    @staticmethod
    def _collect_search_accessions(
        project_exam_ids: List[str], query: str, include_reports: bool
    ) -> Set[str]:
        if not project_exam_ids or not query:
            return set()

        matches: Set[str] = set()

        study_qs = Study.objects.filter(exam_id__in=project_exam_ids).filter(
            Q(patient_name__icontains=query)
            | Q(exam_description__icontains=query)
            | Q(exam_id__icontains=query)
            | Q(medical_record_no__icontains=query)
            | Q(exam_item__icontains=query)
        )
        matches.update(study_qs.values_list('exam_id', flat=True))

        if include_reports:
            report_qs = (
                Report.objects.filter(report_id__in=project_exam_ids, is_latest=True)
                .filter(
                    Q(title__icontains=query)
                    | Q(content_raw__icontains=query)
                    | Q(report_id__icontains=query)
                )
                .distinct()
            )
            matches.update(report_qs.values_list('report_id', flat=True))

        return matches

    @staticmethod
    def _build_study_item(study: Study) -> StudyListItem:
        study_data = {
            'exam_id': study.exam_id,
            'medical_record_no': study.medical_record_no,
            'application_order_no': study.application_order_no,
            'patient_name': study.patient_name,
            'patient_gender': study.patient_gender,
            'patient_age': study.patient_age,
            'exam_status': study.exam_status,
            'exam_source': study.exam_source,
            'exam_item': study.exam_item,
            'exam_description': study.exam_description,
            'order_datetime': study.order_datetime,
            'check_in_datetime': study.check_in_datetime,
            'report_certification_datetime': study.report_certification_datetime,
            'certified_physician': study.certified_physician,
        }
        return StudyListItem(**study_data)

    @staticmethod
    def _build_report_item(report: Report) -> ReportResponse:
        preview = (report.content_raw or '')[:500]
        report_data = {
            'uid': report.uid,
            'report_id': report.report_id,
            'title': report.title,
            'report_type': report.report_type,
            'version_number': report.version_number,
            'is_latest': report.is_latest,
            'created_at': report.created_at.isoformat(),
            'verified_at': report.verified_at.isoformat() if report.verified_at else None,
            'content_preview': preview,
            'content_raw': report.content_raw,
        }
        return ReportResponse(**report_data)

    @staticmethod
    def _derive_timestamp(
        study: Optional[Study], report: Optional[Report], assigned_at: datetime
    ) -> datetime:
        timestamp = assigned_at
        if study and study.order_datetime and study.order_datetime > timestamp:
            timestamp = study.order_datetime
        if report:
            report_ts = report.verified_at or report.created_at
            if report_ts and report_ts > timestamp:
                timestamp = report_ts
        return timestamp

    @classmethod
    def get_project_resources(
        cls,
        project_id: str,
        resource_types: List[str],
        page: int,
        page_size: int,
        q: str = None,
    ) -> Dict[str, Any]:
        """Fetch paginated resources for a project."""

        safe_page = max(1, page)
        safe_page_size = max(1, page_size)
        resource_set = {rt for rt in (resource_types or []) if rt in {'study', 'report', 'ai_annotation'}}
        if not resource_set:
            resource_set = {'study', 'report'}

        base_qs = StudyProjectAssignment.objects.filter(project_id=project_id)
        project_exam_ids = list(base_qs.values_list('study_id', flat=True))
        if q:
            search_accessions = cls._collect_search_accessions(
                project_exam_ids, q, 'report' in resource_set
            )
            if not search_accessions:
                return {'items': [], 'count': 0, 'page': safe_page, 'page_size': safe_page_size}
            filtered_qs = base_qs.filter(study_id__in=search_accessions)
        else:
            filtered_qs = base_qs

        assignments_qs = (
            filtered_qs.select_related('project', 'study', 'assigned_by')
            .order_by('-assigned_at')
        )

        total_assignments = assignments_qs.count()
        start = (safe_page - 1) * safe_page_size
        end = start + safe_page_size
        assignments = list(assignments_qs[start:end])

        if not assignments:
            return {
                'items': [],
                'count': total_assignments,
                'page': safe_page,
                'page_size': safe_page_size,
            }

        accession_candidates = {
            AccessionKeyResolver.resolve_accession(assign.study_id, 'study') for assign in assignments
        }

        reports: Dict[str, Report] = {}
        if 'report' in resource_set and accession_candidates:
            report_objs = Report.objects.filter(report_id__in=accession_candidates, is_latest=True)
            for report in report_objs:
                try:
                    report_accession = AccessionKeyResolver.resolve_accession(report.report_id, 'report')
                except ValueError:
                    continue
                reports[report_accession] = report

        results: List[ProjectResourceItem] = []
        for assign in assignments:
            accession = AccessionKeyResolver.resolve_accession(assign.study_id, 'study')
            user = assign.assigned_by
            user_info = UserInfo(
                id=str(user.id),
                name=user.get_full_name() or user.username,
                email=user.email,
            )
            assignment_info = ProjectResourceAssignment(
                assigned_at=assign.assigned_at,
                assigned_by=user_info,
            )

            study_item: Optional[StudyListItem] = None
            if 'study' in resource_set and assign.study:
                study_item = cls._build_study_item(assign.study)

            report_item: Optional[ReportResponse] = None
            report_model = reports.get(accession)
            if 'report' in resource_set and report_model:
                if not AccessionKeyResolver.validate_linkage(accession, report_model.report_id):
                    raise ValueError(
                        f'Accession mismatch: study {accession} vs report {report_model.report_id}'
                    )
                report_item = cls._build_report_item(report_model)

            primary_type = 'study' if study_item else 'report' if report_item else 'ai_annotation'

            timestamp = cls._derive_timestamp(assign.study, report_model, assign.assigned_at)
            results.append(
                ProjectResourceItem(
                    resource_type=primary_type,
                    accession_number=accession,
                    resource_timestamp=timestamp,
                    study=study_item,
                    report=report_item,
                    assignment=assignment_info,
                )
            )

        results.sort(key=lambda item: item.resource_timestamp or datetime.min, reverse=True)

        return {
            'items': results,
            'count': total_assignments,
            'page': safe_page,
            'page_size': safe_page_size,
        }
