# API Contract: FastAPI ↔ Django Migration
**Status**: 🔒 LOCKED - Response format must not change
**Principle**: Never Break Userspace - Every byte must match

---

## Overview

This document defines the EXACT response format for all API endpoints. During migration from FastAPI to Django, EVERY endpoint must return responses in this format, byte-for-byte.

**If Django response differs by a single field, the entire frontend breaks.**

This is not negotiable. Test this before deploying.

---

## Endpoint: GET /api/v1/studies/search

### Request
```
GET /api/v1/studies/search?q=&exam_status=&exam_source=&exam_item=&page=1&page_size=20
```

**Query Parameters**:
- `q` (string, optional): Text search (patient name, exam description, exam item)
- `exam_status` (string, optional): Filter by exam status
- `exam_source` (string, optional): Filter by exam source
- `exam_item` (string, optional): Filter by exam item
- `page` (integer, default=1): Page number
- `page_size` (integer, default=20): Records per page

### Response (200 OK)

```json
{
  "data": [
    {
      "exam_id": "EXAM001",
      "patient_name": "Zhang Wei",
      "patient_gender": "M",
      "patient_age": 45,
      "exam_status": "completed",
      "exam_source": "CT",
      "exam_item": "Chest CT",
      "order_datetime": "2025-11-06T10:30:00",
      "check_in_datetime": "2025-11-06T10:45:00",
      "report_certification_datetime": "2025-11-06T14:30:00"
    }
  ],
  "total": 1250,
  "page": 1,
  "page_size": 20,
  "filters": {
    "exam_statuses": ["pending", "completed", "cancelled"],
    "exam_sources": ["CT", "MRI", "X-ray"],
    "exam_items": ["Chest CT", "Abdominal CT", "Spine MRI"]
  }
}
```

**Field Rules**:
- `data`: Array of Study objects
- `total`: Total count of all matching records (before pagination)
- `page`: Current page number
- `page_size`: Records per page
- `filters`: Available filter options from database

**Study Object**:
- `exam_id`: String, primary key
- `patient_name`: String
- `patient_gender`: String or null
- `patient_age`: Integer or null
- `exam_status`: String ("pending", "completed", "cancelled")
- `exam_source`: String
- `exam_item`: String
- `order_datetime`: ISO datetime string (e.g., "2025-11-06T10:30:00")
- `check_in_datetime`: ISO datetime string or null
- `report_certification_datetime`: ISO datetime string or null

**DateTime Format**: ISO 8601 format without timezone (YYYY-MM-DDTHH:MM:SS)

---

## Endpoint: GET /api/v1/studies/{exam_id}

### Request
```
GET /api/v1/studies/EXAM001
```

### Response (200 OK)

```json
{
  "exam_id": "EXAM001",
  "patient_name": "Zhang Wei",
  "patient_gender": "M",
  "patient_age": 45,
  "exam_status": "completed",
  "exam_source": "CT",
  "exam_item": "Chest CT",
  "order_datetime": "2025-11-06T10:30:00",
  "check_in_datetime": "2025-11-06T10:45:00",
  "report_certification_datetime": "2025-11-06T14:30:00"
}
```

### Response (404 Not Found)
```json
{
  "detail": "Study not found"
}
```

---

## Endpoint: GET /api/v1/studies/filters/options

### Request
```
GET /api/v1/studies/filters/options
```

### Response (200 OK)

```json
{
  "exam_statuses": ["pending", "completed", "cancelled"],
  "exam_sources": ["CT", "MRI", "X-ray", "Ultrasound"],
  "exam_items": ["Chest CT", "Abdominal CT", "Spine MRI", "Brain MRI"]
}
```

**Rules**:
- `exam_statuses`: Array of unique exam status values from database
- `exam_sources`: Array of unique exam source values from database
- `exam_items`: Array of unique exam item values from database
- All are sorted alphabetically
- No duplicates

---

## Endpoint: GET /api/v1/reports/search

### Request
```
GET /api/v1/reports/search?q=&exam_status=&page=1&page_size=20
```

### Response (200 OK)

```json
{
  "data": [
    {
      "report_id": "RPT001",
      "exam_id": "EXAM001",
      "patient_name": "Zhang Wei",
      "exam_item": "Chest CT",
      "findings": "Normal chest, no abnormalities",
      "radiologist": "Dr. Li",
      "created_at": "2025-11-06T15:00:00",
      "status": "completed"
    }
  ],
  "total": 500,
  "page": 1,
  "page_size": 20,
  "filters": {
    "statuses": ["draft", "completed", "archived"]
  }
}
```

---

## Endpoint: GET /api/v1/reports/{report_id}

### Request
```
GET /api/v1/reports/RPT001
```

### Response (200 OK)

```json
{
  "report_id": "RPT001",
  "exam_id": "EXAM001",
  "patient_name": "Zhang Wei",
  "exam_item": "Chest CT",
  "findings": "Normal chest, no abnormalities",
  "radiologist": "Dr. Li",
  "created_at": "2025-11-06T15:00:00",
  "status": "completed"
}
```

---

## Endpoint: GET /api/v1/analysis/tasks

### Request
```
GET /api/v1/analysis/tasks?status=&page=1&page_size=20
```

### Response (200 OK)

```json
{
  "data": [
    {
      "task_id": "TASK001",
      "exam_id": "EXAM001",
      "patient_name": "Zhang Wei",
      "analysis_type": "lung_nodule_detection",
      "status": "completed",
      "progress": 100,
      "results": {
        "nodules_found": 0,
        "confidence": 0.95
      },
      "created_at": "2025-11-06T10:00:00",
      "completed_at": "2025-11-06T10:30:00"
    }
  ],
  "total": 150,
  "page": 1,
  "page_size": 20,
  "filters": {
    "statuses": ["pending", "running", "completed", "failed"]
  }
}
```

---

## Endpoint: POST /api/v1/analysis/tasks

### Request
```json
{
  "exam_id": "EXAM001",
  "analysis_type": "lung_nodule_detection"
}
```

### Response (201 Created)

```json
{
  "task_id": "TASK001",
  "exam_id": "EXAM001",
  "analysis_type": "lung_nodule_detection",
  "status": "pending",
  "progress": 0,
  "created_at": "2025-11-06T10:00:00"
}
```

---

## Endpoint: GET /api/v1/analysis/tasks/{task_id}

### Request
```
GET /api/v1/analysis/tasks/TASK001
```

### Response (200 OK)

```json
{
  "task_id": "TASK001",
  "exam_id": "EXAM001",
  "analysis_type": "lung_nodule_detection",
  "status": "completed",
  "progress": 100,
  "results": {
    "nodules_found": 2,
    "confidence": 0.92,
    "details": [...]
  },
  "created_at": "2025-11-06T10:00:00",
  "completed_at": "2025-11-06T10:30:00"
}
```

---

## Endpoint: DELETE /api/v1/analysis/tasks/{task_id}

### Request
```
DELETE /api/v1/analysis/tasks/TASK001
```

### Response (204 No Content)
```
(empty body)
```

### Response (404 Not Found)
```json
{
  "detail": "Task not found"
}
```

---

## Endpoint: GET /api/v1/analysis/statistics

### Request
```
GET /api/v1/analysis/statistics
```

### Response (200 OK)

```json
{
  "total_tasks": 500,
  "completed_tasks": 450,
  "running_tasks": 30,
  "failed_tasks": 20,
  "average_duration_seconds": 1800,
  "success_rate": 0.9
}
```

---

## Endpoint: GET /api/v1/auth/me

### Request
```
GET /api/v1/auth/me
Headers: Authorization: Bearer {token}
```

### Response (200 OK)

```json
{
  "user_id": "USER001",
  "username": "zhangwei",
  "email": "zhangwei@hospital.com",
  "role": "radiologist"
}
```

### Response (401 Unauthorized)
```json
{
  "detail": "Not authenticated"
}
```

---

## Error Responses

### 400 Bad Request
```json
{
  "detail": "Invalid parameter: page must be > 0"
}
```

### 401 Unauthorized
```json
{
  "detail": "Not authenticated"
}
```

### 404 Not Found
```json
{
  "detail": "Resource not found"
}
```

### 500 Internal Server Error
```json
{
  "detail": "Internal server error"
}
```

---

## Testing Checklist

Before deploying Django version, verify EVERY endpoint:

- [ ] /api/v1/studies/search - Returns correct format
- [ ] /api/v1/studies/search?q=search_term - Text search works
- [ ] /api/v1/studies/search?exam_status=completed - Status filter works
- [ ] /api/v1/studies/{exam_id} - Detail endpoint works
- [ ] /api/v1/studies/{exam_id} (non-existent) - Returns 404
- [ ] /api/v1/studies/filters/options - Returns all filter options
- [ ] /api/v1/reports/search - Same format as studies
- [ ] /api/v1/reports/{report_id} - Detail works
- [ ] /api/v1/analysis/tasks - Lists all tasks
- [ ] /api/v1/analysis/tasks - Pagination works (page, page_size)
- [ ] POST /api/v1/analysis/tasks - Creates task
- [ ] GET /api/v1/analysis/tasks/{task_id} - Gets task
- [ ] DELETE /api/v1/analysis/tasks/{task_id} - Deletes task
- [ ] GET /api/v1/analysis/statistics - Returns stats
- [ ] GET /api/v1/auth/me - Returns user
- [ ] Every datetime field is ISO format (not Unix timestamp)
- [ ] Null values are returned as null (not empty string or 0)
- [ ] All HTTP status codes match (200, 201, 204, 400, 401, 404, 500)

---

## Frontend Verification

After deploying Django, run in frontend:

```javascript
// Test that all responses match expected format
async function verifyAPIContract() {
  const baseURL = 'http://localhost:8000/api/v1';

  // Test search endpoint
  const searchResp = await fetch(`${baseURL}/studies/search`);
  const searchData = await searchResp.json();

  console.assert(searchData.data instanceof Array, 'Missing "data" array');
  console.assert(typeof searchData.total === 'number', 'Missing "total"');
  console.assert(typeof searchData.page === 'number', 'Missing "page"');
  console.assert(typeof searchData.page_size === 'number', 'Missing "page_size"');
  console.assert(searchData.filters.exam_statuses instanceof Array, 'Missing filters');

  console.log('✅ API contract verified');
}
```

---

**This contract is locked. Any deviation requires explicit approval.**
