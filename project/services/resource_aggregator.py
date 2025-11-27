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

            # Report Item
            if 'report' in resource_types:
                r = reports.get(accession)
                if r:
                    # Manual construction for ReportResponse to handle content_preview
                    # For unified view, we might want full content if requested, 
                    # but strict schema usually limits it. 
                    # User asked for "content_raw" to be visible.
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
                        'content_preview': content_preview,
                        'content_raw': r.content_raw  # Include raw content
                    }
                    
                    # Create a combined item if study exists, or separate if needed.
                    # But wait, Schema ProjectResourceItem is one or the other?
                    # "One Accession One Row" implies we should return a combined object or 
                    # frontend groups them.
                    # Current Schema: study: StudyListItem | None, report: ReportResponse | None
                    # We can populate BOTH in one ProjectResourceItem.
                    
                    # If study already added (same accession), update it.
                    # But we just appended to results.
                    # Check if last item is same accession? 
                    # Logic above: if 'study' in types -> append.
                    # We should restructure loop.
                    pass
        
        # 3. Construct List (Restructured for Grouping)
        results = []
        for assign in assignments:
            accession = assign.study_id
            
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

            study_item = None
            if 'study' in resource_types:
                s = assign.study
                study_data = s.to_dict()
                study_data['id'] = s.exam_id
                study_item = StudyListItem(**study_data)

            report_item = None
            if 'report' in resource_types:
                r = reports.get(accession)
                if r:
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
                        'content_preview': content_preview,
                        'content_raw': r.content_raw
                    }
                    report_item = ReportResponse(**report_data)

            # Create Single Item with potentially BOTH study and report
            # Resource type label? Maybe 'case' or 'combined'? 
            # Or logic in schema: resource_type is just primary tag.
            # Let's call it 'study' if study exists, else 'report', or 'case'.
            # For "One Accession One Row", this single item represents the Case.
            
            primary_type = 'study' if study_item else ('report' if report_item else 'unknown')
            
            # Use timestamp from Study if avail, else Report
            ts = None
            if study_item:
                ts = s.order_datetime
            elif report_item:
                 ts = r.verified_at or r.created_at

            results.append(ProjectResourceItem(
                resource_type=primary_type,
                accession_number=accession,
                resource_timestamp=ts,
                study=study_item,
                report=report_item,
                assignment=assign_info
            ))
            
        return {
            'items': results,
            'count': total_assignments
        }

