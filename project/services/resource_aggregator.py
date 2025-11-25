from typing import List, Dict, Any
from datetime import datetime
from common.models import StudyProjectAssignment
from study.models import Study
from report.models import Report
from project.schemas import ProjectResourceItem, ProjectResourceAssignment, UserInfo
from study.schemas import StudyListItem
from report.schemas import ReportResponse

class ResourceAggregator:
    """
    Aggregates project resources (Studies, Reports) into a unified list.
    """

    @staticmethod
    def get_project_resources(
        project_id: str,
        resource_types: List[str],
        page: int,
        page_size: int,
        q: str = None
    ) -> Dict[str, Any]:
        """
        Fetch paginated resources for a project.
        Pagination is applied at the 'Assignment' (Case) level.
        """
        
        # 1. Base Query: Assignments
        qs = StudyProjectAssignment.objects.filter(project_id=project_id)\
            .select_related('project', 'study', 'assigned_by')\
            .order_by('-assigned_at')
            
        # Apply Search (Basic filtering on Accession/Patient Name via Study)
        if q:
            qs = qs.filter(
                study__patient_name__icontains=q
            ) | qs.filter(
                study__exam_id__icontains=q
            )
            
        # Pagination (LIMIT/OFFSET)
        total_assignments = qs.count()
        start = (page - 1) * page_size
        end = start + page_size
        assignments = list(qs[start:end])
        
        if not assignments:
            return {'items': [], 'count': 0}
            
        exam_ids = [a.study_id for a in assignments]
        
        # 2. Fetch Reports (if requested)
        reports = {}
        if 'report' in resource_types:
            # Join on report_id == exam_id (Accession Number)
            report_objs = Report.objects.filter(report_id__in=exam_ids, is_latest=True)
            for r in report_objs:
                reports[r.report_id] = r
                
        # 3. Construct List
        results = []
        for assign in assignments:
            accession = assign.study_id
            
            # Assignment info
            # Construct UserInfo manually or via helper
            user = assign.assigned_by
            user_info = UserInfo(
                id=str(user.id),
                name=user.get_full_name() or user.username,
                email=user.email
            )
            assign_info = ProjectResourceAssignment(
                assigned_at=assign.assigned_at,
                assigned_by=user_info
            )

            # Study Item
            if 'study' in resource_types:
                s = assign.study
                # Use to_dict() or construct Schema. 
                # StudyListItem expects Pydantic model. 
                # We can use from_orm if model is compatible.
                # Safety: construct dict first.
                study_data = s.to_dict()
                # Add id field which is exam_id
                study_data['id'] = s.exam_id
                
                results.append(ProjectResourceItem(
                    resource_type='study',
                    accession_number=accession,
                    resource_timestamp=s.order_datetime,
                    study=StudyListItem(**study_data),
                    assignment=assign_info
                ))
                
            # Report Item
            if 'report' in resource_types:
                r = reports.get(accession)
                if r:
                    # Manual construction for ReportResponse to handle content_preview
                    content_preview = r.content_raw[:500] if r.content_raw else ""
                    report_data = {
                        'uid': r.uid,
                        'report_id': r.report_id,
                        'title': r.title,
                        'report_type': r.report_type,
                        'version_number': r.version_number,
                        'is_latest': r.is_latest,
                        'created_at': r.created_at.isoformat(),
                        'verified_at': r.verified_at.isoformat() if r.verified_at else None,
                        'content_preview': content_preview
                    }
                    
                    results.append(ProjectResourceItem(
                        resource_type='report',
                        accession_number=accession,
                        resource_timestamp=r.verified_at or r.created_at,
                        report=ReportResponse(**report_data),
                        assignment=assign_info
                    ))
                    
        return {
            'items': results,
            'count': total_assignments
        }

