# Report API - OpenAPI Documentation

**Version**: 1.1.0 (Pagination Unified with Page/PageSize Model)
**Status**: Production Ready
**Last Updated**: 2025-11-12

## API Overview

The Medical Imaging Data Platform Report API provides comprehensive report management capabilities including import, search, retrieval, and version control. The API follows REST conventions and uses JSON for all request/response bodies.

### Base URL
```
http://localhost:8000/api/v1
```

### Authentication
Currently no authentication required (development mode). Production deployments should implement token-based authentication.

### Content Type
All endpoints accept and return `application/json`

---

## Pagination Model (v1.1.0)

**Migration Note**: API v1.1.0 introduced a new pagination model using `page` and `page_size` parameters (replacing legacy `limit` and `offset`).

### Page/PageSize Model Specification

| Parameter | Type | Required | Default | Range | Description |
|-----------|------|----------|---------|-------|-------------|
| `page` | integer | No | 1 | ≥1 | Page number (1-indexed). First page is page 1, not 0 |
| `page_size` | integer | No | 20 | [1, 100] | Number of items per page. Auto-clamped to max 100 |

### Pagination Response Fields

```json
{
  "items": [],           // Array of report objects
  "total": 1234,        // Total number of items matching query
  "page": 1,            // Current page number
  "page_size": 20,      // Items per page (may differ from request if clamped)
  "pages": 62           // Total number of pages (ceil(total / page_size))
}
```

### Pagination Examples

**Request 1: First page with default settings**
```
GET /api/v1/reports/search/paginated?q=covid
```
Returns items 1-20 (page 1, page_size 20 default)

**Request 2: Specific page and custom page size**
```
GET /api/v1/reports/search/paginated?q=covid&page=2&page_size=50
```
Returns items 51-100 (page 2, 50 items per page)

**Request 3: Large page size (auto-clamped)**
```
GET /api/v1/reports/search/paginated?q=covid&page=1&page_size=500
```
Returns items 1-100 (page_size 500 auto-clamped to max 100)

### Offset Calculation (for implementation details)
```
offset = (page - 1) × page_size
end = offset + page_size
```
- Page 1, size 20: offset 0, end 20 (items 0-19)
- Page 2, size 20: offset 20, end 40 (items 20-39)
- Page 9, size 100: offset 800, end 900 (items 800-899)

### Total Pages Calculation
```
total_pages = ceil(total_items / page_size)
```
- 1000 items, page_size 20: 50 pages
- 1000 items, page_size 100: 10 pages
- 105 items, page_size 20: 6 pages (last page has 5 items)

---

## Endpoints

### 1. POST /reports/import

**Description**: Import or update a medical report

**Request Body**
```json
{
  "uid": "report_123",
  "title": "Chest CT Scan",
  "content": "CT findings: ...",
  "report_type": "PDF",
  "source_url": "https://source.com/report/123",
  "report_id": "REP-001 (optional)",
  "chr_no": "chr_12345 (optional)",
  "mod": "CT (optional)",
  "report_date": "2025-11-12 (optional)",
  "verified_at": "2025-11-12T10:30:00 (optional)"
}
```

**Response (200 OK)**
```json
{
  "uid": "report_123",
  "report_id": "REP-001",
  "is_new": true,
  "action": "create",
  "version_number": 1
}
```

**Response Fields**
| Field | Type | Description |
|-------|------|-------------|
| `uid` | string | Unique identifier for the report |
| `report_id` | string | Internal report ID |
| `is_new` | boolean | true=new report created, false=existing report updated |
| `action` | string | "create" (new) or "update" (existing) or "deduplicate" |
| `version_number` | integer | Current version of the report |

**Status Codes**
| Code | Meaning |
|------|---------|
| 200 | Success |
| 400 | Invalid request body |
| 500 | Server error |

**Examples**

Example 1: Create new report
```bash
curl -X POST http://localhost:8000/api/v1/reports/import \
  -H "Content-Type: application/json" \
  -d '{
    "uid": "scan_001",
    "title": "Head MRI",
    "content": "MRI findings...",
    "report_type": "PDF",
    "source_url": "https://hospital.com/scan/001"
  }'
```

Example 2: Update existing report with new version
```bash
curl -X POST http://localhost:8000/api/v1/reports/import \
  -H "Content-Type: application/json" \
  -d '{
    "uid": "scan_001",
    "title": "Head MRI - Updated",
    "content": "MRI findings - verified...",
    "report_type": "PDF",
    "source_url": "https://hospital.com/scan/001"
  }'
```

---

### 2. GET /reports/search/paginated

**Description**: Advanced search with pagination support (Recommended - v1.1.0+)

**Query Parameters**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `q` | string | No | "" | Full-text search query across title, uid, content, etc. |
| `page` | integer | No | 1 | Page number (1-indexed) |
| `page_size` | integer | No | 20 | Items per page (max 100, auto-clamped) |
| `report_type` | string | No | none | Filter by report type (PDF, HTML, TXT, etc.) |
| `report_status` | string | No | none | Filter by status (pending, completed, cancelled) |
| `report_format` | string | No | none | Filter by format (comma-separated values) |
| `date_from` | string | No | none | ISO 8601 date start (YYYY-MM-DD) |
| `date_to` | string | No | none | ISO 8601 date end (YYYY-MM-DD) |
| `sort` | string | No | "verified_at_desc" | Sort order: verified_at_desc, verified_at_asc, created_at_desc, title_asc |

**Response (200 OK)**
```json
{
  "items": [
    {
      "uid": "scan_001",
      "report_id": "REP-001",
      "title": "Head MRI",
      "report_type": "PDF",
      "version_number": 1,
      "is_latest": true,
      "created_at": "2025-11-12T10:00:00",
      "verified_at": "2025-11-12T10:30:00",
      "content_preview": "MRI findings: ... (first 500 chars)"
    }
  ],
  "total": 125,
  "page": 1,
  "page_size": 20,
  "pages": 7,
  "filters": {
    "report_types": ["PDF", "HTML", "TXT"],
    "report_statuses": ["pending", "completed", "cancelled"],
    "mods": ["CT", "MR", "CR"],
    "verified_date_range": {
      "start": "2025-01-01T00:00:00",
      "end": "2025-11-12T10:30:00"
    }
  }
}
```

**Response Fields (Item)**
| Field | Type | Description |
|-------|------|-------------|
| `uid` | string | Unique identifier |
| `report_id` | string | Internal report ID |
| `title` | string | Report title |
| `report_type` | string | Type (PDF, HTML, TXT, etc.) |
| `version_number` | integer | Current version |
| `is_latest` | boolean | Whether this is the latest version |
| `created_at` | datetime | ISO 8601 creation timestamp |
| `verified_at` | datetime | ISO 8601 verification timestamp |
| `content_preview` | string | First 500 characters of content |

**Status Codes**
| Code | Meaning |
|------|---------|
| 200 | Success |
| 422 | Invalid parameters (page/page_size out of range) |
| 500 | Server error |

**Examples**

Example 1: Basic search with default pagination
```bash
curl "http://localhost:8000/api/v1/reports/search/paginated?q=MRI"
# Returns page 1, 20 items per page
```

Example 2: Search with custom pagination
```bash
curl "http://localhost:8000/api/v1/reports/search/paginated?q=covid&page=2&page_size=50"
# Returns page 2 with 50 items per page
```

Example 3: Search with filter and sort
```bash
curl "http://localhost:8000/api/v1/reports/search/paginated?q=CT&report_type=PDF&sort=created_at_desc&page=1&page_size=20"
# Returns PDF reports containing "CT", sorted by creation date
```

Example 4: Date range filter
```bash
curl "http://localhost:8000/api/v1/reports/search/paginated?date_from=2025-01-01&date_to=2025-11-12&page=1&page_size=20"
# Returns reports from date range
```

**Performance Notes**
- Response time: <100ms (page_size=10), <300ms (page_size=100)
- Query count: 2-3 queries (count + fetch), no N+1 problems
- Large page sizes (100 items) response: ~78KB
- Suitable for both mobile (<100ms) and desktop (<300ms) applications

---

### 3. GET /reports/search

**Description**: Legacy search endpoint (limit-based, maintained for backward compatibility)

**Query Parameters**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `q` | string | No | "" | Search query |
| `limit` | integer | No | 50 | Maximum results (legacy, max 500) |
| `report_type` | string | No | none | Filter by type |
| `report_status` | string | No | none | Filter by status |
| `sort` | string | No | "verified_at_desc" | Sort order |

**Response (200 OK)**
```json
[
  {
    "uid": "scan_001",
    "report_id": "REP-001",
    "title": "Head MRI",
    "report_type": "PDF",
    "version_number": 1,
    "is_latest": true,
    "created_at": "2025-11-12T10:00:00",
    "verified_at": "2025-11-12T10:30:00",
    "content_preview": "MRI findings: ..."
  }
]
```

**Status**
⚠️ **LEGACY ENDPOINT** - Use `/reports/search/paginated` for new implementations

**Examples**

```bash
curl "http://localhost:8000/api/v1/reports/search?q=MRI&limit=10"
```

---

### 4. GET /reports/latest

**Description**: Retrieve latest report versions

**Query Parameters**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `limit` | integer | No | 20 | Maximum results (max 500) |

**Response (200 OK)**
```json
[
  {
    "uid": "scan_001",
    "report_id": "REP-001",
    "title": "Head MRI",
    "report_type": "PDF",
    "version_number": 2,
    "is_latest": true,
    "created_at": "2025-11-12T10:00:00",
    "verified_at": "2025-11-12T11:00:00",
    "content_preview": "..."
  }
]
```

**Examples**

```bash
# Get 20 most recent reports
curl "http://localhost:8000/api/v1/reports/latest?limit=20"

# Get 50 most recent reports
curl "http://localhost:8000/api/v1/reports/latest?limit=50"
```

---

### 5. GET /reports/{report_id}

**Description**: Retrieve full details of a specific report

**Path Parameters**
| Parameter | Type | Description |
|-----------|------|-------------|
| `report_id` | string | Report ID |

**Response (200 OK)**
```json
{
  "uid": "scan_001",
  "report_id": "REP-001",
  "title": "Head MRI",
  "report_type": "PDF",
  "version_number": 1,
  "is_latest": true,
  "created_at": "2025-11-12T10:00:00",
  "verified_at": "2025-11-12T10:30:00",
  "content_preview": "MRI findings: ... (first 500 chars)",
  "content_raw": "Full MRI report content here... (complete content)",
  "source_url": "https://hospital.com/scan/001"
}
```

**Status Codes**
| Code | Meaning |
|------|---------|
| 200 | Success |
| 404 | Report not found |
| 500 | Server error |

**Examples**

```bash
curl "http://localhost:8000/api/v1/reports/REP-001"
```

---

### 6. GET /reports/{report_id}/versions

**Description**: Retrieve version history of a report

**Path Parameters**
| Parameter | Type | Description |
|-----------|------|-------------|
| `report_id` | string | Report ID |

**Response (200 OK)**
```json
[
  {
    "version_number": 2,
    "changed_at": "2025-11-12T11:00:00",
    "verified_at": "2025-11-12T11:15:00",
    "change_type": "update",
    "change_description": "Content verified"
  },
  {
    "version_number": 1,
    "changed_at": "2025-11-12T10:00:00",
    "verified_at": "2025-11-12T10:30:00",
    "change_type": "create",
    "change_description": "Initial creation"
  }
]
```

**Response Fields**
| Field | Type | Description |
|-------|------|-------------|
| `version_number` | integer | Version number |
| `changed_at` | datetime | When change was made |
| `verified_at` | datetime | When version was verified |
| `change_type` | string | create, update, verify, deduplicate |
| `change_description` | string | Change description |

**Examples**

```bash
curl "http://localhost:8000/api/v1/reports/REP-001/versions"
```

---

### 7. GET /reports/filters/options

**Description**: Get available filter options for search UI

**Response (200 OK)**
```json
{
  "report_types": ["PDF", "HTML", "TXT", "DOCX", "JPG"],
  "report_statuses": ["pending", "completed", "cancelled"],
  "mods": ["CT", "MR", "CR"],
  "verified_date_range": {
    "start": "2025-01-01T00:00:00",
    "end": "2025-11-12T10:30:00"
  }
}
```

**Examples**

```bash
curl "http://localhost:8000/api/v1/reports/filters/options"
```

> Legacy path `/api/v1/reports/options/filters` is still available but will be removed in v2.0.0. Use the new `/filters/options` route.

Used by frontend to populate dropdown menus and filter controls. It mirrors the data embedded in `/reports/search/paginated` responses to match the `/studies` API pattern.

---

## Migration Guide: limit/offset → page/page_size

### For Developers Upgrading to v1.1.0

#### Old API (limit-based)
```
GET /api/v1/reports/search?q=COVID&limit=50&offset=100
```
Returns 50 items starting from offset 100 (items 100-149)

#### New API (page-based)
```
GET /api/v1/reports/search/paginated?q=COVID&page=3&page_size=50
```
Returns page 3 with 50 items per page (items 100-149)

#### Conversion Formula
```
new_page = (old_offset / old_limit) + 1
new_page_size = old_limit
```

#### Examples

**Old**: `limit=20&offset=0`
- Items: 0-19
- New equivalent: `page=1&page_size=20`

**Old**: `limit=20&offset=20`
- Items: 20-39
- New equivalent: `page=2&page_size=20`

**Old**: `limit=20&offset=100`
- Items: 100-119
- New equivalent: `page=6&page_size=20`

#### JavaScript Migration Example
```javascript
// OLD CODE
const offset = 100;
const limit = 20;
const response = await fetch(`/api/v1/reports/search?limit=${limit}&offset=${offset}`);

// NEW CODE
const page = (offset / limit) + 1;
const pageSize = limit;
const response = await fetch(`/api/v1/reports/search/paginated?page=${page}&page_size=${pageSize}`);
```

#### Python Migration Example
```python
# OLD CODE
offset = 100
limit = 20
response = requests.get('/api/v1/reports/search', params={'limit': limit, 'offset': offset})

# NEW CODE
page = (offset // limit) + 1
page_size = limit
response = requests.get('/api/v1/reports/search/paginated', params={'page': page, 'page_size': page_size})
```

---

## Error Handling

### Standard Error Responses

#### 400 Bad Request
```json
{
  "detail": "Invalid request parameters",
  "errors": {
    "page_size": "page_size must be between 1 and 100"
  }
}
```

#### 404 Not Found
```json
{
  "detail": "Report not found: REP-001"
}
```

#### 422 Unprocessable Entity
```json
{
  "detail": "Invalid pagination parameters",
  "errors": {
    "page": "page must be >= 1",
    "page_size": "page_size must be <= 100"
  }
}
```

#### 500 Internal Server Error
```json
{
  "detail": "Internal server error occurred"
}
```

---

## Performance Guidelines

### Query Performance (Measured - Phase 5.3 Benchmarks)

| Page Size | Avg Response Time | Query Count | Notes |
|-----------|-------------------|-------------|-------|
| 10 | <100ms | 2 | Excellent for mobile |
| 20 | <150ms | 2 | Default, balanced |
| 50 | <200ms | 2 | Good for desktop |
| 100 | <300ms | 2-3 | Max size, still optimal |

### Recommendations

- **Mobile Apps**: Use `page_size=10` for fast response
- **Web Dashboards**: Use `page_size=20` for balanced UX
- **Data Export**: Use `page_size=100` for bulk retrieval
- **Large Datasets**: Implement pagination (don't fetch all at once)

### Database Indexes

The following indexes optimize pagination performance:
- `report_type` - Filters
- `is_latest, -verified_at` - Sorting
- `content_hash, verified_at` - Deduplication
- `source_url, verified_at` - Source tracking

---

## API Versioning

### Current Version: v1.1.0

**Version History**:
- v1.0.0: Initial API with limit/offset pagination
- v1.1.0: New page/page_size pagination (current)

### Backward Compatibility

- Legacy `/reports/search` endpoint still available
- Old `limit` parameter works but deprecated
- New clients should use `/reports/search/paginated`

---

## Testing with cURL

### Test 1: Create a Report
```bash
curl -X POST http://localhost:8000/api/v1/reports/import \
  -H "Content-Type: application/json" \
  -d '{
    "uid": "test_001",
    "title": "Test Report",
    "content": "This is test content",
    "report_type": "PDF",
    "source_url": "https://test.com/report"
  }'
```

### Test 2: Search with Pagination
```bash
# Page 1
curl "http://localhost:8000/api/v1/reports/search/paginated?q=test&page=1&page_size=10"

# Page 2
curl "http://localhost:8000/api/v1/reports/search/paginated?q=test&page=2&page_size=10"
```

### Test 3: Get Latest Reports
```bash
curl "http://localhost:8000/api/v1/reports/latest?limit=10"
```

### Test 4: Get Filter Options
```bash
curl "http://localhost:8000/api/v1/reports/filters/options"
```

---

## Troubleshooting

### Common Issues

**Issue**: "page_size must be between 1 and 100"
- **Cause**: Requested page_size > 100
- **Solution**: Use page_size ≤ 100

**Issue**: "page must be >= 1"
- **Cause**: Requested page < 1
- **Solution**: Use page ≥ 1

**Issue**: Empty results on later pages
- **Cause**: Requested page beyond available pages
- **Example**: Total 100 items, page_size 20 (5 pages), requesting page 10
- **Solution**: Check `pages` field in response to find last valid page

**Issue**: JSON parsing error
- **Cause**: Invalid JSON in request body
- **Solution**: Validate JSON syntax, ensure all strings are quoted

---

## Support & Feedback

For API issues or feedback:
1. Check this documentation
2. Review test suite: `studies/tests.py`
3. Performance analysis: `claudedocs/PHASE_5.3_PERFORMANCE_BENCHMARKS.md`
4. Migration guide: Section above

---

## Document Information

- **Created**: 2025-11-12
- **Status**: Phase 5.4 Complete
- **Version**: 1.1.0
- **Test Coverage**: 43 tests (25 unit + 9 integration + 9 performance)
- **Performance Grade**: A+ (Excellent)
