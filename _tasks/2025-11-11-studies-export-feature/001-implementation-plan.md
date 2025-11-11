# Studies Export Feature Implementation Plan

**Task**: Implement export functionality for studies API
**Date**: 2025-11-11
**Frontend URL**: http://localhost:8001/api/v1/studies/export?q=
**Status**: In Progress

---

## 1. Requirements Analysis

### Frontend Expectations
- **Endpoint**: `/api/v1/studies/export`
- **Method**: GET
- **Query Parameters**: Same as search endpoint (q, exam_status, filters, etc.)
- **Response**: File download (CSV or Excel format)

### Functional Requirements
1. Export filtered study data based on search criteria
2. Support multiple export formats (CSV, Excel)
3. Include all relevant study fields in export
4. Handle large datasets efficiently
5. Maintain consistency with search endpoint filters

---

## 2. Technical Design

### API Endpoint Design
```python
@router.get('/export')
def export_studies(
    request,
    format: str = Query('csv', description="Export format: csv or xlsx"),
    q: str = Query(default=''),
    exam_status: Optional[str] = Query(None),
    exam_source: Optional[str] = Query(None),
    # ... all other search parameters
):
    """Export filtered studies as CSV or Excel file"""
```

### Export Formats
1. **CSV Format**
   - MIME type: `text/csv`
   - Filename: `studies_export_{timestamp}.csv`
   - Character encoding: UTF-8 with BOM for Excel compatibility

2. **Excel Format (XLSX)**
   - MIME type: `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`
   - Filename: `studies_export_{timestamp}.xlsx`
   - Include formatting and headers

### Data Fields to Export
Based on StudyListItem schema:
- exam_id
- medical_record_no
- patient_name
- patient_gender
- patient_age
- exam_status
- exam_source
- exam_description
- exam_room
- exam_equipment
- order_datetime
- check_in_datetime
- report_certification_datetime
- certified_physician

---

## 3. Implementation Steps

### Phase 1: Dependencies
1. Check and add required dependencies:
   - `pandas` - Data manipulation and CSV/Excel export
   - `openpyxl` - Excel file generation

### Phase 2: Service Layer
1. Create `export_service.py` with export logic
2. Add methods:
   - `export_to_csv(queryset) -> bytes`
   - `export_to_excel(queryset) -> bytes`
   - `generate_export_filename(format, timestamp) -> str`

### Phase 3: API Endpoint
1. Add export endpoint to `api.py`
2. Reuse search queryset logic
3. Return file response with appropriate headers

### Phase 4: Testing
1. Create `test_export.py`
2. Test cases:
   - Export with no filters
   - Export with various filters
   - CSV format validation
   - Excel format validation
   - Large dataset handling
   - Empty result handling

### Phase 5: Documentation
1. Update API documentation
2. Add export endpoint to API contract
3. Update README with export feature

---

## 4. File Structure

```
studies/
├── api.py                 # Add export endpoint
├── export_service.py      # New: Export logic
├── export_schemas.py      # New: Export-specific schemas
└── config.py             # Add export configuration

tests/
└── test_export.py        # New: Export tests

docs/
├── 004_API_REFERENCE.md  # Update with export endpoint
└── api/
    └── 301_API_CONTRACT.md  # Update with export specification
```

---

## 5. Code Components

### 5.1 Export Service (export_service.py)
```python
import pandas as pd
from io import BytesIO
from datetime import datetime
from typing import List, Dict, Any
from django.db.models import QuerySet

class ExportService:
    @staticmethod
    def export_to_csv(queryset: QuerySet) -> bytes:
        """Convert queryset to CSV bytes"""

    @staticmethod
    def export_to_excel(queryset: QuerySet) -> bytes:
        """Convert queryset to Excel bytes"""

    @staticmethod
    def prepare_export_data(queryset: QuerySet) -> List[Dict[str, Any]]:
        """Convert queryset to list of dicts for export"""
```

### 5.2 Export Configuration (config.py addition)
```python
class ExportConfig:
    EXPORT_BATCH_SIZE: int = 1000
    MAX_EXPORT_RECORDS: int = 10000
    CSV_ENCODING: str = 'utf-8-sig'  # UTF-8 with BOM
    EXCEL_ENGINE: str = 'openpyxl'
    DEFAULT_EXPORT_FORMAT: str = 'csv'
    ALLOWED_EXPORT_FORMATS: List[str] = ['csv', 'xlsx']
```

### 5.3 API Endpoint (api.py addition)
```python
from django.http import HttpResponse
from .export_service import ExportService

@router.get('/export')
def export_studies(request, format: str = Query('csv'), ...):
    # Get filtered queryset (same as search)
    queryset = StudyService.get_studies_queryset(...)

    # Generate export
    if format == 'xlsx':
        content = ExportService.export_to_excel(queryset)
        content_type = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        extension = 'xlsx'
    else:  # Default to CSV
        content = ExportService.export_to_csv(queryset)
        content_type = 'text/csv'
        extension = 'csv'

    # Return file response
    response = HttpResponse(content, content_type=content_type)
    response['Content-Disposition'] = f'attachment; filename="studies_export_{timestamp}.{extension}"'
    return response
```

---

## 6. Performance Considerations

### Memory Optimization
- Stream large exports instead of loading all data into memory
- Use chunked processing for datasets > 1000 records
- Implement pagination for very large exports

### Query Optimization
- Reuse existing optimized raw SQL from search endpoint
- Use select_related/prefetch_related if needed
- Consider adding export-specific indexes

---

## 7. Security Considerations

1. **Rate Limiting**: Prevent export abuse
2. **File Size Limits**: Cap maximum export size
3. **Authentication**: Ensure only authorized users can export
4. **Data Sanitization**: Clean data before export to prevent injection

---

## 8. Testing Strategy

### Unit Tests
- Export service methods
- Data formatting functions
- File generation

### Integration Tests
- Full export flow with filters
- Response headers validation
- File content validation

### Performance Tests
- Large dataset export (5000+ records)
- Memory usage monitoring
- Response time benchmarks

---

## 9. Rollout Plan

1. **Development** (Day 1)
   - Implement export service
   - Add API endpoint
   - Basic testing

2. **Testing** (Day 2)
   - Complete test suite
   - Performance testing
   - Bug fixes

3. **Documentation** (Day 2)
   - Update API docs
   - Update user guides
   - Add examples

4. **Deployment**
   - Add dependencies to requirements.txt
   - Deploy to staging
   - Verify with frontend
   - Deploy to production

---

## 10. Success Criteria

- ✅ Export endpoint responds at `/api/v1/studies/export`
- ✅ Supports all search filters
- ✅ Generates valid CSV files
- ✅ Generates valid Excel files
- ✅ Handles 5000+ records efficiently
- ✅ Includes appropriate HTTP headers
- ✅ Integrates seamlessly with frontend
- ✅ Comprehensive test coverage (>85%)
- ✅ Documentation updated

---

## 11. Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Large dataset memory issues | Implement streaming/chunking |
| Slow export for complex queries | Add progress indication/async processing |
| Excel compatibility issues | Test with multiple Excel versions |
| Character encoding problems | Use UTF-8 with BOM for CSV |

---

**Next Step**: Begin implementation starting with export service