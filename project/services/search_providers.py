from typing import List
from django.db.models import Q, F
from django.contrib.postgres.search import SearchVector, SearchQuery, SearchRank
from common.models import StudyProjectAssignment
from study.models import Study
from report.models import Report
from project.services.search_registry import ProjectSearchRegistry, SearchResult

@ProjectSearchRegistry.register('study')
def search_studies(project_id: str, query: str) -> List[SearchResult]:
    """
    Search studies within a project.
    Uses Postgres Full Text Search if available, or fallback to icontains.
    """
    if not query:
        return []

    # 1. Get project studies
    # We use StudyProjectAssignment to filter studies in the project
    base_qs = Study.objects.filter(
        project_assignments__project_id=project_id
    ).distinct()

    # 2. Apply Search
    # For now, use Q objects for broad coverage across fields
    # This mimics the "icontains" approach for immediate robustness
    search_qs = base_qs.filter(
        Q(patient_name__icontains=query) |
        Q(exam_description__icontains=query) |
        Q(exam_id__icontains=query) |
        Q(medical_record_no__icontains=query) |
        Q(exam_item__icontains=query)
    )

    # 3. Transform to SearchResult
    results = []
    for study in search_qs[:50]:  # Limit 50
        results.append(SearchResult(
            resource_type='study',
            accession_number=study.exam_id,
            score=1.0,  # TODO: Calculate relevance if using FTS
            snippet=f"{study.patient_name} - {study.exam_description or ''}",
            resource_payload=study.to_dict(),
            resource_timestamp=study.order_datetime.isoformat() if study.order_datetime else ""
        ))
    
    return results

@ProjectSearchRegistry.register('report')
def search_reports(project_id: str, query: str) -> List[SearchResult]:
    """
    Search reports linked to a project.
    Reports are linked via StudyProjectAssignment (Accession Number matching).
    """
    if not query:
        return []

    # 1. Get Accession Numbers (exam_ids) in the project
    # This is the "link" between Project and Report
    project_exam_ids = StudyProjectAssignment.objects.filter(
        project_id=project_id
    ).values_list('study_id', flat=True)

    # 2. Filter Reports by these IDs AND Query
    # Reuse logic from ReportService but scoped to project
    reports = Report.objects.filter(
        report_id__in=project_exam_ids,
        is_latest=True
    ).filter(
        Q(title__icontains=query) |
        Q(content_processed__icontains=query) |
        Q(report_id__icontains=query)
    ).order_by('-verified_at')[:50]

    # 3. Transform
    results = []
    for report in reports:
        # Extract snippet
        content = report.content_processed or ""
        try:
            idx = content.lower().index(query.lower())
            start = max(0, idx - 20)
            end = min(len(content), idx + len(query) + 50)
            snippet = "..." + content[start:end] + "..."
        except ValueError:
            snippet = report.title

        results.append(SearchResult(
            resource_type='report',
            accession_number=report.report_id,
            score=1.0,
            snippet=snippet,
            resource_payload=report.to_dict(),
            resource_timestamp=report.verified_at.isoformat() if report.verified_at else ""
        ))

    return results

