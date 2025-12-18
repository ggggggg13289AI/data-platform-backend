from typing import List
from django.db.models import F
from django.contrib.postgres.search import SearchQuery, SearchRank
from common.models import StudyProjectAssignment
from study.models import Study
from report.models import Report
from report.service import ReportService
from project.services.search_registry import ProjectSearchRegistry, SearchResult
from project.services.search_utils import highlight_query_snippet

@ProjectSearchRegistry.register('study')
def search_studies(project_id: str, query: str, limit: int = 50) -> List[SearchResult]:
    if not query or not query.strip():
        return []

    search_query = SearchQuery(query, config='simple')
    studies = (
        Study.objects.filter(project_assignments__project_id=project_id)
        .annotate(rank=SearchRank(F('search_vector'), search_query))
        .filter(rank__gt=0)
        .order_by('-rank', '-order_datetime')[:limit]
    )

    results: list[SearchResult] = []
    for study in studies:
        score = float(getattr(study, 'rank', 0.0) or 0.0)
        source = study.exam_description or study.exam_item or study.patient_name or ''
        snippet = highlight_query_snippet(source, query)

        results.append(SearchResult(
            resource_type='study',
            accession_number=study.exam_id,
            score=score,
            snippet=snippet,
            resource_payload=study.to_dict(),
            resource_timestamp=study.order_datetime.isoformat() if study.order_datetime else ''
        ))

    return results

@ProjectSearchRegistry.register('report')
def search_reports(project_id: str, query: str, limit: int = 50) -> List[SearchResult]:
    if not query or not query.strip():
        return []

    project_exam_ids = StudyProjectAssignment.objects.filter(
        project_id=project_id
    ).values_list('study_id', flat=True)

    search_query = SearchQuery(query, config='simple')
    reports = (
        Report.objects.filter(report_id__in=project_exam_ids, is_latest=True)
        .annotate(rank=SearchRank(F('search_vector'), search_query))
        .filter(rank__gt=0)
        .order_by('-rank', '-verified_at')[:limit]
    )

    results: list[SearchResult] = []
    for report in reports:
        score = float(getattr(report, 'rank', 0.0) or 0.0)
        source = report.content_processed or report.title or ''
        snippet = highlight_query_snippet(source, query)
        payload = ReportService._serialize_report(report)

        results.append(SearchResult(
            resource_type='report',
            accession_number=report.report_id or '',
            score=score,
            snippet=snippet,
            resource_payload=payload,
            resource_timestamp=report.verified_at.isoformat() if report.verified_at else ''
        ))

    return results

