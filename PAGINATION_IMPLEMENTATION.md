# Django Ninja Pagination Implementation

## Overview

This document describes the pagination implementation for the studies API using Django Ninja's built-in pagination framework.

**Reference**: https://django-ninja.dev/guides/response/pagination/

## Architecture

### Components

1. **Custom Pagination Class** (`studies/pagination.py`)
   - Extends Django Ninja's `PaginationBase`
   - Implements LimitOffsetPagination pattern
   - Supports custom filter context in response

2. **API Endpoint** (`studies/api.py`)
   - Uses `@paginate(StudyPagination)` decorator
   - Returns `List[StudyListItem]` response
   - Handles filter parameters and sorting

3. **Service Layer** (`studies/services.py`)
   - `get_studies_queryset()`: Returns filtered QuerySet (no pagination)
   - `search_studies()`: Deprecated, kept for backward compatibility
   - `_get_filter_options()`: Provides available filters

4. **Response Schema** (`studies/schemas.py`)
   - `StudyListItem`: Individual study record
   - `StudySearchResponse`: Paginated response with filters

## How It Works

### Request Flow

```
Client Request
    ↓
HTTP GET /api/v1/studies/search?q=chest&limit=10&offset=0
    ↓
@router.get('/search', response=List[StudyListItem])
@paginate(StudyPagination)
def search_studies(...)
    ↓
Returns QuerySet (unsliced)
    ↓
@paginate decorator intercepts:
  1. Extracts limit and offset from query params
  2. Calls StudyPagination.paginate_queryset()
  3. Receives StudyPaginationOutput
  4. Serializes to JSON
    ↓
Response: {"items": [...], "count": 100, "filters": {...}}
```

### Response Format

```json
{
  "items": [
    {
      "exam_id": "E001",
      "patient_name": "John Doe",
      "exam_status": "completed",
      "exam_source": "CT",
      ...
    },
    ...
  ],
  "count": 100,
  "filters": {
    "exam_statuses": ["pending", "completed", "cancelled"],
    "exam_sources": ["CT", "MRI", "X-ray"],
    "exam_items": ["Chest CT", "Brain MRI", ...],
    "equipment_types": ["CT Scanner", "MRI Machine", ...]
  }
}
```

## Query Parameters

### Pagination Parameters (Handled by Django Ninja)

- `limit` (int, default=20): Items per page (max 100)
  - Example: `?limit=10`
- `offset` (int, default=0): Number of items to skip
  - Example: `?offset=20` (skip first 20 items)

### Filter Parameters

- `q` (str): Text search in patient_name, exam_description, exam_item
  - Example: `?q=chest`
- `exam_status` (str): Filter by status
  - Example: `?exam_status=completed`
- `exam_source` (str): Filter by source
  - Example: `?exam_source=CT`
- `exam_item` (str): Filter by exam type
  - Example: `?exam_item=Chest%20CT`
- `start_date` (str): Filter from date (ISO 8601)
  - Example: `?start_date=2024-01-01T00:00:00`
- `end_date` (str): Filter to date (ISO 8601)
  - Example: `?end_date=2024-12-31T23:59:59`

### Sorting Parameter

- `sort` (str): Sort order
  - `order_datetime_desc` (default): Most recent first
  - `order_datetime_asc`: Oldest first
  - `patient_name_asc`: Alphabetical by patient name

## Example API Calls

### Basic Pagination

```bash
# Get first 20 items (default)
curl "http://localhost:8001/api/v1/studies/search"

# Get next 20 items (skip first 20)
curl "http://localhost:8001/api/v1/studies/search?limit=20&offset=20"

# Get custom page size
curl "http://localhost:8001/api/v1/studies/search?limit=50&offset=0"
```

### With Filters

```bash
# Search for "chest" and get first page
curl "http://localhost:8001/api/v1/studies/search?q=chest&limit=10&offset=0"

# Filter by status
curl "http://localhost:8001/api/v1/studies/search?exam_status=completed&limit=20&offset=0"

# Combine filters
curl "http://localhost:8001/api/v1/studies/search?q=chest&exam_source=CT&exam_status=completed&limit=10&offset=0"

# With date range
curl "http://localhost:8001/api/v1/studies/search?start_date=2024-01-01T00:00:00&end_date=2024-12-31T23:59:59"

# Sort oldest first
curl "http://localhost:8001/api/v1/studies/search?sort=order_datetime_asc&limit=20&offset=0"
```

## Implementation Details

### CustomPagination Class

```python
class StudyPagination(PaginationBase):
    """Custom pagination with filter context"""
    
    class Input(StudyPaginationInput):
        limit: int = 20
        offset: int = 0
    
    class Output(StudyPaginationOutput):
        items: List[Any]
        count: int
        filters: FilterOptions
    
    def paginate_queryset(self, queryset, pagination, **params):
        # 1. Get total count
        # 2. Apply offset and limit
        # 3. Convert to dicts (queryset → items)
        # 4. Get filter options
        # 5. Return Output
```

### API Endpoint

```python
@router.get('/search', response=List[StudyListItem])
@paginate(StudyPagination)  # ← Django Ninja handles pagination
def search_studies(
    request,
    q: str = Query(default=''),
    exam_status: Optional[str] = Query(None),
    # ... other filters
):
    # Return QuerySet (unsliced)
    # @paginate decorator handles:
    # - Extracting limit and offset
    # - Calling paginate_queryset()
    # - Serializing response
    queryset = StudyService.get_studies_queryset(q=q, exam_status=exam_status, ...)
    return queryset
```

### Service Layer

```python
@staticmethod
def get_studies_queryset(...) -> QuerySet:
    """Returns filtered QuerySet (no pagination)"""
    queryset = Study.objects.all()
    if q:
        queryset = queryset.filter(Q(...) | Q(...))
    # Apply filters...
    # Apply sorting...
    return queryset  # Unsliced!
```

## Performance Considerations

### Query Optimization

1. **Single Count Query**: `queryset.count()` called once in `paginate_queryset()`
2. **Slicing**: Applied via `queryset[offset:offset+limit]`
3. **Filter Caching**: Consider caching `get_filter_options()` result

### Recommended Optimizations

```python
# In paginate_queryset():
# Use select_related/prefetch_related if needed
paginated_items = queryset.select_related(...)[offset:offset+limit]

# Cache filter options
# In pagination.py or services.py
from django.views.decorators.cache import cache_page

@cache_page(300)  # Cache for 5 minutes
def get_filter_options():
    ...
```

### Batch Size

The current implementation uses:
- `limit` parameter to control results per page
- Max limit: 100 items
- Default limit: 20 items

## Testing

### Manual Testing

```bash
# Start development server
python manage.py runserver 8001

# Test basic pagination
curl "http://localhost:8001/api/v1/studies/search?limit=10&offset=0" | jq

# Test with filters
curl "http://localhost:8001/api/v1/studies/search?q=chest&limit=10" | jq

# Test response structure
curl "http://localhost:8001/api/v1/studies/search?limit=5" | jq '.items, .count, .filters'
```

### Automated Testing

Create `tests/test_pagination.py`:

```python
from django.test import TestCase
from ninja.testing import TestClient
from studies.api import router

class PaginationTestCase(TestCase):
    def setUp(self):
        self.client = TestClient(router)
    
    def test_default_pagination(self):
        response = self.client.get('/search')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('items', data)
        self.assertIn('count', data)
        self.assertIn('filters', data)
    
    def test_limit_parameter(self):
        response = self.client.get('/search?limit=10')
        data = response.json()
        self.assertLessEqual(len(data['items']), 10)
    
    def test_offset_parameter(self):
        response1 = self.client.get('/search?limit=10&offset=0')
        response2 = self.client.get('/search?limit=10&offset=10')
        data1 = response1.json()
        data2 = response2.json()
        # Verify different pages returned
```

## Troubleshooting

### Issue: "has no collection response"

**Cause**: Response is not `List[Schema]`

**Fix**: Ensure `response=List[StudyListItem]` in decorator

```python
# ✓ Correct
@router.get('/search', response=List[StudyListItem])
@paginate(StudyPagination)

# ✗ Wrong
@router.get('/search', response=StudySearchResponse)
@paginate(StudyPagination)
```

### Issue: Filters missing in response

**Cause**: Django Ninja's `@paginate` replaces response

**Fix**: Custom `StudyPagination` class handles this automatically

### Issue: Pagination parameters not recognized

**Cause**: Parameter names don't match `Input` class

**Fix**: Use `limit` and `offset` (not `page` and `page_size`)

```python
# ✓ Correct
curl "?limit=10&offset=20"

# ✗ Wrong
curl "?page=2&page_size=10"
```

## Migration Guide (from old manual pagination)

### Before (Manual Pagination)

```python
# In api.py
page: int = Query(1)
page_size: int = Query(20)

# In services.py
offset = (page - 1) * page_size
studies = queryset[offset:offset + page_size]
return StudySearchResponse(data=studies, total=total, page=page, page_size=page_size, ...)
```

### After (Django Ninja Pagination)

```python
# In api.py
@paginate(StudyPagination)  # ← Replaces manual logic
def search_studies(...):
    return queryset  # ← Return unsliced queryset

# In services.py
def get_studies_queryset(...):  # ← New method
    return queryset  # ← Return unsliced queryset
```

## Best Practices

1. **Always Return Unsliced QuerySet**: Don't apply pagination in service layer
2. **Use @paginate Decorator**: Handles all pagination logic centrally
3. **Custom Pagination Class**: Extend for custom output format (like filters)
4. **Validate Query Parameters**: Check limit bounds (1-100)
5. **Cache Filter Options**: Expensive queries should be cached
6. **Document Parameters**: Keep API documentation updated
7. **Test Edge Cases**: Empty results, max limit, invalid offset

## References

- Django Ninja Pagination: https://django-ninja.dev/guides/response/pagination/
- Django QuerySet Slicing: https://docs.djangoproject.com/en/stable/ref/models/querysets/#slicing
- Pydantic BaseModel: https://docs.pydantic.dev/latest/api/base_model/
