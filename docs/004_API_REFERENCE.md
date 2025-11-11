# API Reference - Medical Imaging Management System

**Version**: 1.1.0
**Base URL**: `http://localhost:8001/api/v1`
**Framework**: Django Ninja (FastAPI-style)
**Authentication**: None (Internal system)

---

## Table of Contents

- [Overview](#overview)
- [Base Information](#base-information)
- [Response Format](#response-format)
- [Error Handling](#error-handling)
- [Endpoints](#endpoints)
  - [Search Studies](#search-studies)
  - [Get Study Detail](#get-study-detail)
  - [Get Filter Options](#get-filter-options)
  - [Export Studies](#export-studies)
- [Data Models](#data-models)
- [Query Parameters](#query-parameters)
- [Examples](#examples)
- [Rate Limiting](#rate-limiting)

---

## Overview

The Medical Imaging Management System API provides RESTful endpoints for managing and querying medical examination records. Built with Django Ninja, it offers:

- **Full-text search** across 9 fields
- **Multi-filter support** (status, source, equipment, gender, room)
- **Date range and age filtering**
- **Pagination** with customizable page sizes
- **Sorting** by multiple criteria
- **Filter options** with dynamic dropdown values

### Key Features

✅ **Production Ready**: 85% test coverage, comprehensive error handling
✅ **Performance Optimized**: Strategic caching, database indexing
✅ **API Compatibility**: 100% compatible with FastAPI response format
✅ **Graceful Degradation**: Cache failures don't break service

---

## Base Information

### Base URLs

| Environment | URL |
|------------|-----|
| Development | `http://localhost:8001/api/v1` |
| Production | `https://your-domain.com/api/v1` |

### Content Type

All requests and responses use `application/json` content type.

### API Documentation

- **Interactive Docs**: `http://localhost:8001/api/v1/docs`
- **Health Check**: `http://localhost:8001/api/v1/health`

---

## Response Format

### Standard Success Response

```json
{
  "items": [...],
  "count": 1234,
  "filters": {...}
}
```

### Standard Error Response

```json
{
  "detail": "Error message description"
}
```

### HTTP Status Codes

| Code | Meaning | Usage |
|------|---------|-------|
| 200 | OK | Successful request |
| 404 | Not Found | Study not found by exam_id |
| 422 | Validation Error | Invalid query parameters |
| 500 | Internal Server Error | Database or system error |

---

## Error Handling

### Error Types

#### 1. StudyNotFoundError (404)
```json
{
  "detail": "Study with exam_id 'EXAM999' not found"
}
```

**Causes**:
- Invalid exam_id
- Study deleted from database
- Typo in exam_id parameter

#### 2. DatabaseQueryError (500)
```json
{
  "detail": "Database query failed"
}
```

**Causes**:
- Database connection lost
- Query timeout
- Database constraint violation

#### 3. Validation Error (422)
```json
{
  "detail": [
    {
      "loc": ["query", "patient_age_min"],
      "msg": "value is not a valid integer",
      "type": "type_error.integer"
    }
  ]
}
```

**Causes**:
- Invalid parameter types (e.g., string for integer)
- Out-of-range values (e.g., page_size > 100)
- Invalid date format

---

## Endpoints

## Search Studies

Search medical examination records with filters and pagination.

### HTTP Request

```
GET /api/v1/studies/search
```

### Query Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `q` | string | No | `""` | Full-text search query (searches 9 fields) |
| `exam_status` | string | No | - | Filter by exam status |
| `exam_source` | string | No | - | Filter by exam source (CT, MRI, etc.) |
| `exam_equipment` | array[string] | No | - | Filter by equipment (multi-select) |
| `application_order_no` | string | No | - | Filter by order number (exact match) |
| `patient_gender` | array[string] | No | - | Filter by gender (multi-select) |
| `exam_description` | array[string] | No | - | Filter by description (multi-select) |
| `exam_room` | array[string] | No | - | Filter by exam room (multi-select) |
| `patient_age_min` | integer | No | - | Minimum patient age |
| `patient_age_max` | integer | No | - | Maximum patient age |
| `start_date` | string | No | - | Check-in date from (YYYY-MM-DD) |
| `end_date` | string | No | - | Check-in date to (YYYY-MM-DD) |
| `limit` | integer | No | 20 | Items per page (max: 100) |
| `offset` | integer | No | 0 | Number of items to skip |
| `sort` | string | No | `order_datetime_desc` | Sort order |

### Array Parameter Formats

The API supports two formats for array parameters:

**Format 1: Bracket notation** (frontend format)
```
?patient_gender[]=F&patient_gender[]=M
```

**Format 2: Repeated parameter** (standard format)
```
?patient_gender=F&patient_gender=M
```

### Sort Options

| Value | Description |
|-------|-------------|
| `order_datetime_desc` | Order by datetime descending (newest first) |
| `order_datetime_asc` | Order by datetime ascending (oldest first) |
| `patient_name_asc` | Order by patient name A-Z |

### Full-Text Search Fields

The `q` parameter searches across these 9 fields:
- `exam_id`
- `medical_record_no`
- `application_order_no`
- `patient_name`
- `exam_item`
- `exam_description`
- `exam_room`
- `exam_equipment`
- `certified_physician`

### Response Schema

```json
{
  "items": [
    {
      "exam_id": "EXAM001",
      "medical_record_no": "MR12345",
      "application_order_no": "APP001",
      "patient_name": "張偉",
      "patient_gender": "M",
      "patient_age": 45,
      "exam_status": "completed",
      "exam_source": "CT",
      "exam_item": "胸部電腦斷層",
      "exam_description": "胸腔",
      "order_datetime": "2025-11-06T10:30:00",
      "check_in_datetime": "2025-11-06T11:00:00",
      "report_certification_datetime": "2025-11-06T14:30:00",
      "certified_physician": "王醫師"
    }
  ],
  "count": 1250,
  "filters": {
    "exam_statuses": ["completed", "pending", "cancelled"],
    "exam_sources": ["CT", "MRI", "X-ray", "Ultrasound"],
    "equipment_types": ["Siemens", "GE", "Philips"],
    "exam_rooms": ["Room 1", "Room 2", "Room 3"],
    "exam_equipments": ["CT-001", "MRI-002"],
    "exam_descriptions": ["胸腔", "腹部", "頭部"]
  }
}
```

### Examples

#### Basic Search
```bash
GET /api/v1/studies/search?q=張偉

# Response
{
  "items": [...],
  "count": 5,
  "filters": {...}
}
```

#### Filtered Search
```bash
GET /api/v1/studies/search?exam_status=completed&exam_source=CT&limit=10

# Response
{
  "items": [
    {
      "exam_id": "EXAM001",
      "patient_name": "張偉",
      "exam_status": "completed",
      "exam_source": "CT",
      ...
    }
  ],
  "count": 234,
  "filters": {...}
}
```

#### Multi-Select Filter (Bracket Format)
```bash
GET /api/v1/studies/search?patient_gender[]=F&patient_gender[]=M&limit=20

# Response
{
  "items": [...],
  "count": 1250,
  "filters": {...}
}
```

#### Multi-Select Filter (Standard Format)
```bash
GET /api/v1/studies/search?patient_gender=F&patient_gender=M&limit=20

# Response (same as above)
```

#### Age Range Filter
```bash
GET /api/v1/studies/search?patient_age_min=30&patient_age_max=50

# Response
{
  "items": [...],
  "count": 456,
  "filters": {...}
}
```

#### Date Range Filter
```bash
GET /api/v1/studies/search?start_date=2025-11-01&end_date=2025-11-07

# Response
{
  "items": [...],
  "count": 87,
  "filters": {...}
}
```

#### Pagination Example
```bash
# Page 1 (items 1-20)
GET /api/v1/studies/search?limit=20&offset=0

# Page 2 (items 21-40)
GET /api/v1/studies/search?limit=20&offset=20

# Page 3 (items 41-60)
GET /api/v1/studies/search?limit=20&offset=40
```

#### Complex Query
```bash
GET /api/v1/studies/search?q=胸部&exam_status=completed&exam_source=CT&patient_gender[]=M&patient_age_min=40&patient_age_max=60&start_date=2025-11-01&end_date=2025-11-07&sort=order_datetime_desc&limit=10&offset=0

# Response
{
  "items": [
    {
      "exam_id": "EXAM045",
      "patient_name": "李強",
      "patient_gender": "M",
      "patient_age": 52,
      "exam_status": "completed",
      "exam_source": "CT",
      "exam_item": "胸部電腦斷層",
      "order_datetime": "2025-11-06T14:30:00",
      ...
    }
  ],
  "count": 15,
  "filters": {...}
}
```

---

## Get Study Detail

Retrieve complete details for a specific examination record.

### HTTP Request

```
GET /api/v1/studies/{exam_id}
```

### Path Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `exam_id` | string | Yes | Examination ID (e.g., "EXAM001") |

### Response Schema

```json
{
  "exam_id": "EXAM001",
  "medical_record_no": "MR12345",
  "application_order_no": "APP001",
  "patient_name": "張偉",
  "patient_gender": "M",
  "patient_birth_date": "1978-05-15",
  "patient_age": 45,
  "exam_status": "completed",
  "exam_source": "CT",
  "exam_item": "胸部電腦斷層",
  "exam_description": "胸腔",
  "exam_room": "Room 1",
  "exam_equipment": "CT-001",
  "equipment_type": "Siemens",
  "order_datetime": "2025-11-06T10:30:00",
  "check_in_datetime": "2025-11-06T11:00:00",
  "report_certification_datetime": "2025-11-06T14:30:00",
  "certified_physician": "王醫師",
  "data_load_time": "2025-11-06T09:00:00"
}
```

### Examples

#### Successful Request
```bash
GET /api/v1/studies/EXAM001

# Response (200 OK)
{
  "exam_id": "EXAM001",
  "patient_name": "張偉",
  "exam_status": "completed",
  ...
}
```

#### Not Found
```bash
GET /api/v1/studies/EXAM999

# Response (404 Not Found)
{
  "detail": "Study with exam_id 'EXAM999' not found"
}
```

---

## Get Filter Options

Retrieve all available filter options for search dropdowns.

### HTTP Request

```
GET /api/v1/studies/filters/options
```

### Response Schema

```json
{
  "exam_statuses": ["completed", "pending", "cancelled"],
  "exam_sources": ["CT", "MRI", "X-ray", "Ultrasound", "Endoscopy"],
  "equipment_types": ["GE", "Philips", "Siemens", "Toshiba"],
  "exam_rooms": ["Room 1", "Room 2", "Room 3", "Room 4"],
  "exam_equipments": ["CT-001", "CT-002", "MRI-001", "MRI-002"],
  "exam_descriptions": ["胸腔", "腹部", "頭部", "骨骼", "心臟"]
}
```

### Field Descriptions

| Field | Description |
|-------|-------------|
| `exam_statuses` | All distinct exam statuses in database |
| `exam_sources` | All distinct exam sources (imaging modalities) |
| `equipment_types` | All distinct equipment manufacturers |
| `exam_rooms` | All distinct examination rooms |
| `exam_equipments` | All distinct equipment identifiers |
| `exam_descriptions` | Common exam descriptions (limited set) |

### Examples

#### Basic Request
```bash
GET /api/v1/studies/filters/options

# Response (200 OK)
{
  "exam_statuses": ["completed", "pending", "cancelled"],
  "exam_sources": ["CT", "MRI", "X-ray", "Ultrasound"],
  "equipment_types": ["GE", "Philips", "Siemens"],
  "exam_rooms": ["Room 1", "Room 2", "Room 3"],
  "exam_equipments": ["CT-001", "MRI-002"],
  "exam_descriptions": ["胸腔", "腹部", "頭部"]
}
```

### Caching Behavior

- **Cache TTL**: 24 hours
- **Cache Backend**: Local memory (development) or Redis (production)
- **Graceful Degradation**: If cache fails, query database directly
- **Performance**: Sub-100ms response time with caching

---

## Export Studies

Export filtered studies as CSV or Excel file.

### HTTP Request

```
GET /api/v1/studies/export
```

### Query Parameters

All parameters from the Search Studies endpoint are supported, plus:

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `format` | string | "csv" | Export format: "csv" or "xlsx" |

All search/filter parameters from the Search Studies endpoint apply:
- `q` - Text search query
- `exam_status` - Filter by exam status
- `exam_source` - Filter by exam source
- `exam_equipment[]` - Filter by equipment (multi-select)
- `patient_gender[]` - Filter by gender (multi-select)
- `exam_description[]` - Filter by description (multi-select)
- `exam_room[]` - Filter by room (multi-select)
- `application_order_no` - Filter by application order number
- `patient_age_min` - Minimum patient age
- `patient_age_max` - Maximum patient age
- `start_date` - Check-in date from (YYYY-MM-DD)
- `end_date` - Check-in date to (YYYY-MM-DD)
- `sort` - Sort order

### Response

Returns a file download with appropriate content type:
- **CSV**: `text/csv; charset=utf-8` (with UTF-8 BOM for Excel compatibility)
- **Excel**: `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`

### Export Fields

The export includes all available fields from the study records:
- `exam_id` - Examination ID
- `medical_record_no` - Medical record number
- `application_order_no` - Application order number
- `patient_name` - Patient name
- `patient_gender` - Patient gender (M/F/U)
- `patient_birth_date` - Birth date (YYYY-MM-DD)
- `patient_age` - Age in years
- `exam_status` - Examination status
- `exam_source` - Imaging modality
- `exam_item` - Exam type
- `exam_description` - Additional description
- `exam_room` - Examination room
- `exam_equipment` - Equipment identifier
- `equipment_type` - Equipment manufacturer
- `order_datetime` - Order date/time
- `check_in_datetime` - Check-in date/time
- `report_certification_datetime` - Report certification date/time
- `certified_physician` - Certifying physician

### Examples

#### Export All Studies as CSV
```bash
GET /api/v1/studies/export?format=csv

# Response Headers
Content-Type: text/csv; charset=utf-8
Content-Disposition: attachment; filename="studies_export_20251111_143022.csv"
```

#### Export Filtered Studies as Excel
```bash
GET /api/v1/studies/export?format=xlsx&exam_status=completed&exam_source=CT

# Response Headers
Content-Type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet
Content-Disposition: attachment; filename="studies_export_20251111_143022.xlsx"
```

#### Export with Search Query
```bash
GET /api/v1/studies/export?format=csv&q=chest&patient_gender[]=M&start_date=2025-11-01
```

#### Export with Multiple Filters
```bash
GET /api/v1/studies/export?format=xlsx&exam_status=completed&exam_equipment[]=CT-001&exam_equipment[]=CT-002&patient_age_min=30&patient_age_max=60
```

### Important: Field Type Handling

**Patient Birth Date Field**:
- **Type**: String (YYYY-MM-DD format)
- **Storage**: CharField in database
- **Export**: Returns string value directly (not parsed as date object)
- **Latest Fix** (v1.1.0): Corrected export handling to properly treat as string field (prevents AttributeError)

**DateTime Fields** (exported as ISO 8601 strings):
- `order_datetime` - String format: "2025-11-06T10:30:00"
- `check_in_datetime` - String format: "2025-11-06T11:00:00"
- `report_certification_datetime` - String format: "2025-11-06T14:30:00"

### Limitations

- **Maximum Records**: 10,000 records per export (prevents memory issues)
- **File Size**: Depends on data content, typically 1-10MB
- **Performance**: Export generation may take 2-10 seconds for large datasets

### Error Responses

| Status | Description |
|--------|-------------|
| 400 | Invalid format parameter |
| 500 | Internal server error during export generation |

---

## Data Models

### StudyListItem (Search Results)

Used in `/api/v1/studies/search` response.

```typescript
interface StudyListItem {
  exam_id: string;                            // Examination ID
  medical_record_no: string | null;          // Medical record number
  application_order_no: string | null;       // Application order number
  patient_name: string;                       // Patient name
  patient_gender: string | null;             // M/F/U
  patient_age: number | null;                // Age in years
  exam_status: string;                        // completed/pending/cancelled
  exam_source: string;                        // CT/MRI/X-ray/etc.
  exam_item: string;                          // Exam type description
  exam_description: string | null;           // Additional description
  order_datetime: string;                     // ISO 8601 datetime
  check_in_datetime: string | null;          // ISO 8601 datetime
  report_certification_datetime: string | null; // ISO 8601 datetime
  certified_physician: string | null;        // Physician name
}
```

### StudyDetail (Detail Endpoint)

Used in `/api/v1/studies/{exam_id}` response.

```typescript
interface StudyDetail {
  exam_id: string;
  medical_record_no: string | null;
  application_order_no: string | null;
  patient_name: string;
  patient_gender: string | null;
  patient_birth_date: string | null;         // YYYY-MM-DD
  patient_age: number | null;
  exam_status: string;
  exam_source: string;
  exam_item: string;
  exam_description: string | null;
  exam_room: string | null;
  exam_equipment: string | null;
  equipment_type: string;
  order_datetime: string;                     // ISO 8601
  check_in_datetime: string | null;          // ISO 8601
  report_certification_datetime: string | null; // ISO 8601
  certified_physician: string | null;
  data_load_time: string | null;             // ISO 8601
}
```

### FilterOptions

Used in `/api/v1/studies/filters/options` response.

```typescript
interface FilterOptions {
  exam_statuses: string[];        // All distinct statuses
  exam_sources: string[];         // All distinct sources
  equipment_types: string[];      // All distinct equipment types
  exam_rooms: string[];           // All distinct rooms
  exam_equipments: string[];      // All distinct equipments
  exam_descriptions: string[];    // Common descriptions
}
```

### SearchResponse

Used in `/api/v1/studies/search` response.

```typescript
interface SearchResponse {
  items: StudyListItem[];   // Array of study records
  count: number;            // Total count of matching records
  filters: FilterOptions;   // Available filter options
}
```

---

## Query Parameters

### Text Search (`q`)

- **Type**: `string`
- **Max Length**: 200 characters
- **Behavior**: Case-insensitive, partial matching
- **Searches**: 9 fields simultaneously

**Example**:
```bash
# Find all records with "張" in any searchable field
GET /api/v1/studies/search?q=張
```

### Filters

#### exam_status
- **Type**: `string`
- **Values**: `completed`, `pending`, `cancelled`
- **Match**: Exact match

```bash
GET /api/v1/studies/search?exam_status=completed
```

#### exam_source
- **Type**: `string`
- **Values**: `CT`, `MRI`, `X-ray`, `Ultrasound`, `Endoscopy`, etc.
- **Match**: Exact match

```bash
GET /api/v1/studies/search?exam_source=CT
```

#### exam_equipment
- **Type**: `array[string]`
- **Match**: Any match (OR logic)

```bash
# Bracket format
GET /api/v1/studies/search?exam_equipment[]=CT-001&exam_equipment[]=CT-002

# Standard format
GET /api/v1/studies/search?exam_equipment=CT-001&exam_equipment=CT-002
```

#### patient_gender
- **Type**: `array[string]`
- **Values**: `M`, `F`, `U`
- **Match**: Any match (OR logic)

```bash
GET /api/v1/studies/search?patient_gender[]=M&patient_gender[]=F
```

#### Age Range
- **patient_age_min**: Minimum age (inclusive)
- **patient_age_max**: Maximum age (inclusive)
- **Type**: `integer`

```bash
# Age 30-50
GET /api/v1/studies/search?patient_age_min=30&patient_age_max=50
```

#### Date Range
- **start_date**: Check-in date from (YYYY-MM-DD)
- **end_date**: Check-in date to (YYYY-MM-DD)
- **Type**: `string` (ISO 8601 date format)

```bash
# November 1-7, 2025
GET /api/v1/studies/search?start_date=2025-11-01&end_date=2025-11-07
```

### Pagination

#### limit
- **Type**: `integer`
- **Default**: 20
- **Range**: 1-100
- **Description**: Items per page

```bash
GET /api/v1/studies/search?limit=50
```

#### offset
- **Type**: `integer`
- **Default**: 0
- **Description**: Number of items to skip

```bash
# Skip first 40 items (page 3 with limit=20)
GET /api/v1/studies/search?limit=20&offset=40
```

### Sorting

#### sort
- **Type**: `string`
- **Default**: `order_datetime_desc`
- **Values**:
  - `order_datetime_desc`: Order datetime descending (newest first)
  - `order_datetime_asc`: Order datetime ascending (oldest first)
  - `patient_name_asc`: Patient name A-Z

```bash
GET /api/v1/studies/search?sort=patient_name_asc
```

---

## Examples

### Frontend Integration (JavaScript/TypeScript)

#### Basic Search
```javascript
async function searchStudies(query) {
  const response = await fetch(
    `http://localhost:8001/api/v1/studies/search?q=${encodeURIComponent(query)}&limit=20&offset=0`
  );
  const data = await response.json();
  return data;
}

// Usage
const results = await searchStudies('張偉');
console.log(`Found ${results.count} studies`);
console.log(results.items);
```

#### Multi-Filter Search
```javascript
async function searchWithFilters(filters) {
  const params = new URLSearchParams();

  if (filters.q) params.append('q', filters.q);
  if (filters.exam_status) params.append('exam_status', filters.exam_status);
  if (filters.exam_source) params.append('exam_source', filters.exam_source);

  // Array parameters (bracket format)
  if (filters.patient_gender) {
    filters.patient_gender.forEach(g => {
      params.append('patient_gender[]', g);
    });
  }

  params.append('limit', filters.limit || 20);
  params.append('offset', filters.offset || 0);

  const response = await fetch(
    `http://localhost:8001/api/v1/studies/search?${params.toString()}`
  );
  return response.json();
}

// Usage
const results = await searchWithFilters({
  q: '胸部',
  exam_status: 'completed',
  exam_source: 'CT',
  patient_gender: ['M', 'F'],
  limit: 10,
  offset: 0
});
```

#### Get Study Detail
```javascript
async function getStudyDetail(examId) {
  const response = await fetch(
    `http://localhost:8001/api/v1/studies/${examId}`
  );

  if (!response.ok) {
    if (response.status === 404) {
      throw new Error(`Study ${examId} not found`);
    }
    throw new Error('Failed to fetch study');
  }

  return response.json();
}

// Usage
try {
  const study = await getStudyDetail('EXAM001');
  console.log(study);
} catch (error) {
  console.error(error.message);
}
```

#### Load Filter Options
```javascript
async function loadFilterOptions() {
  const response = await fetch(
    'http://localhost:8001/api/v1/studies/filters/options'
  );
  const options = await response.json();

  // Populate dropdowns
  populateSelect('exam-status-select', options.exam_statuses);
  populateSelect('exam-source-select', options.exam_sources);
  populateSelect('equipment-select', options.exam_equipments);

  return options;
}
```

### Python Integration

#### Using requests library
```python
import requests

# Search studies
def search_studies(q='', limit=20, offset=0):
    url = 'http://localhost:8001/api/v1/studies/search'
    params = {
        'q': q,
        'limit': limit,
        'offset': offset
    }
    response = requests.get(url, params=params)
    response.raise_for_status()
    return response.json()

# Get study detail
def get_study_detail(exam_id):
    url = f'http://localhost:8001/api/v1/studies/{exam_id}'
    response = requests.get(url)
    response.raise_for_status()
    return response.json()

# Usage
results = search_studies(q='張偉', limit=10)
print(f"Found {results['count']} studies")

study = get_study_detail('EXAM001')
print(f"Patient: {study['patient_name']}")
```

### cURL Examples

#### Search with text query
```bash
curl "http://localhost:8001/api/v1/studies/search?q=張偉&limit=10"
```

#### Filtered search
```bash
curl "http://localhost:8001/api/v1/studies/search?exam_status=completed&exam_source=CT&limit=20"
```

#### Multi-select filter (bracket format)
```bash
curl "http://localhost:8001/api/v1/studies/search?patient_gender[]=M&patient_gender[]=F"
```

#### Get study detail
```bash
curl "http://localhost:8001/api/v1/studies/EXAM001"
```

#### Get filter options
```bash
curl "http://localhost:8001/api/v1/studies/filters/options"
```

---

## Rate Limiting

### Current Status

**Rate Limiting**: Not implemented (internal system)

### Future Considerations

For production deployment with external access:
- Rate limiting: 100 requests/minute per IP
- Burst allowance: 20 requests
- Implementation: Django Ratelimit or nginx rate limiting

---

## Performance Considerations

### Database Optimization

- **Composite Indexes**: `(exam_status, order_datetime)`, `(exam_source, order_datetime)`
- **Single Indexes**: `patient_name`, `exam_item`
- **Query Efficiency**: Optimized Q object filtering

### Caching Strategy

- **Filter Options**: 24-hour TTL
- **Cache Backend**: Local memory (dev) or Redis (prod)
- **Graceful Degradation**: System works without cache

### Response Times (Typical)

| Endpoint | Cached | Uncached |
|----------|--------|----------|
| `/search` | 50-150ms | 100-300ms |
| `/{exam_id}` | 20-50ms | 30-80ms |
| `/filters/options` | 10-30ms | 50-100ms |

---

## Version History

### v1.1.1 (2025-11-11)
- ✅ **CRITICAL FIX**: Corrected patient_birth_date export handling (CharField vs .isoformat())
- ✅ Added comprehensive test case for birth_date field export (test_patient_birth_date_export)
- ✅ Updated field type documentation with proper handling clarifications
- ✅ Test coverage: 16 tests passing (100% success rate)

### v1.1.0 (2025-11-10)
- ✅ Added comprehensive exception handling
- ✅ Centralized configuration management
- ✅ Request timing middleware
- ✅ 63 test cases (~85% coverage)
- ✅ Export functionality implementation
- ✅ Production-ready status

### v1.0.0 (2025-11-06)
- Initial Django Ninja API implementation
- PostgreSQL database integration
- Full API compatibility with FastAPI version

---

## Support and Contact

For API issues or questions:
- **GitHub Issues**: [Report here](https://github.com/your-org/image_data_platform/issues)
- **Documentation**: See `docs/` directory for detailed guides
- **Team**: Medical Imaging Team

---

**Last Updated**: 2025-11-11 (Bug fix for patient_birth_date export handling)
**Maintainer**: Medical Imaging Team
**API Version**: 1.1.1
